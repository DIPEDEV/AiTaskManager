from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path

import typer

standup_app = typer.Typer(help="Generate daily standup from task history")


@standup_app.command(name="run")
def run_standup(
    agent_type: str = "coder",
    days: int = 1,
) -> None:
    """Generate daily standup from task status changes.

    Shows:
    - What you did: tasks completed (done or verify_passed)
    - What you'll do: tasks started and not finished
    - Blockers: tasks with verify_fail
    """
    from taskcli.store import TaskStore, StoreError
    from taskcli.models import TaskStatus

    try:
        store = TaskStore()
    except StoreError as e:
        typer.echo(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)

    tasks = store.load(agent_type)
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)

    yesterday_done = []
    today_started = []
    blocked = []

    for task in tasks:
        if task.finished_at:
            try:
                finished = datetime.fromisoformat(task.finished_at.replace("Z", "+00:00"))
                if finished > cutoff:
                    yesterday_done.append(task)
            except ValueError:
                pass

        if task.started_at and task.status not in (TaskStatus.DONE, TaskStatus.PENDING):
            try:
                started = datetime.fromisoformat(task.started_at.replace("Z", "+00:00"))
                if started > cutoff:
                    today_started.append(task)
            except ValueError:
                pass

        if "re-check" in task.title.lower() or task.status == TaskStatus.IN_PROGRESS:
            if task.started_at:
                today_started.append(task)

    lines = ["# Daily Standup\n"]
    lines.append(f"**Date:** {now.strftime('%Y-%m-%d')}\n")

    lines.append("\n## Yesterday (done)\n")
    if yesterday_done:
        for t in sorted(yesterday_done, key=lambda x: x.finished_at or ""):
            lines.append(f"- [{t.priority}] {t.title}")
    else:
        lines.append("- No tasks completed.")

    lines.append("\n## Today (in progress / planned)\n")
    if today_started:
        for t in sorted(today_started, key=lambda x: x.started_at or ""):
            lines.append(f"- [{t.priority}] {t.title}")
    else:
        lines.append("- No tasks started.")

    lines.append("\n## Blockers\n")
    blockers = [t for t in tasks if "re-check" in t.title.lower()]
    if blockers:
        for t in blockers:
            lines.append(f"- {t.title}")
    else:
        lines.append("- No blockers.")

    typer.echo("\n".join(lines))