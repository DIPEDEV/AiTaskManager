from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any


class HookRunner:
    """Execute configured hooks on task lifecycle events."""

    def __init__(self, agent_type: str, config_path: Path | None = None):
        from taskcli.config import get_hooks
        self.agent_type = agent_type
        self.hooks = get_hooks(agent_type, config_path)

    def run(self, event: str, context: dict[str, Any]) -> None:
        """Run all hooks for the given event.

        Events: on_done, on_verify_pass, on_verify_fail, on_create
        Context keys: task_id, agent_type, title, priority, etc.
        """
        commands = self.hooks.get(event, [])
        for cmd in commands:
            self._execute(cmd, context)

    def _execute(self, cmd: str, context: dict[str, Any]) -> None:
        """Substitute template variables and run command."""
        rendered = cmd
        for key, val in context.items():
            rendered = rendered.replace(f"{{{key}}}", str(val))
        parts = rendered.split()
        if not parts:
            return
        try:
            subprocess.run(parts, check=False, capture_output=True)
        except Exception:
            pass


__all__ = ["HookRunner"]