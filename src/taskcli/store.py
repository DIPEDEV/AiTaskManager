from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from taskcli.models import Task, TaskStatus
from taskcli.parser import write_tasks_file
from taskcli.config import (
    find_tasks_root, load_config, get_agent, get_config_path,
    get_storage_backend, get_git_sync_enabled,
)
from taskcli.backend import StorageBackend, PlainTextBackend, create_backend
from taskcli.git_sync import GitSync, GitSyncError
from taskcli.hooks import HookRunner


class StoreError(Exception):
    """Error in task store operations."""
    pass


class TaskStore:
    """CRUD operations for .tasks files.

    Uses a pluggable StorageBackend for persistence. Defaults to
    plain-text .tasks files for backward compatibility.
    """

    def __init__(self, root: Path | None = None, backend: StorageBackend | None = None):
        self.root = root or find_tasks_root()
        if self.root is None or not self.root.is_dir():
            raise StoreError(
                "No .tasks directory found. Run 'task init' first."
            )
        self._agents = load_config(get_config_path(self.root))
        config_path = get_config_path(self.root)

        if backend is not None:
            self._backend = backend
        else:
            backend_type = get_storage_backend(config_path)
            self._backend = create_backend(backend_type, self.root)

        self._git_sync = None
        if get_git_sync_enabled(config_path):
            self._git_sync = GitSync(self.root)

    def _maybe_git_commit(self, agent_type: str, action: str) -> None:
        """Auto-commit to git after a mutation if git sync is enabled."""
        if self._git_sync is None:
            return
        try:
            self._git_sync.commit(f"auto: {agent_type}.{action}")
        except GitSyncError:
            pass

    def _run_hooks(self, event: str, task: Task, extra: dict | None = None) -> None:
        """Run hooks for an event with task context."""
        try:
            runner = HookRunner(task.agent_type, get_config_path(self.root))
            ctx = {
                "task_id": task.id,
                "agent_type": task.agent_type,
                "title": task.title,
                "priority": task.priority,
                "section": task.section,
                **(extra or {}),
            }
            runner.run(event, ctx)
        except Exception:
            pass

    def _get_agent(self, agent_type: str):
        """Get agent config, raising StoreError if not found."""
        agent = get_agent(agent_type, self._agents)
        if agent is None:
            raise StoreError(f"Unknown agent type: {agent_type}")
        return agent

    def load(self, agent_type: str) -> list[Task]:
        """Load all tasks for an agent type."""
        self._get_agent(agent_type)  # validate agent exists
        return self._backend.load(agent_type)

    def save(self, agent_type: str, tasks: list[Task]) -> None:
        """Save tasks for an agent type."""
        self._get_agent(agent_type)  # validate agent exists
        self._backend.ensure(agent_type)
        self._backend.save(agent_type, tasks)

    def get(self, agent_type: str, task_id: int) -> Task | None:
        """Get a single task by ID."""
        tasks = self.load(agent_type)
        for task in tasks:
            if task.id == task_id:
                return task
        return None

    def add(self, agent_type: str, task: Task) -> Task:
        """Add a new task with auto-incremented ID."""
        tasks = self.load(agent_type)
        max_id = max((t.id for t in tasks), default=0)
        task.id = max_id + 1
        task.agent_type = agent_type
        tasks.append(task)
        self.save(agent_type, tasks)
        self._maybe_git_commit(agent_type, "add")
        self._run_hooks("on_create", task)
        return task

    def update(self, agent_type: str, task_id: int, **kwargs) -> Task | None:
        """Update task fields."""
        tasks = self.load(agent_type)
        for i, task in enumerate(tasks):
            if task.id == task_id:
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)
                tasks[i] = task
                self.save(agent_type, tasks)
                self._maybe_git_commit(agent_type, "update")
                self._run_hooks("on_done", task)
                return task
        return None

    def move(self, from_agent: str, to_agent: str, task_id: int) -> Task | None:
        """Move a task from one agent file to another, preserving ID."""
        from_tasks = self.load(from_agent)
        task = None
        remaining = []
        for t in from_tasks:
            if t.id == task_id:
                task = t
            else:
                remaining.append(t)

        if task is None:
            return None

        task.agent_type = to_agent
        self.save(from_agent, remaining)

        to_tasks = self.load(to_agent)
        to_tasks.append(task)
        self.save(to_agent, to_tasks)

        return task

    def get_next(self, agent_type: str, mark_in_progress: bool = True) -> Task | None:
        """Get the next pending task, optionally marking it in_progress.

        Priority order: high > medium > low, then by creation date.
        Overdue tasks (due field in past) are boosted to top.
        Skips tasks that are blocked by other pending tasks (DAG).
        """
        tasks = self.load(agent_type)
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]
        pending = [t for t in pending if not self._is_blocked(t, tasks)]

        if not pending:
            return None

        priority_order = {"high": 0, "medium": 1, "low": 2}

        def sort_key(t: Task) -> tuple:
            overdue = self._is_overdue(t) if t.due else False
            return (not overdue, priority_order.get(t.priority, 1), t.created)

        pending.sort(key=sort_key)

        task = pending[0]

        if mark_in_progress:
            now = datetime.now(timezone.utc).isoformat()
            self.update(agent_type, task.id, status=TaskStatus.IN_PROGRESS, started_at=now)
            task.status = TaskStatus.IN_PROGRESS
            task.started_at = now

        return task

    def _is_overdue(self, task: Task) -> bool:
        """Return True if task has a due date in the past."""
        if not task.due:
            return False
        try:
            due_dt = datetime.fromisoformat(task.due.replace("Z", "+00:00"))
            return due_dt < datetime.now(timezone.utc)
        except ValueError:
            return False

    def _is_blocked(self, task: Task, all_tasks: list[Task]) -> bool:
        """Return True if any blocker task is still pending."""
        for blocker_id in task.blocked_by:
            for t in all_tasks:
                if t.id == blocker_id and t.status == TaskStatus.PENDING:
                    return True
        return False

    def task_done_coder(self, task_id: int) -> Task:
        """Move coder task to debug for verification (legacy, delegates to generic)."""
        return self.task_done_with_pipeline("coder", task_id)

    def task_done_with_pipeline(self, agent_type: str, task_id: int) -> Task:
        """Move task to its pipeline_to agent: delete source, create verify task."""
        agent = get_agent(agent_type, self._agents)
        if agent is None:
            raise StoreError(f"Unknown agent: {agent_type}")

        target_name = agent.pipeline_to
        if not target_name:
            if agent_type == "debug":
                return self.update(agent_type, task_id, status=TaskStatus.DONE)
            target_name = "debug"

        target_agent = get_agent(target_name, self._agents)
        if target_agent is None:
            raise StoreError(f"Pipeline target '{target_name}' not found")

        tasks = self.load(agent_type)
        task = None
        remaining = []
        for t in tasks:
            if t.id == task_id:
                task = t
            else:
                remaining.append(t)

        if task is None:
            raise StoreError(f"Task {task_id} not found in {agent_type}")

        # Remove source task entirely
        self.save(agent_type, remaining)
        self._maybe_git_commit(agent_type, "done")

        # Create verify task in pipeline target
        verify_task = Task(
            id=0,
            title=f"[Verify] {task.title}",
            status=TaskStatus.PENDING,
            priority=task.priority,
            spec=task.spec,
            file=task.file,
            line=task.line,
            agent_type=target_name,
            coder_ref=task.id,
            source_agent=agent_type,
        )
        result = self.add(target_name, verify_task)

        if task.started_at:
            try:
                from datetime import datetime
                start = datetime.fromisoformat(task.started_at.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                actual = int((now - start).total_seconds() / 60)
                self.update(agent_type, task.id, finished_at=now.isoformat(), actual_min=actual)
            except Exception:
                pass

        self._run_hooks("on_done", task, {"verify_task_id": result.id})
        return result

    def task_pass_verify(self, task_id: int, agent_type: str = "debug") -> tuple[Task, Task | None]:
        """Verification passed. Mark verify task as done."""
        verify_task = self.get(agent_type, task_id)
        if verify_task is None:
            raise StoreError(f"Task {task_id} not found in {agent_type}")

        self.update(agent_type, task_id, status=TaskStatus.DONE)
        verify_task.status = TaskStatus.DONE
        self._run_hooks("on_verify_pass", verify_task)

        return verify_task, None

    def task_pass_debug(self, task_id: int) -> tuple[Task, Task | None]:
        """Debug verification passed (legacy, delegates to generic)."""
        return self.task_pass_verify(task_id, "debug")

    def task_fail_verify(self, task_id: int, reason: str, agent_type: str = "debug") -> Task:
        """Verification failed. Creates new task in source agent with feedback."""
        verify_task = self.get(agent_type, task_id)
        if verify_task is None:
            raise StoreError(f"Task {task_id} not found in {agent_type}")

        self.update(agent_type, task_id, status=TaskStatus.DONE)

        source_agent_type = verify_task.source_agent or "coder"

        new_task = Task(
            id=0,
            title=f"[Re-check] {verify_task.title.replace('[Verify] ', '')}",
            status=TaskStatus.PENDING,
            priority=verify_task.priority,
            spec=f"Previous verification FAILED:\n{reason}\n\n---\n{verify_task.spec}",
            file=verify_task.file,
            line=verify_task.line,
            agent_type=source_agent_type,
        )
        new_task = self.add(source_agent_type, new_task)
        self._run_hooks("on_verify_fail", verify_task, {"reason": reason, "recheck_task_id": new_task.id})
        return new_task

    def task_fail_debug(self, task_id: int, reason: str) -> Task:
        """Debug verification failed (legacy, delegates to generic)."""
        return self.task_fail_verify(task_id, reason, "debug")

    def list_sections(self, agent_type: str) -> list[str]:
        """Return distinct non-empty sections for an agent."""
        tasks = self.load(agent_type)
        sections = sorted({t.section for t in tasks if t.section})
        return sections

    def set_section(
        self, agent_type: str, task_id: int, section: str
    ) -> Task | None:
        """Set the section on a task. Wraps update()."""
        return self.update(agent_type, task_id, section=section)

    def list_tasks(
        self,
        agent_type: str | None = None,
        status: TaskStatus | None = None,
        section: str | None = None,
        tag: str | None = None,
    ) -> list[Task]:
        """List tasks with optional filters."""
        if agent_type:
            tasks = self.load(agent_type)
            if status:
                tasks = [t for t in tasks if t.status == status]
            if section is not None:
                tasks = [t for t in tasks if t.section == section]
            if tag:
                tasks = [t for t in tasks if tag in t.tags]
            return tasks

        all_tasks = []
        for agent in self._agents:
            t = self.load(agent.name)
            if status:
                t = [x for x in t if x.status == status]
            if section is not None:
                t = [x for x in t if x.section == section]
            if tag:
                t = [x for x in t if tag in x.tags]
            all_tasks.extend(t)
        return all_tasks
