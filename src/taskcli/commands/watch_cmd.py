from __future__ import annotations

import sys
import time
from pathlib import Path

import typer

watch_app = typer.Typer(help="Watch .tasks files and re-render TUI on changes")


@watch_app.command(name="run")
def run_watch(
    debounce: float = 0.5,
) -> None:
    """Watch .tasks/ files and print changes to stdout.

    Useful for triggering external tools when tasks change.
    """
    from taskcli.config import find_tasks_root
    from taskcli.watch import watch_tasks, WATCHDOG_AVAILABLE

    if not WATCHDOG_AVAILABLE:
        typer.echo("[red]Error: watchdog not installed. Run: pip install watchdog[/red]")
        raise typer.Exit(1)

    root = find_tasks_root()
    if root is None:
        typer.echo("[red]No .tasks/ directory found.[/red]")
        raise typer.Exit(1)

    typer.echo(f"Watching {root} for changes (Ctrl+C to stop)...")

    changed = False

    def on_change(path: str):
        nonlocal changed
        changed = True
        print(f"[task] {path} changed at {time.strftime('%H:%M:%S')}")

    observer = watch_tasks(root, on_change, debounce)

    try:
        while True:
            time.sleep(1)
            if changed:
                changed = False
    except KeyboardInterrupt:
        observer.stop()
        typer.echo("\nStopped.")