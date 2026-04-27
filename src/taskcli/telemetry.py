from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from taskcli.config import find_tasks_root, _read_config


@dataclass
class TaskEvent:
    timestamp: str
    event: str
    agent_type: str
    task_id: int
    title: str
    duration_minutes: Optional[int] = None
    priority: str = "medium"
    tags: list[str] = field(default_factory=list)


@dataclass
class TelemetryStore:
    root: Path
    events: list[TaskEvent] = field(default_factory=list)

    def save(self) -> None:
        path = self.root / ".telemetry"
        data = [asdict(e) for e in self.events]
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, root: Path) -> "TelemetryStore":
        path = root / ".telemetry"
        if not path.exists():
            return cls(root=root)
        try:
            with open(path) as f:
                data = json.load(f)
            events = [TaskEvent(**e) for e in data]
            return cls(root=root, events=events)
        except (json.JSONDecodeError, TypeError):
            return cls(root=root)

    def record(self, event: TaskEvent) -> None:
        self.events.append(event)
        self.save()

    def record_done(self, agent_type: str, task_id: int, title: str, duration_minutes: Optional[int], priority: str, tags: list[str]) -> None:
        self.record(TaskEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event="done",
            agent_type=agent_type,
            task_id=task_id,
            title=title,
            duration_minutes=duration_minutes,
            priority=priority,
            tags=tags,
        ))

    def record_verify_pass(self, agent_type: str, task_id: int, title: str, duration_minutes: Optional[int]) -> None:
        self.record(TaskEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event="verify_pass",
            agent_type=agent_type,
            task_id=task_id,
            title=title,
            duration_minutes=duration_minutes,
        ))

    def record_verify_fail(self, agent_type: str, task_id: int, title: str) -> None:
        self.record(TaskEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event="verify_fail",
            agent_type=agent_type,
            task_id=task_id,
            title=title,
        ))


def is_telemetry_enabled(root: Path | None = None) -> bool:
    """Check if telemetry is enabled in config."""
    data = _read_config(root)
    return data.get("telemetry", False)


def get_telemetry_store(root: Path | None = None) -> TelemetryStore:
    """Get telemetry store, respecting opt-in."""
    tasks_root = root or find_tasks_root()
    if tasks_root is None:
        return TelemetryStore(root=Path("."))
    return TelemetryStore.load(tasks_root)


def record_task_done(agent_type: str, task_id: int, title: str, duration_minutes: Optional[int], priority: str, tags: list[str], root: Path | None = None) -> None:
    """Record a task completion event if telemetry is enabled."""
    if not is_telemetry_enabled(root):
        return
    store = get_telemetry_store(root)
    store.record_done(agent_type, task_id, title, duration_minutes, priority, tags)


def record_verify_pass(agent_type: str, task_id: int, title: str, duration_minutes: Optional[int], root: Path | None = None) -> None:
    """Record a verification pass event if telemetry is enabled."""
    if not is_telemetry_enabled(root):
        return
    store = get_telemetry_store(root)
    store.record_verify_pass(agent_type, task_id, title, duration_minutes)


def record_verify_fail(agent_type: str, task_id: int, title: str, root: Path | None = None) -> None:
    """Record a verification fail event if telemetry is enabled."""
    if not is_telemetry_enabled(root):
        return
    store = get_telemetry_store(root)
    store.record_verify_fail(agent_type, task_id, title)


def get_stats(root: Path | None = None) -> dict:
    """Calculate stats from telemetry data."""
    store = get_telemetry_store(root)
    events = store.events

    total_tasks = len([e for e in events if e.event == "done"])
    total_verified = len([e for e in events if e.event == "verify_pass"])
    total_failed = len([e for e in events if e.event == "verify_fail"])

    durations = [e.duration_minutes for e in events if e.event in ("done", "verify_pass") and e.duration_minutes is not None]
    avg_duration = sum(durations) / len(durations) if durations else 0

    agent_stats = {}
    for e in events:
        if e.agent_type not in agent_stats:
            agent_stats[e.agent_type] = {"done": 0, "verified": 0, "failed": 0, "total_minutes": 0}
        if e.event == "done":
            agent_stats[e.agent_type]["done"] += 1
            if e.duration_minutes:
                agent_stats[e.agent_type]["total_minutes"] += e.duration_minutes
        elif e.event == "verify_pass":
            agent_stats[e.agent_type]["verified"] += 1
        elif e.event == "verify_fail":
            agent_stats[e.agent_type]["failed"] += 1

    return {
        "total_tasks": total_tasks,
        "total_verified": total_verified,
        "total_failed": total_failed,
        "avg_duration_minutes": round(avg_duration, 1),
        "agent_stats": agent_stats,
    }