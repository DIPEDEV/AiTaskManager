from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

import typer

from taskcli.store import TaskStore, StoreError
from taskcli.models import TaskStatus

due_app = typer.Typer(help="Due date and recurrence commands")


@due_app.command(name="today")
def today_cmd(
    agent_type: str = "coder",
) -> None:
    """List tasks due today or overdue."""
    try:
        store = TaskStore()
    except StoreError as e:
        raise SystemExit(f"Error: {e}")

    tasks = store.list_tasks(agent_type, status=TaskStatus.PENDING)
    now = datetime.now(timezone.utc)
    today_tasks = []
    overdue_tasks = []

    for task in tasks:
        if not task.due:
            continue
        try:
            due_dt = datetime.fromisoformat(task.due.replace("Z", "+00:00"))
            if due_dt.date() == now.date():
                today_tasks.append(task)
            elif due_dt < now:
                overdue_tasks.append(task)
        except ValueError:
            continue

    if overdue_tasks:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        console.print("[bold red]Overdue[/bold red]")
        table = Table()
        table.add_column("ID")
        table.add_column("Title")
        table.add_column("Due")
        for t in overdue_tasks:
            table.add_row(str(t.id), t.title, t.due)
        console.print(table)

    if today_tasks:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        console.print("[bold green]Due today[/bold green]")
        table = Table()
        table.add_column("ID")
        table.add_column("Title")
        table.add_column("Due")
        for t in today_tasks:
            table.add_row(str(t.id), t.title, t.due)
        console.print(table)

    if not overdue_tasks and not today_tasks:
        print("No tasks due today or overdue.")


@due_app.command(name="overdue")
def overdue_cmd(
    agent_type: str = "coder",
) -> None:
    """List overdue tasks."""
    try:
        store = TaskStore()
    except StoreError as e:
        raise SystemExit(f"Error: {e}")

    tasks = store.list_tasks(agent_type, status=TaskStatus.PENDING)
    now = datetime.now(timezone.utc)
    overdue = []

    for task in tasks:
        if not task.due:
            continue
        try:
            due_dt = datetime.fromisoformat(task.due.replace("Z", "+00:00"))
            if due_dt < now:
                overdue.append(task)
        except ValueError:
            continue

    if not overdue:
        print("No overdue tasks.")
        return

    from rich.console import Console
    from rich.table import Table
    console = Console()
    console.print("[bold red]Overdue tasks[/bold red]")
    table = Table()
    table.add_column("ID")
    table.add_column("Title")
    table.add_column("Due")
    for t in sorted(overdue, key=lambda x: x.due):
        table.add_row(str(t.id), t.title, t.due)
    console.print(table)