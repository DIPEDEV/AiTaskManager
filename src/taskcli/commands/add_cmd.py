from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.table import Table

from taskcli.models import Task, TaskStatus
from taskcli.store import TaskStore, StoreError
from taskcli.claude_spec import generate_spec

console = Console()


def run(
    title: str,
    agent_type: str = "coder",
    priority: str = "medium",
    file: str = "",
    line: int = 0,
    spec: str = "",
    description: str = "",
    section: str = "",
    root: Path | None = None,
    auto_spec: bool = False,
    tag: str = "",
due: str = "",
        recur: str = "",
        estimate_min: int = 0,
    ) -> None:
    """Add a new task."""
    try:
        store = TaskStore(root) if root else TaskStore()
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    if description and not spec:
        spec = description

    if auto_spec and not spec:
        result = generate_spec(title, context=description)
        spec = result.spec
        if not file and result.file:
            file = result.file
        if not line and result.line:
            line = result.line

    tags = [t.strip() for t in tag.split(",") if t.strip()]

    task = Task(
        id=0,
        title=title,
        status=TaskStatus.PENDING,
        priority=priority,
        spec=spec,
        file=file,
        line=line,
        section=section,
        tags=tags,
        due=due,
        recur=recur,
        estimate_min=estimate_min,
    )

    task = store.add(agent_type, task)

    console.print(f"[green]Task {task.id} added to {agent_type} ({priority} priority)[/green]")

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")
    table.add_row("ID", str(task.id))
    table.add_row("Title", task.title)
    table.add_row("Status", task.status.value)
    table.add_row("Priority", task.priority)
    table.add_row("Agent", agent_type)
    if task.file:
        loc = task.file
        if task.line:
            loc += f":{task.line}"
        table.add_row("Location", loc)
    if task.spec:
        table.add_row("Spec", task.spec[:100] + ("..." if len(task.spec) > 100 else ""))
    console.print(table)