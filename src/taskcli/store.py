from __future__ import annotations

from pathlib import Path
from typing import Callable

from taskcli.models import Task, TaskStatus
from taskcli.parser import parse_tasks_file, write_tasks_file
from taskcli.config import find_tasks_root, load_config, get_agent, get_config_path


class StoreError(Exception):
    """Error in task store operations."""
    pass


class TaskStore:
    """CRUD operations for .tasks files."""

    def __init__(self, root: Path | None = None):
        self.root = root or find_tasks_root()
        if self.root is None or not self.root.is_dir():
            raise StoreError(
                "No .tasks directory found. Run 'task init' first."
            )
        self._agents = load_config(get_config_path(self.root))

    def _task_file(self, agent_type: str) -> Path:
        agent = get_agent(agent_type, self._agents)
        if agent is None:
            raise StoreError(f"Unknown agent type: {agent_type}")
        return self.root / agent.file

    def _ensure_file(self, agent_type: str) -> Path:
        filepath = self._task_file(agent_type)
        if not filepath.exists():
            header = f"{agent_type}.tasks - Tasks for {agent_type} agent"
            write_tasks_file(str(filepath), [], header)
        return filepath

    def load(self, agent_type: str) -> list[Task]:
        """Load all tasks for an agent type."""
        filepath = self._task_file(agent_type)
        return parse_tasks_file(str(filepath))

    def save(self, agent_type: str, tasks: list[Task]) -> None:
        """Save tasks for an agent type."""
        filepath = self._ensure_file(agent_type)
        header = f"{agent_type}.tasks - Tasks for {agent_type} agent"
        write_tasks_file(str(filepath), tasks, header)

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
        """
        tasks = self.load(agent_type)
        pending = [t for t in tasks if t.status == TaskStatus.PENDING]

        if not pending:
            return None

        priority_order = {"high": 0, "medium": 1, "low": 2}
        pending.sort(key=lambda t: (priority_order.get(t.priority, 1), t.created))

        task = pending[0]

        if mark_in_progress:
            self.update(agent_type, task.id, status=TaskStatus.IN_PROGRESS)
            task.status = TaskStatus.IN_PROGRESS

        return task

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
            return self.update(agent_type, task_id, status=TaskStatus.DONE)

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
        return self.add(target_name, verify_task)

    def task_pass_verify(self, task_id: int, agent_type: str = "debug") -> tuple[Task, Task | None]:
        """Verification passed. Mark verify task as done."""
        verify_task = self.get(agent_type, task_id)
        if verify_task is None:
            raise StoreError(f"Task {task_id} not found in {agent_type}")

        self.update(agent_type, task_id, status=TaskStatus.DONE)
        verify_task.status = TaskStatus.DONE

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
        return self.add(source_agent_type, new_task)

    def task_fail_debug(self, task_id: int, reason: str) -> Task:
        """Debug verification failed (legacy, delegates to generic)."""
        return self.task_fail_verify(task_id, reason, "debug")

    def list_tasks(
        self,
        agent_type: str | None = None,
        status: TaskStatus | None = None,
    ) -> list[Task]:
        """List tasks with optional filters."""
        if agent_type:
            tasks = self.load(agent_type)
            if status:
                tasks = [t for t in tasks if t.status == status]
            return tasks

        all_tasks = []
        for agent in self._agents:
            t = self.load(agent.name)
            if status:
                t = [x for x in t if x.status == status]
            all_tasks.extend(t)
        return all_tasks
