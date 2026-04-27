from __future__ import annotations

import os
from pathlib import Path

import yaml

from typing import Literal

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


def find_global_root() -> Path:
    """Return global tasks root honoring TASKCLI_GLOBAL_ROOT or ~/.tasks."""
    env_root = os.environ.get("TASKCLI_GLOBAL_ROOT", "")
    if env_root:
        root = Path(env_root).expanduser().resolve()
    else:
        root = Path.home() / ".tasks"

    if not root.exists():
        root.mkdir(parents=True, exist_ok=True)
        write_default_config(root)

    return root


def get_storage_backend(path: Path | None = None) -> str:
    """Read storage backend type from config. Defaults to 'plaintext'."""
    data = _read_config(path)
    return data.get("storage_backend", "plaintext")


def get_git_sync_enabled(path: Path | None = None) -> bool:
    """Read git sync enabled from config. Defaults to False."""
    data = _read_config(path)
    return data.get("git_sync", False)


def set_git_sync_enabled(enabled: bool, path: Path | None = None) -> None:
    """Enable or disable git sync in config."""
    config_path = path or get_config_path()
    if config_path is None:
        return
    data = {}
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f.read()) or {}
    data["git_sync"] = enabled
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)


def get_telemetry_enabled(path: Path | None = None) -> bool:
    """Read telemetry opt-in from config. Defaults to False."""
    data = _read_config(path)
    return data.get("telemetry", False)


def set_telemetry_enabled(enabled: bool, path: Path | None = None) -> None:
    """Enable or disable telemetry in config."""
    config_path = path or get_config_path()
    if config_path is None:
        return
    data = {}
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f.read()) or {}
    data["telemetry"] = enabled
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)


def _read_config(path: Path | None = None) -> dict:
    """Read config as dict, returning empty dict if not found."""
    config_path = path or get_config_path()
    if config_path is None or not config_path.exists():
        return {}
    with open(config_path) as f:
        return yaml.safe_load(f.read()) or {}


def get_hooks(agent_type: str, path: Path | None = None) -> dict[str, list[str]]:
    """Read hooks for an agent from config. Returns dict of event -> list of commands."""
    data = _read_config(path)
    agents_data = data.get("agents", {})
    agent_data = agents_data.get(agent_type, {})
    return agent_data.get("hooks", {})


def set_hooks(agent_type: str, hooks: dict[str, list[str]], path: Path | None = None) -> None:
    """Set hooks for an agent in config."""
    config_path = path or get_config_path()
    if config_path is None:
        return
    data = {}
    if config_path.exists():
        with open(config_path) as f:
            data = yaml.safe_load(f.read()) or {}
    if "agents" not in data:
        data["agents"] = {}
    if agent_type not in data["agents"]:
        data["agents"][agent_type] = {}
    data["agents"][agent_type]["hooks"] = hooks
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)


def resolve_root(scope: Literal["project", "global", "auto"] = "auto") -> Path:
    """Resolve tasks root based on scope.

    - project: return project root or raise
    - global: always return global root
    - auto: project root if found, else global
    """
    if scope == "global":
        return find_global_root()
    if scope == "project":
        root = find_tasks_root()
        if root is None:
            raise FileNotFoundError("No .tasks directory found in project tree")
        return root
    # auto
    return find_tasks_root() or find_global_root()


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
