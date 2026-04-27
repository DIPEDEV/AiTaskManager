from __future__ import annotations

import typer

from taskcli.importers import import_github_issues_cmd, ImporterError

import_app = typer.Typer(help="Import issues from external systems")


@import_app.command(name="github")
def github_cmd(
    repo: str = "",
    state: str = "open",
    agent_type: str = "coder",
) -> None:
    """Import GitHub issues as tasks.

    Usage: task import github --repo owner/repo
    """
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if not repo:
        console.print("[red]Error: --repo required (format: owner/repo)[/red]")
        return

    try:
        result = import_github_issues_cmd(repo, state, agent_type)
    except ImporterError as e:
        console.print(f"[red]Import failed: {e}[/red]")
        return

    table = Table(title=f"Imported {result['imported']} issues")
    table.add_column("ID", style="dim")
    table.add_column("Title")
    for t in result["tasks"]:
        table.add_row(str(t["id"]), t["title"][:60])
    console.print(table)
    console.print(f"[green]Imported {result['imported']} tasks.[/green]")