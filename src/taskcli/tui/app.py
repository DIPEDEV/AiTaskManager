from __future__ import annotations

from pathlib import Path

from textual import on
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll, Container
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    Select,
    Static,
)
from textual.screen import ModalScreen
from textual.message import Message

from taskcli.config import load_config
from taskcli.models import Task, TaskStatus
from taskcli.store import TaskStore, StoreError


class TaskListItem(ListItem):
    """A ListItem that remembers its task ID."""

    def __init__(self, task_id: int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.task_id = task_id


class TaskListView(ListView):
    """A custom ListView for displaying tasks."""

    def __init__(self, store: TaskStore, agent_type: str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.store = store
        self.agent_type = agent_type

    def on_mount(self) -> None:
        self.refresh_tasks()

    def refresh_tasks(self) -> None:
        self.clear()
        tasks = self.store.load(self.agent_type)
        status_order = {
            TaskStatus.PENDING: 0,
            TaskStatus.IN_PROGRESS: 1,
            TaskStatus.NEEDS_VERIFICATION: 2,
            TaskStatus.DONE: 3,
        }
        tasks.sort(key=lambda t: status_order.get(t.status, 99))

        for task in tasks:
            icons = {
                TaskStatus.PENDING: "○",
                TaskStatus.IN_PROGRESS: "◉",
                TaskStatus.NEEDS_VERIFICATION: "◇",
                TaskStatus.DONE: "✓",
            }
            icon = icons.get(task.status, "?")
            title = task.title[:60]
            label = f"{icon} {title}"
            self.append(TaskListItem(task.id, Static(label)))

    def current_task_id(self) -> int | None:
        if self.index is not None and self.index < len(self.children):
            item = self.children[self.index]
            if isinstance(item, TaskListItem):
                return item.task_id
        return None


class DetailView(VerticalScroll):
    """Panel showing task details."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.current_task: Task | None = None
        self._store: TaskStore | None = None
        self._default = Static("Select a task to view details", id="detail-title")

    def on_mount(self) -> None:
        self.mount(self._default)

    def show_default(self) -> None:
        self.current_task = None
        self._store = None
        try:
            placeholder = self.query_one("#detail-title", Static)
            placeholder.update("Select a task to view details")
        except Exception:
            pass
        for child in list(self.children):
            if isinstance(child, Markdown):
                child.remove()

    def show_task(self, task: Task, store: TaskStore) -> None:
        self.current_task = task
        self._store = store

        lines = [
            f"# Task {task.id}: {task.title}",
            "",
            f"**Status:** {task.status_icon} {task.status.value}",
            f"**Priority:** {task.priority}",
            f"**Agent:** {task.agent_type}",
        ]
        if task.file:
            loc = task.file
            if task.line:
                loc += f":{task.line}"
            lines.append(f"**File:** {loc}")
        if task.coder_ref:
            lines.append(f"**Coder Ref:** {task.coder_ref}")
        if task.source_agent:
            lines.append(f"**Source Agent:** {task.source_agent}")
        if task.created:
            lines.append(f"**Created:** {task.created[:19]}")
        if task.spec:
            lines.append("")
            lines.append("---")
            lines.append("")
            lines.append(f"**Specification:**\n\n{task.spec}")

        md = Markdown("\n".join(lines))
        for child in list(self.children):
            if not isinstance(child, Static) or child.id != "detail-title":
                child.remove()
        self.mount(md)


class AddTaskScreen(ModalScreen[Task]):
    """Modal screen for creating a new task."""

    BINDINGS = [
        ("escape", "cancel", "Cancel"),
        ("ctrl+s", "submit", "Create Task"),
    ]

    CSS = """
    AddTaskScreen {
        align: center middle;
    }
    #add-task-dialog {
        width: 60;
        height: auto;
        max-height: 90%;
        border: solid $primary;
        background: $surface;
        padding: 1 2;
    }
    #add-task-dialog Input {
        margin: 1 0;
        width: 100%;
    }
    #add-task-dialog Label {
        margin: 0 0;
        text-style: bold;
    }
    #add-task-dialog Select {
        margin: 1 0;
        width: 100%;
    }
    """

    def __init__(self, store: TaskStore, agent_types: list[str], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._store = store
        self._agent_types = agent_types

    def compose(self) -> ComposeResult:
        with Vertical(id="add-task-dialog"):
            yield Label("[bold reverse] CREATE NEW TASK [/bold reverse]")
            yield Label("Title *")
            yield Input(placeholder="What needs to be done?", id="task-title")
            yield Label("Agent type")
            agent_options = [(t, t) for t in self._agent_types] if self._agent_types else [("coder", "coder")]
            agent_default = self._agent_types[0] if self._agent_types else "coder"
            yield Select(agent_options, id="task-agent", value=agent_default)
            yield Label("Priority")
            yield Select(
                [("high", "high"), ("medium", "medium"), ("low", "low")],
                id="task-priority",
                value="medium",
            )
            yield Label("File (optional)")
            yield Input(placeholder="src/module.py", id="task-file")
            yield Label("Line (optional)")
            yield Input(placeholder="42", id="task-line")
            yield Label("Specification (optional)")
            yield Input(placeholder="Multi-line context for the AI...", id="task-spec")
            with Horizontal():
                yield Button("Create Task", variant="primary", id="btn-create")
                yield Button("Cancel", variant="error", id="btn-cancel")
            yield Label("[dim]Ctrl+S to create  •  Esc to cancel[/dim]")

    def on_mount(self) -> None:
        self.query_one("#task-title", Input).focus()

    def action_submit(self) -> None:
        self._do_create()

    def _do_create(self) -> None:
        title = self.query_one("#task-title", Input).value.strip()
        if not title:
            self.notify("Title is required", severity="error")
            return

        agent: str | None = None
        try:
            select = self.query_one("#task-agent", Select)
            if select.value and select.value != Select.BLANK:
                agent = str(select.value)
        except Exception:
            pass
        if not agent:
            agent = self._agent_types[0] if self._agent_types else "coder"

        priority_value: str | None = None
        try:
            select = self.query_one("#task-priority", Select)
            if select.value and select.value != Select.BLANK:
                priority_value = str(select.value)
        except Exception:
            pass
        if priority_value not in ("high", "medium", "low"):
            priority_value = "medium"

        file = self.query_one("#task-file", Input).value.strip()
        line_str = self.query_one("#task-line", Input).value.strip()
        spec = self.query_one("#task-spec", Input).value.strip()

        line = 0
        try:
            line = int(line_str)
        except ValueError:
            pass

        task = Task(
            id=0,
            title=title,
            status=TaskStatus.PENDING,
            priority=priority_value,
            spec=spec,
            file=file,
            line=line,
        )
        task = self._store.add(agent, task)
        self.notify(f"Task {task.id} created in {agent}")
        self.dismiss(task)

    @on(Button.Pressed, "#btn-create")
    def create_task(self) -> None:
        self._do_create()

    def action_cancel(self) -> None:
        self.dismiss(None)

    @on(Button.Pressed, "#btn-cancel")
    def cancel(self) -> None:
        self.dismiss(None)


class KanbanColumn(Vertical):
    def __init__(self, status_key: str, header: str, store: TaskStore, agent_type: str):
        super().__init__(classes="kanban-column")
        self.status_key = status_key
        self.header = header
        self.store = store
        self.agent_type = agent_type

    def render(self) -> None:
        self.clear()
        self.mount(Static(self.header, classes="kanban-header"))
        status = TaskStatus(self.status_key)
        tasks = [t for t in self.store.load(self.agent_type) if t.status == status]
        for task in tasks:
            self.mount(TaskListItem(task.id, Static(f"{task.status_icon} {task.title[:40]}", classes="kanban-task")))


class TaskTUI(App):
    """Interactive TUI for task management."""

    CSS = """
    #main-layout {
        height: 1fr;
    }
    #sidebar {
        width: 30%;
        border: solid $primary;
    }
    #detail {
        width: 70%;
        border: solid $primary-background;
        padding: 1 2;
    }
    #agent-tabs {
        height: 3;
        overflow-x: auto;
    }
    .agent-tab {
        width: auto;
        padding: 0 1;
        margin: 0 1 0 0;
    }
    .agent-tab-active {
        background: $primary;
        color: $text;
    }
    TaskListView:focus {
        border: solid $secondary;
    }
    #detail-title {
        text-style: bold;
        color: $text;
        height: auto;
    }
    #kanban-container {
        width: 100%;
        height: 100%;
    }
    .kanban-column {
        width: 25%;
        height: 100%;
        border: solid $primary;
    }
    .kanban-header {
        height: 3;
        background: $primary;
        text-style: bold;
        padding: 0 1;
    }
    .kanban-task {
        padding: 0 1;
        margin: 0 0 1 0;
    }
    """

    BINDINGS = [
        ("n", "next_task", "Next Task"),
        ("d", "done_task", "Done"),
        ("p", "pass_debug", "Pass (verify OK)"),
        ("f", "fail_debug", "Fail (re-create)"),
        ("a", "add_task", "Add Task"),
        ("tab", "switch_agent", "Switch Agent"),
        ("k", "toggle_kanban", "Kanban"),
        ("q", "quit", "Quit"),
    ]

    def __init__(self, root: Path | None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._kanban_visible = False
        try:
            self.store = TaskStore(root) if root else TaskStore()
        except StoreError:
            self.store = None
        if self.store:
            self.agents = [a.name for a in self.store._agents]
        else:
            self.agents = []
        self.current_agent = self.agents[0] if self.agents else "coder"

    def compose(self) -> ComposeResult:
        yield Header()
        if self.store is None:
            yield Static("No .tasks directory found. Run 'task init' first.", id="error-msg")
            yield Footer()
            return

        with Horizontal(id="main-layout"):
            with Vertical(id="sidebar"):
                yield Static(" AGENTS ", id="agents-label")
                with Horizontal(id="agent-tabs"):
                    for name in self.agents:
                        classes = "agent-tab"
                        if name == self.current_agent:
                            classes += " agent-tab-active"
                        yield Button(name, id=f"tab-{name}", classes=classes)
                yield TaskListView(self.store, self.current_agent, id="task-list")
            yield DetailView(id="detail")
        yield Footer()

    def on_mount(self) -> None:
        if self.store is None:
            return
        try:
            self.set_focus(self.query_one(TaskListView))
        except Exception:
            pass

    def _switch_agent(self, name: str) -> None:
        if name == self.current_agent:
            return
        self.current_agent = name

        for agent_name in self.agents:
            btn = self.query_one(f"#tab-{agent_name}", Button)
            if agent_name == name:
                btn.classes = "agent-tab agent-tab-active"
            else:
                btn.classes = "agent-tab"

        task_list = self.query_one(TaskListView)
        task_list.agent_type = name
        task_list.refresh_tasks()

        detail = self.query_one(DetailView)
        detail.show_default()

        try:
            self.set_focus(task_list)
        except Exception:
            pass

    @on(Button.Pressed, ".agent-tab")
    def on_agent_tab_pressed(self, event: Button.Pressed) -> None:
        if event.button.id and event.button.id.startswith("tab-"):
            name = event.button.id.replace("tab-", "")
            self._switch_agent(name)

    def action_switch_agent(self) -> None:
        if not self.agents:
            return
        idx = self.agents.index(self.current_agent)
        next_idx = (idx + 1) % len(self.agents)
        self._switch_agent(self.agents[next_idx])
        self.notify(f"Switched to {self.agents[next_idx]}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not self.store:
            return
        task_list = event.list_view
        if not isinstance(task_list, TaskListView):
            return
        task_id = task_list.current_task_id()
        if task_id is None:
            return
        task = self.store.get(self.current_agent, task_id)
        if task is None:
            return
        detail = self.query_one(DetailView)
        detail.show_task(task, self.store)

    def action_add_task(self) -> None:
        if not self.store:
            return
        screen = AddTaskScreen(self.store, self.agents)
        self.push_screen(screen, callback=self._on_task_added)

    def _get_selected_task(self) -> Task | None:
        detail = self.query_one(DetailView)
        if detail.current_task:
            return detail.current_task
        task_list = self.query_one(TaskListView)
        task_id = task_list.current_task_id()
        if task_id is not None:
            return self.store.get(self.current_agent, task_id)
        return None

    def _on_task_added(self, task: Task | None) -> None:
        if task:
            self.notify(f"Task {task.id} created in {task.agent_type}")
            if task.agent_type == self.current_agent:
                self._refresh()
            else:
                self._switch_agent(task.agent_type)

    def action_next_task(self) -> None:
        if not self.store:
            return
        task = self.store.get_next(self.current_agent, mark_in_progress=True)
        if task:
            self.notify(f"Assigned: {task.title}", title="Next Task")
            self._refresh()
            detail = self.query_one(DetailView)
            detail.show_task(task, self.store)

            from taskcli.config import get_agent, get_pipeline_target
            agent = get_agent(self.current_agent, self.store._agents)
            target = get_pipeline_target(agent, self.store._agents) if agent else None
            if target:
                self.notify(f"Pipeline to: {target.name} (use 'd' when done)", title="Note")
        else:
            self.notify("No pending tasks", title="Info", severity="warning")

    def action_done_task(self) -> None:
        if not self.store:
            return
        task = self._get_selected_task()
        if task is None:
            self.notify("Select a task first (arrow keys + Enter)", title="Warning", severity="warning")
            return

        from taskcli.config import get_agent
        agent = get_agent(task.agent_type, self.store._agents)

        if agent and agent.pipeline_to:
            result = self.store.task_done_with_pipeline(task.agent_type, task.id)
            self.notify(f"Sent to {agent.pipeline_to} -> task {result.id}", title="Done")
        else:
            self.store.update(task.agent_type, task.id, status=TaskStatus.DONE)
            self.notify(f"Task {task.id} marked done", title="Done")
        self._refresh()

    def action_pass_debug(self) -> None:
        if not self.store:
            return
        task = self._get_selected_task()
        if task is None:
            self.notify("Select a verify task first", title="Warning", severity="warning")
            return
        if task.coder_ref:
            d, _ = self.store.task_pass_verify(task.id, task.agent_type)
            self.notify(f"Verification passed", title="Pass")
            self._refresh()
        else:
            self.notify("Only verification tasks with coder_ref can be passed", title="Warning", severity="warning")

    def action_fail_debug(self) -> None:
        if not self.store:
            return
        task = self._get_selected_task()
        if task is None:
            self.notify("Select a verify task first", title="Warning", severity="warning")
            return
        if task.coder_ref:
            new_task = self.store.task_fail_verify(task.id, "Verification failed from TUI", task.agent_type)
            self.notify(f"Re-created in {new_task.agent_type} -> task {new_task.id}", title="Fail")
            self._refresh()
        else:
            self.notify("Only verification tasks with coder_ref can be failed", title="Warning", severity="warning")

    def _refresh(self) -> None:
        task_list = self.query_one(TaskListView)
        task_list.refresh_tasks()
        detail = self.query_one(DetailView)
        detail.show_default()
        try:
            self.set_focus(task_list)
        except Exception:
            pass

    def action_toggle_kanban(self) -> None:
        """Toggle between list view and kanban view."""
        if not self.store:
            return

        if self._kanban_visible:
            self._switch_to_list()
        else:
            self._switch_to_kanban()

    def _switch_to_kanban(self) -> None:
        main = self.query_one("#main-layout")
        main.display = "none"

        columns = [
            ("pending", "○ Pending"),
            ("in_progress", "◉ In Progress"),
            ("needs_verification", "◇ Needs Verification"),
            ("done", "✓ Done"),
        ]
        container = Horizontal(id="kanban-container")
        self.mount(container)
        for status_key, header in columns:
            col = KanbanColumn(status_key, header, self.store, self.current_agent)
            col.render()
            container.mount(col)

        self._kanban_visible = True
        self.notify("Kanban view (press k to return to list)")

    def _switch_to_list(self) -> None:
        try:
            kanban = self.query_one("#kanban-container")
            kanban.remove()
        except Exception:
            pass

        main = self.query_one("#main-layout")
        main.display = "flex"

        self._kanban_visible = False
        self.notify("List view")


def run_tui(root: Path | None = None) -> None:
    app = TaskTUI(root=root)
    app.run()