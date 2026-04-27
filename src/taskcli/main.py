from __future__ import annotations

import sys
from typing import Annotated, Optional

import typer
from rich.console import Console
from typer import Context

from taskcli.commands import (
    add_cmd,
    agent_cmd,
    debug as debug_mod,
    done as done_mod,
    fail_cmd,
    init as init_mod,
    list_cmd,
    next_cmd,
    pass_cmd,
    show_cmd,
)
from taskcli.tui.app import run_tui

console = Console()

app = typer.Typer(
    name="task",
    help="CLI para manejar tasks con AI de forma efectiva.",
    no_args_is_help=False,
    invoke_without_command=True,
)

agent_app = typer.Typer(
    help="Manage agent types (coder, debug, tester, ...)"
)
app.add_typer(agent_app, name="agent")


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: Context,
) -> None:
    """CLI para manejar tasks con AI de forma efectiva.

    Run 'task --help' for available commands.
    """
    if ctx.invoked_subcommand is None:
        console.print("[bold cyan]task[/bold cyan] - CLI para manejar tasks con AI")
        console.print()
        console.print("[bold]Commands:[/bold]")
        commands = [
            ("init", "Initialize .tasks directory"),
            ("agent", "Manage agent types (add/list)"),
            ("add", "Add a new task"),
            ("list", "List tasks"),
            ("show", "Show task details"),
            ("next", "Get next pending task"),
            ("done", "Mark task as done (coder→debug transition)"),
            ("verify-pass", "Pass debug verification"),
            ("verify-fail", "Fail debug verification → new coder task"),
            ("debug", "Execute command, capture errors as debug tasks"),
            ("tui", "Launch interactive TUI"),
        ]
        for name, desc in commands:
            console.print(f"  [green]{name:<12}[/green] {desc}")
        console.print()
        console.print("[dim]Run 'task --help' for detailed options.[/dim]")


@app.command()
def init(
    path: Annotated[
        Optional[str],
        typer.Option("-p", "--path", help="Path to initialize .tasks directory"),
    ] = None,
) -> None:
    """Initialize .tasks directory in the current or specified path."""
    from pathlib import Path

    init_mod.run(Path(path) if path else None)


@app.command()
def add(
    title: Annotated[str, typer.Argument(help="Task title")],
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type (coder, debug, ...)"),
    ] = "coder",
    priority: Annotated[
        str,
        typer.Option("-p", "--priority", help="Priority: high, medium, low"),
    ] = "medium",
    file: Annotated[
        str,
        typer.Option("-f", "--file", help="File path related to the task"),
    ] = "",
    line: Annotated[
        int,
        typer.Option("-l", "--line", help="Line number"),
    ] = 0,
    spec: Annotated[
        str,
        typer.Option("-s", "--spec", help="Multi-line specification/context for AI"),
    ] = "",
    description: Annotated[
        str,
        typer.Option("-d", "--description", help="Short description (fallback for spec)"),
    ] = "",
) -> None:
    """Add a new task."""
    add_cmd.run(
        title=title,
        agent_type=agent_type,
        priority=priority,
        file=file,
        line=line,
        spec=spec,
        description=description,
    )


@app.command()
def list(
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Filter by agent type"),
    ] = "",
    status: Annotated[
        str,
        typer.Option("-s", "--status", help="Filter by status"),
    ] = "",
    all_agents: Annotated[
        bool,
        typer.Option("-a", "--all", help="Show tasks from all agent types"),
    ] = False,
) -> None:
    """List tasks."""
    list_cmd.run(
        agent_type=agent_type,
        status=status,
        all_agents=all_agents,
    )


@app.command()
def show(
    task_id: Annotated[int, typer.Argument(help="Task ID")],
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type"),
    ] = "coder",
) -> None:
    """Show full task details including specification."""
    show_cmd.run(task_id=task_id, agent_type=agent_type)


@app.command()
def next(
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type to find next task for"),
    ] = "coder",
) -> None:
    """Get the next pending task and mark it as in_progress."""
    next_cmd.run(agent_type=agent_type)


@app.command()
def done(
    task_id: Annotated[int, typer.Argument(help="Task ID")],
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type"),
    ] = "coder",
) -> None:
    """Mark a task as done. Coder tasks move to debug for verification."""
    done_mod.run(task_id=task_id, agent_type=agent_type)


@app.command()
def verify_pass(
    task_id: Annotated[int, typer.Argument(help="Debug task ID")],
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type"),
    ] = "debug",
) -> None:
    """Pass debug verification: mark debug + coder task as done."""
    pass_cmd.run(task_id=task_id, agent_type=agent_type)


@app.command()
def verify_fail(
    task_id: Annotated[int, typer.Argument(help="Debug task ID")],
    message: Annotated[
        str,
        typer.Option("-m", "--message", help="Failure reason / feedback for coder"),
    ] = "Verification failed",
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type"),
    ] = "debug",
) -> None:
    """Fail debug verification: create new coder task with feedback."""
    fail_cmd.run(task_id=task_id, message=message, agent_type=agent_type)


@app.command(
    name="debug",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
def debug_cmd_wrapper(
    ctx: Context,
) -> None:
    """Execute a command and capture errors as debug tasks.

    Usage: task debug <command...>
    Example: task debug love .
    """
    args = ctx.args
    if not args:
        console.print("[red]Usage: task debug <command...>[/red]")
        return
    debug_mod.run(args)


@agent_app.command()
def add(
    name: Annotated[str, typer.Argument(help="Agent type name (e.g., tester, docs)")],
    description: Annotated[
        str,
        typer.Option("-d", "--description", help="Agent description"),
    ] = "",
    pipeline_to: Annotated[
        str,
        typer.Option("--pipeline-to", help="Agent type to pipeline tasks to on done"),
    ] = "",
) -> None:
    """Add a new agent type and create its .tasks file."""
    agent_cmd.add(name=name, description=description, pipeline_to=pipeline_to)


@agent_app.command(name="list")
def list_agents() -> None:
    """List all configured agent types."""
    agent_cmd.list_agents()


@app.command()
def tui() -> None:
    """Launch the interactive TUI."""
    run_tui()


def entry():
    """Entry point — handles --debug before typer processing."""
    args = sys.argv[1:]

    if "--debug" in args:
        idx = args.index("--debug")
        cmd = args[idx + 1 :]
        if not cmd:
            console.print("[red]Usage: task --debug <command...>[/red]")
            sys.exit(1)
        debug_mod.run(cmd)
        return

    app()


if __name__ == "__main__":
    entry()
