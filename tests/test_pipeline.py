import tempfile
from pathlib import Path

import yaml
import pytest

from taskcli.store import TaskStore
from taskcli.models import Task, TaskStatus, AgentConfig
from taskcli.config import CONFIG_DIR, load_config, get_agent
from taskcli.parser import write_tasks_file


@pytest.fixture
def multi_agent_dir():
    """Setup a tasks dir with coder, debug, and tester agents."""
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / CONFIG_DIR
        root.mkdir()
        data = {
            "agents": {
                "coder": {
                    "file": "coder.tasks",
                    "description": "Code",
                    "pipeline_to": "debug",
                },
                "debug": {
                    "file": "debug.tasks",
                    "description": "Debug",
                    "pipeline_to": "",
                },
                "tester": {
                    "file": "tester.tasks",
                    "description": "Test",
                    "pipeline_to": "debug",
                },
            }
        }
        with open(root / "config", "w") as f:
            yaml.safe_dump(data, f)
        for name in ["coder", "debug", "tester"]:
            write_tasks_file(str(root / f"{name}.tasks"), [], f"{name}.tasks")
        yield root


@pytest.fixture
def store(multi_agent_dir):
    return TaskStore(multi_agent_dir)


def test_generic_pipeline_tester_to_debug(store):
    store.add("tester", Task(id=0, title="Test task", file="test.ts", line=5))
    task = store.task_done_with_pipeline("tester", 1)

    # Returns verify task in debug
    assert task.status == TaskStatus.PENDING
    assert task.agent_type == "debug"
    assert "Verify" in task.title
    assert task.coder_ref == 1

    # Source task is deleted
    tester_tasks = store.load("tester")
    assert len(tester_tasks) == 0

    debug_tasks = store.load("debug")
    assert len(debug_tasks) == 1
    assert debug_tasks[0].coder_ref == 1
    assert "Verify" in debug_tasks[0].title
    assert debug_tasks[0].agent_type == "debug"


def test_generic_pipeline_pass_verify(store):
    store.add("tester", Task(id=0, title="Test task"))
    store.task_done_with_pipeline("tester", 1)

    v, s = store.task_pass_verify(1, "debug")

    assert v.status == TaskStatus.DONE
    assert s is None  # source was already deleted


def test_generic_pipeline_fail_verify(store):
    store.add("tester", Task(id=0, title="Test task"))
    store.task_done_with_pipeline("tester", 1)

    new_task = store.task_fail_verify(1, "Still broken", "debug")

    assert new_task.agent_type == "tester"
    assert new_task.status == TaskStatus.PENDING
    assert "Re-check" in new_task.title
    assert "Still broken" in new_task.spec

    tester_tasks = store.load("tester")
    assert len(tester_tasks) == 1  # only re-check, source was deleted


def test_no_pipeline_agent_done(store):
    store.add("debug", Task(id=0, title="Standalone debug"))
    task = store.task_done_with_pipeline("debug", 1)
    assert task.status == TaskStatus.DONE
    assert task.agent_type == "debug"


def test_agent_without_pipeline(store):
    agents = store._agents
    coder = get_agent("coder", agents)
    assert coder.pipeline_to == "debug"
    debug_agent = get_agent("debug", agents)
    assert debug_agent.pipeline_to == ""
    tester = get_agent("tester", agents)
    assert tester.pipeline_to == "debug"


def test_legacy_methods_still_work(store):
    store.add("coder", Task(id=0, title="Legacy test"))
    task = store.task_done_coder(1)
    assert task.agent_type == "debug"
    assert task.status == TaskStatus.PENDING

    d, c = store.task_pass_debug(1)
    assert d.status == TaskStatus.DONE
    assert c is None  # source deleted


def test_fail_verify_finds_source_agent(store):
    store.add("tester", Task(id=0, title="Tester task"))
    store.task_done_with_pipeline("tester", 1)

    new_task = store.task_fail_verify(1, "Failed", "debug")
    assert new_task.agent_type == "tester"
    assert new_task.status == TaskStatus.PENDING
