from __future__ import annotations

import subprocess
from pathlib import Path
from datetime import datetime, timezone


class GitSyncError(Exception):
    """Error during git sync operation."""
    pass


class GitSync:
    """Automatic git sync for .tasks/ directory.

    Provides auto-commit on save, push/pull sync, and a custom merge
    driver for .tasks plain-text files.
    """

    def __init__(self, root: Path):
        self.root = root

    # ── Repo management ──

    @property
    def is_repo(self) -> bool:
        """Check if .tasks/ is a git repo."""
        git_dir = self.root / ".git"
        return git_dir.is_dir()

    def init(self, remote: str | None = None) -> bool:
        """Initialize .tasks/ as a git repository.

        Returns True if newly initialized, False if already a repo.
        """
        if self.is_repo:
            return False
        self._run("init", "-q")
        if remote:
            self._run("remote", "add", "origin", remote)
        return True

    # ── Auto-commit ──

    def commit(self, message: str | None = None) -> str | None:
        """Stage all changes and commit. Returns commit hash or None."""
        if not self.is_repo:
            return None

        status = self._run("status", "--porcelain", capture=True)
        if not status.strip():
            return None

        self._run("add", "-A")
        msg = message or "auto: task mutation at " + datetime.now(timezone.utc).isoformat()
        self._run("commit", "-m", msg)
        return self._run("rev-parse", "HEAD", capture=True).strip()

    # ── Sync ──

    def push(self, remote: str = "origin", branch: str = "main") -> str:
        """Push to remote. Returns output or raises."""
        if not self.is_repo:
            raise GitSyncError(".tasks/ is not a git repo. Run 'task sync init' first.")
        return self._run("push", remote, branch)

    def pull(self, remote: str = "origin", branch: str = "main") -> str:
        """Pull from remote. Returns output or raises."""
        if not self.is_repo:
            raise GitSyncError(".tasks/ is not a git repo. Run 'task sync init' first.")
        return self._run("pull", "--rebase", remote, branch)

    def log(self, n: int = 20) -> str:
        """Show recent commits."""
        if not self.is_repo:
            raise GitSyncError(".tasks/ is not a git repo.")
        return self._run("log", f"--oneline", f"-{n}", capture=True)

    def status(self) -> str:
        """Show git status."""
        if not self.is_repo:
            raise GitSyncError(".tasks/ is not a git repo.")
        return self._run("status", "--short", capture=True)

    # ── Custom merge driver ──

    def install_merge_driver(self) -> None:
        """Install a custom merge driver for .tasks files in git config.

        The merge driver uses simple last-write-wins by union of task
        blocks — tasks with the same ID keep the version from the current
        branch, new task IDs are added from both sides.
        """
        if not self.is_repo:
            raise GitSyncError(".tasks/ is not a git repo.")

        gitattributes = self.root / ".gitattributes"
        if not gitattributes.exists():
            gitattributes.write_text("*.tasks merge=union\n")

        try:
            self._run("config", "merge.union.name", "Union merge for .tasks files")
            self._run("config", "merge.union.driver", "task-merge-driver %A %O %B %L")
        except GitSyncError:
            pass

        gitignore = self.root / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("tasks.db\n*.jsonl\n.merge_*\n")

    # ── Internal ──

    def _run(self, *args: str, capture: bool = False) -> str:
        """Run a git command in the .tasks/ directory."""
        cmd = ["git", "-C", str(self.root), *args]
        try:
            if capture:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=True
                )
                return result.stdout
            else:
                subprocess.run(cmd, check=True, capture_output=True, text=True)
                return ""
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.strip() if e.stderr else str(e)
            raise GitSyncError(f"git {' '.join(args)}: {stderr}") from e
