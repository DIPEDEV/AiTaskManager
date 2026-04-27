from __future__ import annotations

from rich.console import Console

from taskcli.store import TaskStore, StoreError

console = Console()


def run(task_id: int, message: str, agent_type: str = "debug") -> None:
    """Mark debug verification as failed. Creates new coder task with feedback."""
    try:
        store = TaskStore()
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    new_task = store.task_fail_debug(task_id, message)

    console.print(f"[red]Debug task {task_id} verification: FAILED ✗[/red]")
    console.print(f"[yellow]New coder task {new_task.id} created with feedback[/yellow]")
    console.print(f"[dim]Title: {new_task.title}[/dim]")
