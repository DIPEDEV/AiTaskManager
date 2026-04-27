import tempfile
from pathlib import Path

import yaml
import pytest

from taskcli.models import AgentConfig
from taskcli.config import (
    CONFIG_DIR,
    load_config,
    get_agent,
    get_pipeline_target,
    write_default_config,
    get_config_path,
)


def test_load_default_config(tmp_path):
    root = tmp_path / CONFIG_DIR
    root.mkdir()
    write_default_config(root)
    agents = load_config(get_config_path(root))
    assert len(agents) == 2
    names = {a.name for a in agents}
    assert "coder" in names
    assert "debug" in names


def test_get_agent():
    agents = load_config()
    coder = get_agent("coder", agents)
    assert coder is not None
    assert coder.name == "coder"
    assert coder.file == "coder.tasks"
    assert coder.pipeline_to == "debug"


def test_get_pipeline_target():
    agents = load_config()
    coder = get_agent("coder", agents)
    target = get_pipeline_target(coder, agents)
    assert target is not None
    assert target.name == "debug"


def test_load_custom_config(tmp_path):
    root = tmp_path / CONFIG_DIR
    root.mkdir()
    config_path = root / "config"
    data = {
        "agents": {
            "custom": {
                "file": "custom.tasks",
                "description": "Custom agent",
                "pipeline_to": "other",
            },
            "other": {
                "file": "other.tasks",
                "description": "Other agent",
                "pipeline_to": "",
            },
        }
    }
    with open(config_path, "w") as f:
        yaml.safe_dump(data, f)

    agents = load_config(config_path)
    assert len(agents) == 2
    custom = get_agent("custom", agents)
    assert custom.file == "custom.tasks"
