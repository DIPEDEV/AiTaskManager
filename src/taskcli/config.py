from __future__ import annotations

import os
from pathlib import Path

import yaml

from taskcli.models import AgentConfig, DEFAULT_AGENTS

CONFIG_DIR = ".tasks"
CONFIG_FILE = "config"


def find_tasks_root(start: Path | None = None) -> Path | None:
    """Walk up from start to find .tasks directory."""
    current = (start or Path.cwd()).resolve()
    for parent in [current, *current.parents]:
        tasks_dir = parent / CONFIG_DIR
        if tasks_dir.is_dir():
            return tasks_dir
    return None


def get_config_path(tasks_root: Path | None = None) -> Path | None:
    root = tasks_root or find_tasks_root()
    if root is None:
        return None
    return root / CONFIG_FILE


def load_config(path: Path | None = None) -> list[AgentConfig]:
    """Load agent configuration from .tasks/config file."""
    config_path = path or get_config_path()
    if config_path is None or not config_path.exists():
        return list(DEFAULT_AGENTS)

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    agents_data = data.get("agents", {})
    if not agents_data:
        return list(DEFAULT_AGENTS)

    agents = []
    for name, info in agents_data.items():
        agents.append(
            AgentConfig(
                name=name,
                file=info.get("file", f"{name}.tasks"),
                description=info.get("description", ""),
                pipeline_to=info.get("pipeline_to", ""),
            )
        )
    return agents


def get_agent(name: str, agents: list[AgentConfig] | None = None) -> AgentConfig | None:
    """Find agent config by name."""
    if agents is None:
        agents = load_config()
    for agent in agents:
        if agent.name == name:
            return agent
    return None


def get_pipeline_target(agent: AgentConfig, agents: list[AgentConfig] | None = None) -> AgentConfig | None:
    """Get the agent that this agent pipelines to on done."""
    if not agent.pipeline_to:
        return None
    return get_agent(agent.pipeline_to, agents)


def write_default_config(tasks_root: Path) -> None:
    """Write default .tasks/config file."""
    config_path = tasks_root / CONFIG_FILE
    data = {
        "agents": {
            "coder": {
                "file": "coder.tasks",
                "description": "Code implementation tasks",
                "pipeline_to": "debug",
            },
            "debug": {
                "file": "debug.tasks",
                "description": "Debugging and verification tasks",
                "pipeline_to": "",
            },
        }
    }
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
