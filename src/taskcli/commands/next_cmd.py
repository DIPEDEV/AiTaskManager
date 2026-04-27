from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from taskcli.store import TaskStore, StoreError

console = Console()


def run(agent_type: str = "coder", root: Path | None = None, short: bool = False) -> None:
    """Get the next pending task and mark it in_progress."""
    try:
        store = TaskStore(root) if root else TaskStore()
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    task = store.get_next(agent_type, mark_in_progress=True)

    if task is None:
        if short:
            console.print(f"[dim]{agent_type}: no tasks[/dim]")
        else:
            console.print(f"[dim]No pending tasks for {agent_type}[/dim]")
        return

    if short:
        title = task.title[:50] + ("..." if len(task.title) > 50 else "")
        priority = task.priority[0].upper() if task.priority else "?"
        console.print(f"[{priority}] [{agent_type}] {title}")
        return

    lines = [
        f"[bold]ID:[/bold]        {task.id}",
        f"[bold]Title:[/bold]     {task.title}",
        f"[bold]Status:[/bold]     [bold cyan]in_progress[/bold cyan] (assigned)",
        f"[bold]Priority:[/bold]   {task.priority}",
        f"[bold]Agent:[/bold]      {agent_type}",
    ]

    if task.file:
        loc = task.file
        if task.line:
            loc += f":{task.line}"
        lines.append(f"[bold]File:[/bold]       {loc}")

    if task.spec:
        lines.append("")
        lines.append(f"[bold]Spec:[/bold]")
        lines.append(task.spec[:300] + ("..." if len(task.spec) > 300 else ""))

    content = "\n".join(lines)
    console.print(Panel(content, title=f"Next task ({agent_type})", border_style="green"))
