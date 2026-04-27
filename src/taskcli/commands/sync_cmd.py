from __future__ import annotations

from pathlib import Path

import typer

from taskcli.config import find_tasks_root, get_config_path, get_git_sync_enabled, set_git_sync_enabled
from taskcli.git_sync import GitSync, GitSyncError

sync_app = typer.Typer(help="Git sync for .tasks/ directory")


@sync_app.command()
def init(
    remote: str | None = None,
    install_driver: bool = True,
) -> None:
    """Initialize .tasks/ as a git repo with optional remote."""
    root = find_tasks_root()
    if root is None:
        raise SystemExit("No .tasks/ directory found.")

    gs = GitSync(root)
    try:
        is_new = gs.init(remote)
        if is_new:
            print("Initialized git repository in .tasks/")
        else:
            print(".tasks/ is already a git repository.")
    except GitSyncError as e:
        raise SystemExit(f"Error: {e}")

    if install_driver:
        try:
            gs.install_merge_driver()
            print("Installed custom merge driver for .tasks files.")
        except GitSyncError:
            print("Warning: could not install merge driver.")

    set_git_sync_enabled(True, get_config_path(root))
    print("Git sync enabled.")


@sync_app.command()
def push(
    remote: str = "origin",
    branch: str = "main",
) -> None:
    """Push to remote."""
    root = find_tasks_root()
    if root is None:
        raise SystemExit("No .tasks/ directory found.")

    gs = GitSync(root)
    try:
        out = gs.push(remote, branch)
        print(out or "Push successful.")
    except GitSyncError as e:
        raise SystemExit(f"Push failed: {e}")


@sync_app.command()
def pull(
    remote: str = "origin",
    branch: str = "main",
) -> None:
    """Pull from remote."""
    root = find_tasks_root()
    if root is None:
        raise SystemExit("No .tasks/ directory found.")

    gs = GitSync(root)
    try:
        out = gs.pull(remote, branch)
        print(out or "Pull successful.")
    except GitSyncError as e:
        raise SystemExit(f"Pull failed: {e}")


@sync_app.command()
def log(
    n: int = 20,
) -> None:
    """Show recent commits."""
    root = find_tasks_root()
    if root is None:
        raise SystemExit("No .tasks/ directory found.")

    gs = GitSync(root)
    try:
        out = gs.log(n)
        print(out or "No commits yet.")
    except GitSyncError as e:
        raise SystemExit(f"Error: {e}")


@sync_app.command()
def status() -> None:
    """Show git status."""
    root = find_tasks_root()
    if root is None:
        raise SystemExit("No .tasks/ directory found.")

    gs = GitSync(root)
    try:
        out = gs.status()
        print(out or "No changes.")
    except GitSyncError as e:
        raise SystemExit(f"Error: {e}")


@sync_app.command(name="enable")
def enable_cmd() -> None:
    """Enable git sync auto-commit on task mutations."""
    root = find_tasks_root()
    if root is None:
        raise SystemExit("No .tasks/ directory found.")
    set_git_sync_enabled(True, get_config_path(root))
    print("Git sync enabled.")


@sync_app.command(name="disable")
def disable_cmd() -> None:
    """Disable git sync auto-commit."""
    root = find_tasks_root()
    if root is None:
        raise SystemExit("No .tasks/ directory found.")
    set_git_sync_enabled(False, get_config_path(root))
    print("Git sync disabled.")