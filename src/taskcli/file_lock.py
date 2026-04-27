from __future__ import annotations

import fcntl
import os
import time
from contextlib import contextmanager
from pathlib import Path


class FileLockError(Exception):
    """Error acquiring file lock."""
    pass


class FileLock:
    """File-based lock using fcntl.flock.

    Provides exclusive locking for .tasks/ files to prevent concurrent
    writes from CLI, MCP, or TUI from corrupting data.
    """

    def __init__(self, path: Path | str, timeout: float = 10.0):
        self.path = Path(path)
        self.timeout = timeout

    @contextmanager
    def lock(self, exclusive: bool = True):
        """Context manager for holding a file lock.

        Args:
            exclusive: If True, acquire exclusive (write) lock.
                      If False, acquire shared (read) lock.
        """
        lock_path = self._lock_path()
        lock_path.parent.mkdir(parents=True, exist_ok=True)

        lock_fd = os.open(str(lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            self._acquire(lock_fd, exclusive)
            yield
        finally:
            self._release(lock_fd)
            os.close(lock_fd)

    def _lock_path(self) -> Path:
        """Return path to lock file for a given resource path."""
        return self.path.parent / ".locks" / f"{self.path.name}.lock"

    def _acquire(self, fd: int, exclusive: bool) -> None:
        """Acquire flock, raising FileLockError on timeout."""
        start = time.monotonic()
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX if exclusive else fcntl.LOCK_SH)
                return
            except BlockingIOError:
                if time.monotonic() - start >= self.timeout:
                    raise FileLockError(
                        f"Could not acquire lock on '{self.path}' after {self.timeout}s"
                    )
                time.sleep(0.05)

    def _release(self, fd: int) -> None:
        """Release flock."""
        fcntl.flock(fd, fcntl.LOCK_UN)


@contextmanager
def locked(path: Path | str, exclusive: bool = True, timeout: float = 10.0):
    """Context manager shortcut: acquire lock on a path."""
    lock = FileLock(Path(path), timeout=timeout)
    with lock.lock(exclusive=exclusive):
        yield


__all__ = ["FileLock", "FileLockError", "locked"]