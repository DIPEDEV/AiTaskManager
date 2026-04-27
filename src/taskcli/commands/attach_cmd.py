from __future__ import annotations

import shutil
from pathlib import Path

import typer

attach_app = typer.Typer(help="Attach files to tasks")


def _blobs_dir(root: Path) -> Path:
    return root / ".tasks" / "blobs"


@attach_app.command(name="add")
def add_attachment(
    task_id: int = typer.Argument(..., help="Task ID"),
    file_path: str = typer.Argument(..., help="Path to file to attach"),
    agent_type: str = "coder",
) -> None:
    """Attach a file to a task. File is copied to .tasks/blobs/."""
    from taskcli.store import TaskStore, StoreError
    from rich.console import Console

    console = Console()

    try:
        store = TaskStore()
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Abort()

    task = store.get(agent_type, task_id)
    if task is None:
        console.print(f"[red]Task {task_id} not found in {agent_type}[/red]")
        raise typer.Abort()

    src = Path(file_path).expanduser().resolve()
    if not src.exists():
        console.print(f"[red]File not found: {src}[/red]")
        raise typer.Abort()

    blobs = _blobs_dir(Path.cwd())
    blobs.mkdir(parents=True, exist_ok=True)

    dest_name = f"{agent_type}-{task_id}-{src.name}"
    dest = blobs / dest_name
    shutil.copy2(src, dest)

    attachments = list(task.attachments) + [str(dest)]
    store.update(agent_type, task_id, attachments=attachments)

    console.print(f"[green]Attached {src.name} to task {task_id} (saved as {dest_name})[/green]")