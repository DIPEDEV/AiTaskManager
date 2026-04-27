from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table

from taskcli.telemetry import get_stats, is_telemetry_enabled

console = Console()

app = typer.Typer(help="Show telemetry and stats (opt-in)")


@app.command()
def stats(
    root: Optional[Path] = None,
) -> None:
    """Show local telemetry dashboard."""
    if not is_telemetry_enabled(root):
        console.print("[yellow]Telemetry is disabled.[/yellow]")
        console.print("Enable with: task config set telemetry true")
        return

    data = get_stats(root)

    console.print("\n[bold cyan]TaskFlow Telemetry Dashboard[/bold cyan]\n")

    summary = Table(show_header=False, box=None)
    summary.add_column("Metric", style="bold")
    summary.add_column("Value")
    summary.add_row("Total tasks completed", str(data["total_tasks"]))
    summary.add_row("Verifications passed", str(data["total_verified"]))
    summary.add_row("Verifications failed", str(data["total_failed"]))
    summary.add_row("Avg duration (minutes)", str(data["avg_duration_minutes"]))
    console.print(summary)

    if data["agent_stats"]:
        console.print("\n[bold]Per-Agent Stats:[/bold]")
        table = Table()
        table.add_column("Agent", style="cyan")
        table.add_column("Done", justify="right")
        table.add_column("Verified", justify="right")
        table.add_column("Failed", justify="right")
        table.add_column("Total Minutes", justify="right")

        for agent, stats in data["agent_stats"].items():
            table.add_row(
                agent,
                str(stats["done"]),
                str(stats["verified"]),
                str(stats["failed"]),
                str(stats["total_minutes"]),
            )
        console.print(table)

    console.print("\n[dim]Data stored locally at .telemetry[/dim]")


if __name__ == "__main__":
    app()