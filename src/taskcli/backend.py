from __future__ import annotations

import json
import sqlite3
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from taskcli.models import Task, TaskStatus
from taskcli.parser import parse_tasks_file, write_tasks_file


class StorageBackend(ABC):
    """Abstract storage backend for .tasks files.

    Allows swapping storage implementations (plain-text, SQLite, JSONL)
    without modifying CLI, TUI, or MCP server.
    """

    @abstractmethod
    def load(self, agent_type: str) -> list[Task]:
        """Load all tasks for an agent type."""

    @abstractmethod
    def save(self, agent_type: str, tasks: list[Task]) -> None:
        """Save tasks for an agent type."""

    @abstractmethod
    def exists(self, agent_type: str) -> bool:
        """Check if storage for an agent type exists."""

    def ensure(self, agent_type: str) -> None:
        """Ensure storage for agent type is initialized."""


class LockedBackend(StorageBackend):
    """Wrapper that adds file locking to any StorageBackend.

    Uses exclusive locks on the agent's task file during load/save
    to prevent concurrent writes from CLI, MCP, or TUI.
    """

    def __init__(self, inner: StorageBackend, lock_dir: Path | None = None):
        self.inner = inner
        self._lock_dir = lock_dir

    def _lock_path(self, agent_type: str) -> Path:
        lock_root = self._lock_dir or getattr(self.inner, "root", Path.cwd())
        return lock_root / ".locks" / f"{agent_type}.lock"

    def _with_lock(self, agent_type: str, exclusive: bool, fn):
        """Execute fn while holding an exclusive/shared lock."""
        from taskcli.file_lock import FileLock
        lock_path = self._lock_path(agent_type)
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock = FileLock(lock_path, timeout=10.0)
        with lock.lock(exclusive=exclusive):
            return fn()

    def load(self, agent_type: str) -> list[Task]:
        return self._with_lock(agent_type, exclusive=False, fn=lambda: self.inner.load(agent_type))

    def save(self, agent_type: str, tasks: list[Task]) -> None:
        return self._with_lock(agent_type, exclusive=True, fn=lambda: self.inner.save(agent_type, tasks))

    def exists(self, agent_type: str) -> bool:
        return self._with_lock(agent_type, exclusive=False, fn=lambda: self.inner.exists(agent_type))

    def ensure(self, agent_type: str) -> None:
        return self._with_lock(agent_type, exclusive=True, fn=lambda: self.inner.ensure(agent_type))


class PlainTextBackend(StorageBackend):
    """Current file-based .tasks storage using parser.py."""

    def __init__(self, root: Path):
        self.root = root

    def _filepath(self, agent_type: str) -> Path:
        return self.root / f"{agent_type}.tasks"

    def load(self, agent_type: str) -> list[Task]:
        filepath = self._filepath(agent_type)
        return parse_tasks_file(str(filepath))

    def save(self, agent_type: str, tasks: list[Task]) -> None:
        filepath = self._filepath(agent_type)
        header = f"{agent_type}.tasks - Tasks for {agent_type} agent"
        write_tasks_file(str(filepath), tasks, header)

    def exists(self, agent_type: str) -> bool:
        return self._filepath(agent_type).exists()

    def ensure(self, agent_type: str) -> None:
        filepath = self._filepath(agent_type)
        if not filepath.exists():
            header = f"{agent_type}.tasks - Tasks for {agent_type} agent"
            write_tasks_file(str(filepath), [], header)


