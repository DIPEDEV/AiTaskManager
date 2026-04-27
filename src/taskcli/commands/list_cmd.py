from __future__ import annotations

from rich.console import Console
from rich.table import Table

from taskcli.models import TaskStatus
from taskcli.store import TaskStore, StoreError

console = Console()


def run(
    agent_type: str = "",
    status: str = "",
    all_agents: bool = False,
) -> None:
    """List tasks with optional filters."""
    try:
        store = TaskStore()
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    status_filter = TaskStatus(status) if status else None

    if all_agents or not agent_type:
        agents = [a.name for a in store._agents]
    else:
        agents = [agent_type]

    table = Table(title="Tasks")
    table.add_column("ID", style="dim")
    table.add_column("S", style="bold")
    table.add_column("Agent", style="cyan")
    table.add_column("Priority")
    table.add_column("Title")
    table.add_column("File")

    total = 0
    for agent in agents:
        try:
            tasks = store.list_tasks(agent, status_filter)
        except StoreError:
            continue

        for task in tasks:
            total += 1
            priority_style = {
                "high": "red",
                "medium": "yellow",
                "low": "green",
            }.get(task.priority, "white")

            table.add_row(
                str(task.id),
                task.status_icon,
                agent,
                f"[{priority_style}]{task.priority}[/{priority_style}]",
                task.title,
                f"{task.file}:{task.line}" if task.file else "",
            )

    if total == 0:
        console.print("[dim]No tasks found.[/dim]")
    else:
        console.print(table)
        console.print(f"[dim]{total} task(s)[/dim]")
