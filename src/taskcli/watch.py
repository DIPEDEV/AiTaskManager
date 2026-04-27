from __future__ import annotations

import time
from pathlib import Path
from threading import Thread

try:
    from watchdog import observers
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    observers = None
    FileSystemEventHandler = object
    FileModifiedEvent = object


class TasksFileHandler(FileSystemEventHandler):
    """Handle .tasks file change events."""

    def __init__(self, callback):
        self.callback = callback
        self._last_modified = 0

    def on_modified(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix in (".tasks", "") and path.name in ("coder.tasks", "debug.tasks", "ideas.tasks"):
            now = time.time()
            if now - self._last_modified > 0.5:
                self._last_modified = now
                self.callback(str(path))


def watch_tasks(root: Path, callback, debounce: float = 0.5):
    """Watch .tasks files in root and call callback on changes."""
    if not WATCHDOG_AVAILABLE:
        raise ImportError("watchdog not installed: pip install watchdog")

    handler = TasksFileHandler(callback)
    observer = observers.Observer()
    observer.schedule(handler, str(root), recursive=False)
    observer.start()
    return observer