class JSONLBackend(StorageBackend):
    """JSON Lines storage — one task per line, human-readable JSON."""

    def __init__(self, root: Path):
        self.root = root

    def _filepath(self, agent_type: str) -> Path:
        return self.root / f"{agent_type}.jsonl"

    def _task_to_dict(self, task: Task) -> dict[str, Any]:
        return {
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "priority": task.priority,
            "spec": task.spec,
            "file": task.file,
            "line": task.line,
            "created": task.created,
            "agent_type": task.agent_type,
            "section": task.section,
            "coder_ref": task.coder_ref,
            "debug_ref": task.debug_ref,
            "source_agent": task.source_agent,
        }

    def _dict_to_task(self, d: dict[str, Any]) -> Task:
        return Task(
            id=d["id"],
            title=d.get("title", ""),
            status=TaskStatus(d.get("status", "pending")),
            priority=d.get("priority", "medium"),
            spec=d.get("spec", ""),
            file=d.get("file", ""),
            line=d.get("line", 0),
            created=d.get("created", ""),
            agent_type=d.get("agent_type", "coder"),
            section=d.get("section", ""),
            coder_ref=d.get("coder_ref", 0),
            debug_ref=d.get("debug_ref", 0),
            source_agent=d.get("source_agent", ""),
        )

    def load(self, agent_type: str) -> list[Task]:
        filepath = self._filepath(agent_type)
        if not filepath.exists():
            return []
        tasks = []
        with open(filepath) as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        tasks.append(self._dict_to_task(json.loads(line)))
                    except (json.JSONDecodeError, KeyError):
                        continue
        return tasks

    def save(self, agent_type: str, tasks: list[Task]) -> None:
        filepath = self._filepath(agent_type)
        with open(filepath, "w") as f:
            for task in tasks:
                f.write(json.dumps(self._task_to_dict(task), ensure_ascii=False) + "\n")

    def exists(self, agent_type: str) -> bool:
        return self._filepath(agent_type).exists()

    def ensure(self, agent_type: str) -> None:
        filepath = self._filepath(agent_type)
        if not filepath.exists():
            filepath.write_text("")


