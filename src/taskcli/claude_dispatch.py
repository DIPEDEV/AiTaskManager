from __future__ import annotations

import os
import subprocess
from typing import Any


class DispatchError(Exception):
    """Error during agent dispatch."""
    pass


def build_dispatch_command(task_id: int, agent_type: str, scope: str = "project") -> dict[str, Any]:
    """Build the dispatch command for a task.

    Returns a dict with:
      - command: list of strings to execute
      - prompt: the full prompt text for the subagent
      - task_info: basic task metadata
    """
    from taskcli.config import resolve_root
    from taskcli.store import TaskStore

    root = resolve_root(scope)  # type: ignore[arg-type]
    store = TaskStore(root)

    task = store.get(agent_type, task_id)
    if task is None:
        raise DispatchError(f"Task {task_id} not found in {agent_type}")

    prompt = _build_prompt_from_task(task, agent_type)

    cmd = _build_claude_command(prompt, agent_type, task_id)

    return {
        "task_id": task_id,
        "agent_type": agent_type,
        "command": cmd,
        "prompt": prompt,
        "note": "Execute command to dispatch Claude subagent for this task.",
    }


def run_dispatch(task_id: int, agent_type: str, scope: str = "project") -> dict[str, Any]:
    """Execute the dispatch command and return the result.

    Runs the Claude subagent and returns stdout/stderr.
    """
    info = build_dispatch_command(task_id, agent_type, scope)

    try:
        result = subprocess.run(
            info["command"],
            capture_output=True,
            text=True,
            timeout=600,
        )
        return {
            "success": result.returncode == 0,
            "returncode": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "task_id": task_id,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "Timed out after 600 seconds",
            "task_id": task_id,
        }
    except FileNotFoundError:
        return {
            "success": False,
            "returncode": -1,
            "stdout": "",
            "stderr": "claude command not found. Install Claude CLI.",
            "task_id": task_id,
        }


def _build_prompt_from_task(task: Any, agent_type: str) -> str:
    parts = [f"# Task: {task.title}"]

    if task.priority:
        parts.append(f"**Priority:** {task.priority}")

    if task.file:
        loc = task.file
        if task.line:
            loc += f":{task.line}"
        parts.append(f"**Location:** {loc}")

    if task.spec:
        parts.append("\n## Specification\n" + task.spec)

    parts.append("\n## Instructions\n")
    parts.append(f"Work on this task as the '{agent_type}' agent.")
    parts.append("Use 'task done <id> -t " + agent_type + "' when complete.")
    parts.append("Use 'task show <id> -t " + agent_type + "' to review full details.")

    return "\n".join(parts)


def _build_claude_command(prompt: str, agent_type: str, task_id: int) -> list[str]:
    """Build the claude CLI command to dispatch.

    Uses Claude Code's --resume flag and prompt injection.
    """
    return [
        "claude",
        "--resume",
        f"task-{task_id}",
        "-p",
        prompt,
    ]


__all__ = ["build_dispatch_command", "run_dispatch", "DispatchError"]