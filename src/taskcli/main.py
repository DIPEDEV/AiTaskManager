from __future__ import annotations

import sys
from pathlib import Path
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
    mcp_cmd,
    next_cmd,
    pass_cmd,
    show_cmd,
)
from taskcli.commands.sync_cmd import sync_app
from taskcli.commands.due_cmd import due_app
from taskcli.commands.triage_cmd import triage_app
from taskcli.commands.find_cmd import find_app
from taskcli.commands.import_cmd import import_app
from taskcli.commands.attach_cmd import attach_app
from taskcli.commands.watch_cmd import watch_app
from taskcli.commands.standup_cmd import standup_app
from taskcli.commands.quick_cmd import quick_app
from taskcli.config import resolve_root
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
app.add_typer(sync_app, name="sync")
app.add_typer(due_app, name="due")
app.add_typer(triage_app, name="triage")
app.add_typer(find_app, name="find")
app.add_typer(import_app, name="import")
app.add_typer(attach_app, name="attach")
app.add_typer(watch_app, name="watch")
app.add_typer(standup_app, name="standup")


def _resolve_root(ctx: Context) -> Path | None:
    if ctx.obj and ctx.obj.get("global"):
        return resolve_root("global")
    return None


@app.callback(invoke_without_command=True)
def main_callback(
    ctx: Context,
    global_mode: Annotated[
        bool,
        typer.Option("-g", "--global", help="Use global .tasks directory (~/.tasks)"),
    ] = False,
) -> None:
    """CLI para manejar tasks con AI de forma efectiva.

    Run 'task --help' for available commands.
    """
    ctx.ensure_object(dict)
    ctx.obj["global"] = global_mode

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
            ("sync", "Git sync (init, push, pull, log, enable/disable)"),
            ("tui", "Launch interactive TUI"),
            ("mcp", "Start MCP stdio server"),
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
    init_mod.run(Path(path) if path else None)


@app.command()
def add(
    ctx: Context,
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
    section: Annotated[
        str,
        typer.Option("-S", "--section", help="Task section for grouping"),
    ] = "",
    auto_spec: Annotated[
        bool,
        typer.Option("--auto-spec", help="Call Anthropic API to generate spec from title"),
    ] = False,
    tag: Annotated[
        str,
        typer.Option("--tag", help="Comma-separated tags for the task"),
    ] = "",
    due: Annotated[
        str,
        typer.Option("--due", help="ISO 8601 due date (e.g. 2026-04-30 or 2026-04-30T14:00)"),
    ] = "",
    recur: Annotated[
        str,
        typer.Option("--recur", help="Recurrence: daily, weekly:mon, hourly, ..."),
    ] = "",
    estimate_min: Annotated[
        int,
        typer.Option("-e", "--estimate", help="Estimated minutes to complete"),
    ] = 0,
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
        section=section,
        root=_resolve_root(ctx),
        auto_spec=auto_spec,
        tag=tag,
        due=due,
        recur=recur,
        estimate_min=estimate_min,
    )


@app.command()
def list(
    ctx: Context,
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
    section: Annotated[
        str,
        typer.Option("-S", "--section", help="Filter by section"),
    ] = "",
    tag: Annotated[
        str,
        typer.Option("--tag", help="Filter by tag"),
    ] = "",
) -> None:
    """List tasks."""
    list_cmd.run(
        agent_type=agent_type,
        status=status,
        all_agents=all_agents,
        section=section,
        tag=tag,
        root=_resolve_root(ctx),
    )


@app.command()
def show(
    ctx: Context,
    task_id: Annotated[int, typer.Argument(help="Task ID")],
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type"),
    ] = "coder",
) -> None:
    """Show full task details including specification."""
    show_cmd.run(task_id=task_id, agent_type=agent_type, root=_resolve_root(ctx))


@app.command()
def next(
    ctx: Context,
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type to find next task for"),
    ] = "coder",
    short: Annotated[
        bool,
        typer.Option("-s", "--short", help="Output single-line format for statusLine integration"),
    ] = False,
) -> None:
    """Get the next pending task and mark it as in_progress."""
    next_cmd.run(agent_type=agent_type, root=_resolve_root(ctx), short=short)


@app.command()
def done(
    ctx: Context,
    task_id: Annotated[int, typer.Argument(help="Task ID")],
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type"),
    ] = "coder",
) -> None:
    """Mark a task as done. Coder tasks move to debug for verification."""
    done_mod.run(task_id=task_id, agent_type=agent_type, root=_resolve_root(ctx))


@app.command()
def verify_pass(
    ctx: Context,
    task_id: Annotated[int, typer.Argument(help="Debug task ID")],
    agent_type: Annotated[
        str,
        typer.Option("-t", "--type", help="Agent type"),
    ] = "debug",
) -> None:
    """Pass debug verification: mark debug + coder task as done."""
    pass_cmd.run(task_id=task_id, agent_type=agent_type, root=_resolve_root(ctx))


@app.command()
def verify_fail(
    ctx: Context,
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
    fail_cmd.run(task_id=task_id, message=message, agent_type=agent_type, root=_resolve_root(ctx))


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
    debug_mod.run(args, root=_resolve_root(ctx))


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
def tui(
    ctx: Context,
) -> None:
    """Launch the interactive TUI."""
    run_tui(root=_resolve_root(ctx))


@app.command()
def mcp(
    scope: Annotated[
        str,
        typer.Option(
            "--scope",
            help="Scope: global, project, or auto",
        ),
    ] = "global",
    root: Annotated[
        Optional[str],
        typer.Option(
            "--root",
            help="Custom root path for .tasks directory",
        ),
    ] = None,
) -> None:
    """Start the MCP (Model Context Protocol) stdio server."""
    mcp_cmd.run(scope=scope, root=root)


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
