from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    NEEDS_VERIFICATION = "needs_verification"
    DONE = "done"


@dataclass
class Task:
    id: int
    title: str
    status: TaskStatus = TaskStatus.PENDING
    priority: str = "medium"
    spec: str = ""
    file: str = ""
    line: int = 0
    created: str = ""
    agent_type: str = "coder"
    coder_ref: int = 0
    debug_ref: int = 0
    source_agent: str = ""

    def __post_init__(self):
        if not self.created:
            self.created = datetime.now(timezone.utc).isoformat()

    @property
    def status_icon(self) -> str:
        icons = {
            TaskStatus.PENDING: "○",
            TaskStatus.IN_PROGRESS: "◉",
            TaskStatus.NEEDS_VERIFICATION: "◇",
            TaskStatus.DONE: "✓",
        }
        return icons.get(self.status, "?")

    @property
    def priority_color(self) -> str:
        colors = {"high": "red", "medium": "yellow", "low": "green"}
        return colors.get(self.priority, "white")


@dataclass
class AgentConfig:
    name: str
    file: str
    description: str = ""
    pipeline_to: str = ""


DEFAULT_AGENTS = [
    AgentConfig(
        name="coder",
        file="coder.tasks",
        description="Code implementation tasks",
        pipeline_to="debug",
    ),
    AgentConfig(
        name="debug",
        file="debug.tasks",
        description="Debugging and verification tasks",
        pipeline_to="",
    ),
]
