from __future__ import annotations

from rich.console import Console

from taskcli.config import get_agent
from taskcli.models import TaskStatus
from taskcli.store import TaskStore, StoreError

console = Console()


def run(task_id: int, agent_type: str) -> None:
    """Mark a task as done.

    For agents with pipeline_to: transitions to target for verification.
    For verification agents: marks verify + source as done.
    For agents without pipeline: marks task as done.
    """
    try:
        store = TaskStore()
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    agent = get_agent(agent_type, store._agents)
    if agent is None:
        console.print(f"[red]Unknown agent type: {agent_type}[/red]")
        return

    if agent.pipeline_to:
        verify_task = store.task_done_with_pipeline(agent_type, task_id)
        console.print(
            f"[yellow]Task {task_id} ({agent_type}) → {agent.pipeline_to} as task {verify_task.id}[/yellow]"
        )
        return

    task = store.get(agent_type, task_id)
    if task is None:
        console.print(f"[red]Task {task_id} not found in {agent_type}[/red]")
        return

    if task.coder_ref:
        verify_task, _ = store.task_pass_verify(task_id, agent_type)
        console.print(f"[green]Task {task_id} passed verification ✓[/green]")
        return

    store.update(agent_type, task_id, status=TaskStatus.DONE)
    console.print(f"[green]Task {task_id} ({agent_type}) marked done ✓[/green]")
