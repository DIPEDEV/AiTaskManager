from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel

from taskcli.models import Task, TaskStatus
from taskcli.store import TaskStore, StoreError

console = Console()


def run(command: list[str], root: Path | None = None) -> None:
    """Execute a command and capture errors as debug tasks.

    Usage: task --debug <command...>
    """
    if not command:
        console.print("[red]No command specified. Usage: task --debug <command...>[/red]")
        return

    console.print(f"[dim]Running: {' '.join(command)}[/dim]")
    console.print()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except subprocess.TimeoutExpired:
        console.print("[red]Command timed out after 120s[/red]")
        _add_debug_task(command, "", "Command timed out after 120 seconds", root=root)
        return
    except FileNotFoundError:
        console.print(f"[red]Command not found: {command[0]}[/red]")
        return

    stdout = result.stdout
    stderr = result.stderr

    if stdout:
        console.print(stdout, end="")
    if stderr:
        console.print(f"[red]{stderr}[/red]", end="")

    if result.returncode != 0:
        console.print()
        console.print(f"[red]Exit code: {result.returncode}[/red]")

        error_info = _extract_error_info(stderr, stdout)

        task = _add_debug_task(
            command,
            error_info["file"],
            error_info["message"],
            error_info["line"],
            root=root,
        )

        panel_content = "\n".join([
            f"[bold]Task ID:[/bold] {task.id}",
            f"[bold]Title:[/bold] {task.title}",
            f"[bold]File:[/bold] {task.file}:{task.line or '?'}",
            f"[bold]Error:[/bold] {error_info['message'][:200]}",
        ])
        console.print()
        console.print(Panel(panel_content, title="Debug Task Created", border_style="yellow"))
    else:
        console.print("[green]Command completed successfully ✓[/green]")


def _extract_error_info(stderr: str, stdout: str) -> dict:
    """Extract file, line, and error message from command output."""
    text = stderr or stdout
    result = {"file": "", "line": 0, "message": text[:500] if text else "Unknown error"}

    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            continue

        if ": error:" in stripped or ": Error:" in stripped:
            result["message"] = stripped
            parts = stripped.split(":", 2)
            if len(parts) >= 1:
                result["file"] = parts[0].strip()
            if len(parts) >= 2:
                try:
                    result["line"] = int(parts[1].strip())
                except ValueError:
                    pass
            break

        if "Error" in stripped or "error" in stripped:
            if result["message"] == text[:500]:
                result["message"] = stripped
            break

    return result


def _add_debug_task(
    command: list[str],
    file: str,
    message: str,
    line: int = 0,
    root: Path | None = None,
) -> Task:
    """Add a debug task for a failed command."""
    try:
        store = TaskStore(root) if root else TaskStore()
    except StoreError:
        console.print("[red]No .tasks directory found. Run 'task init' first.[/red]")
        sys.exit(1)

    cmd_str = " ".join(command)
    task = Task(
        id=0,
        title=f"Debug: {cmd_str[:80]}",
        status=TaskStatus.PENDING,
        priority="medium",
        spec=f"Command failed: `{cmd_str}`\n\nError:\n{message}",
        file=file,
        line=line,
    )

    return store.add("debug", task)
