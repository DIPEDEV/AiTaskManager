from __future__ import annotations

from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from taskcli.store import TaskStore, StoreError

console = Console()


def run(task_id: int, agent_type: str = "coder", root: Path | None = None) -> None:
    """Show full task details including spec."""
    try:
        store = TaskStore(root) if root else TaskStore()
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    task = store.get(agent_type, task_id)
    if task is None:
        console.print(f"[red]Task {task_id} not found in {agent_type}[/red]")
        return

    lines = [
        f"[bold]ID:[/bold]        {task.id}",
        f"[bold]Title:[/bold]     {task.title}",
        f"[bold]Status:[/bold]     [{task.status_icon}] {task.status.value}",
        f"[bold]Priority:[/bold]   {task.priority}",
        f"[bold]Agent:[/bold]      {task.agent_type}",
        f"[bold]Created:[/bold]    {task.created[:19] if task.created else 'N/A'}",
    ]

    if task.section:
        lines.append(f"[bold]Section:[/bold]    {task.section}")

    if task.file:
        loc = f"         {task.file}"
        if task.line:
            loc += f":{task.line}"
        lines.append(f"[bold]File:[/bold]{loc}")

    if task.coder_ref:
        lines.append(f"[bold]Coder Ref:[/bold]  {task.coder_ref}")
    if task.debug_ref:
        lines.append(f"[bold]Debug Ref:[/bold]  {task.debug_ref}")

    if task.spec:
        spec_header = "[bold]Specification:[/bold]"
        lines.append("")
        lines.append(spec_header)
        lines.append("─" * 50)
        lines.append(task.spec)

    content = "\n".join(lines)
    console.print(Panel(content, title=f"Task {task.id} - {agent_type}", border_style="cyan"))
