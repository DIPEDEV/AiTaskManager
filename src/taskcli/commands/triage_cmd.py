from __future__ import annotations

import typer

from taskcli.triage import triage_inbox
from taskcli.store import StoreError

triage_app = typer.Typer(help="LLM-based task triage")


@triage_app.command(name="run")
def run_cmd(
    agent_type: str = "coder",
    auto: bool = False,
) -> None:
    """Run LLM triage on inbox tasks."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if not auto:
        console.print("[dim]Usage: task triage run --auto (to triage inbox tasks)[/dim]")
        return

    try:
        results = triage_inbox(agent_type)
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    if not results:
        console.print("[dim]No inbox tasks to triage.[/dim]")
        return

    table = Table(title="Triage results")
    table.add_column("Task ID")
    table.add_column("New Section", style="green")
    for task_id, section in results.items():
        table.add_row(task_id, section)
    console.print(table)
    console.print(f"[dim]{len(results)} task(s) triaged.[/dim]")