class SQLiteBackend(StorageBackend):
    """SQLite storage — single database file, efficient for large volumes."""

    SCHEMA_VERSION = 1

    def __init__(self, root: Path):
        self.root = root
        self._db_path = root / "tasks.db"
        self._init_db()
        self._migrate()

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(str(self._db_path))
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA foreign_keys=ON")
        return db

    def _init_db(self) -> None:
        db = self._connect()
        try:
            db.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER NOT NULL,
                    agent_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    priority TEXT NOT NULL DEFAULT 'medium',
                    spec TEXT NOT NULL DEFAULT '',
                    file TEXT NOT NULL DEFAULT '',
                    line INTEGER NOT NULL DEFAULT 0,
                    created TEXT NOT NULL DEFAULT '',
                    section TEXT NOT NULL DEFAULT '',
                    coder_ref INTEGER NOT NULL DEFAULT 0,
                    debug_ref INTEGER NOT NULL DEFAULT 0,
                    source_agent TEXT NOT NULL DEFAULT '',
                    parent_id INTEGER NOT NULL DEFAULT 0,
                    blocked_by TEXT NOT NULL DEFAULT '',
                    tags TEXT NOT NULL DEFAULT '',
                    due TEXT NOT NULL DEFAULT '',
                    recur TEXT NOT NULL DEFAULT '',
                    estimate_min INTEGER NOT NULL DEFAULT 0,
                    actual_min INTEGER NOT NULL DEFAULT 0,
                    started_at TEXT NOT NULL DEFAULT '',
                    finished_at TEXT NOT NULL DEFAULT '',
                    attachments TEXT NOT NULL DEFAULT '',
                    PRIMARY KEY (agent_type, id)
                )
            """)
            db.execute("""
                CREATE TABLE IF NOT EXISTS schema_info (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                )
            """)
            db.commit()
        finally:
            db.close()

    def _migrate(self) -> None:
        db = self._connect()
        try:
            row = db.execute(
                "SELECT value FROM schema_info WHERE key = 'version'"
            ).fetchone()
            version = int(row["value"]) if row else 0

            migrations = [
                lambda d: d.execute("ALTER TABLE tasks ADD COLUMN parent_id INTEGER NOT NULL DEFAULT 0"),
                lambda d: d.execute("ALTER TABLE tasks ADD COLUMN blocked_by TEXT NOT NULL DEFAULT ''"),
                lambda d: d.execute("ALTER TABLE tasks ADD COLUMN tags TEXT NOT NULL DEFAULT ''"),
                lambda d: d.execute("ALTER TABLE tasks ADD COLUMN due TEXT NOT NULL DEFAULT ''"),
                lambda d: d.execute("ALTER TABLE tasks ADD COLUMN recur TEXT NOT NULL DEFAULT ''"),
            ]
            for i, migration in enumerate(migrations[version:], start=version + 1):
                try:
                    migration(db)
                except Exception:
                    pass
                db.execute("INSERT OR REPLACE INTO schema_info (key, value) VALUES ('version', ?)", (str(i),))
                db.commit()
        finally:
            db.close()

    def load(self, agent_type: str) -> list[Task]:
        db = self._connect()
        try:
            rows = db.execute(
                "SELECT * FROM tasks WHERE agent_type = ? ORDER BY id",
                (agent_type,),
            ).fetchall()
            tasks = []
            for row in rows:
                blocked_by_str = row["blocked_by"] or ""
                blocked_by = [int(x) for x in blocked_by_str.split(",") if blocked_by_str]
                tags_str = row["tags"] or ""
                tags = [x for x in tags_str.split(",") if x]
                tasks.append(Task(
                    id=row["id"],
                    title=row["title"],
                    status=TaskStatus(row["status"]),
                    priority=row["priority"],
                    spec=row["spec"],
                    file=row["file"],
                    line=row["line"],
                    created=row["created"],
                    agent_type=row["agent_type"],
                    section=row["section"],
                    coder_ref=row["coder_ref"],
                    debug_ref=row["debug_ref"],
                    source_agent=row["source_agent"],
                    parent_id=row["parent_id"],
                    blocked_by=blocked_by,
                    tags=tags,
                    due=row["due"],
                    recur=row["recur"],
                    estimate_min=row["estimate_min"],
                    actual_min=row["actual_min"],
                    started_at=row["started_at"],
                    finished_at=row["finished_at"],
                    attachments=[x for x in row["attachments"].split(",") if x],
                ))
            return tasks
        finally:
            db.close()

    def save(self, agent_type: str, tasks: list[Task]) -> None:
        db = self._connect()
        try:
            db.execute("DELETE FROM tasks WHERE agent_type = ?", (agent_type,))
            for task in tasks:
                db.execute(
                    """INSERT INTO tasks
                       (id, agent_type, title, status, priority, spec, file, line,
                        created, section, coder_ref, debug_ref, source_agent,
                        parent_id, blocked_by, tags, due, recur,
                        estimate_min, actual_min, started_at, finished_at, attachments)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        task.id, agent_type, task.title,
                        task.status.value, task.priority, task.spec,
                        task.file, task.line, task.created or "",
                        task.section, task.coder_ref, task.debug_ref,
                        task.source_agent,
                        task.parent_id,
                        ",".join(str(x) for x in task.blocked_by),
                        ",".join(task.tags),
                        task.due, task.recur,
                        task.estimate_min, task.actual_min,
                        task.started_at, task.finished_at,
                        ",".join(task.attachments),
                    ),
                )
            db.commit()
        finally:
            db.close()

    def exists(self, agent_type: str) -> bool:
        db = self._connect()
        try:
            row = db.execute(
                "SELECT 1 FROM tasks WHERE agent_type = ? LIMIT 1",
                (agent_type,),
            ).fetchone()
            return row is not None
        finally:
            db.close()

    def ensure(self, agent_type: str) -> None:
        self._init_db()


def create_backend(backend_type: str, root: Path, lock_for_writes: bool = True) -> StorageBackend:
    """Factory for creating a storage backend by type name."""
    backends = {
        "plaintext": PlainTextBackend,
        "jsonl": JSONLBackend,
        "sqlite": SQLiteBackend,
    }
    cls = backends.get(backend_type, PlainTextBackend)
    inner = cls(root)
    if lock_for_writes:
        return LockedBackend(inner, lock_dir=root)
    return inner


__all__ = [
    "StorageBackend",
    "LockedBackend",
    "PlainTextBackend",
    "JSONLBackend",
    "SQLiteBackend",
    "create_backend",
]
