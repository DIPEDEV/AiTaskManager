from __future__ import annotations

from rich.console import Console

from taskcli.store import TaskStore, StoreError

console = Console()


def run(task_id: int, agent_type: str = "debug") -> None:
    """Mark debug verification as passed. Debug + coder ref → done."""
    try:
        store = TaskStore()
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    debug_task, coder_task = store.task_pass_debug(task_id)

    console.print(f"[green]Debug task {task_id} verification: PASSED ✓[/green]")
    if coder_task:
        console.print(f"[green]Coder task {coder_task.id} marked done ✓[/green]")
