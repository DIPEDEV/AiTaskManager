import tempfile
import os
from pathlib import Path

import pytest

from taskcli.store import TaskStore, StoreError
from taskcli.models import Task, TaskStatus
from taskcli.config import CONFIG_DIR, write_default_config
from taskcli.parser import write_tasks_file


@pytest.fixture
def tasks_dir():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / CONFIG_DIR
        root.mkdir()
        write_default_config(root)
        write_tasks_file(str(root / "coder.tasks"), [], "coder.tasks - test")
        write_tasks_file(str(root / "debug.tasks"), [], "debug.tasks - test")
        yield root


@pytest.fixture
def store(tasks_dir):
    return TaskStore(tasks_dir)


def test_store_add(store):
    task = Task(id=0, title="Test task")
    result = store.add("coder", task)
    assert result.id == 1
    assert result.title == "Test task"
    assert result.status == TaskStatus.PENDING


def test_store_add_auto_id(store):
    store.add("coder", Task(id=0, title="First"))
    store.add("coder", Task(id=0, title="Second"))
    tasks = store.load("coder")
    assert len(tasks) == 2
    assert tasks[0].id == 1
    assert tasks[1].id == 2


def test_store_load_empty(store):
    tasks = store.load("coder")
    assert tasks == []


def test_store_get(store):
    store.add("coder", Task(id=0, title="Find me"))
    task = store.get("coder", 1)
    assert task is not None
    assert task.title == "Find me"


def test_store_get_not_found(store):
    assert store.get("coder", 999) is None


def test_store_update(store):
    store.add("coder", Task(id=0, title="Original"))
    updated = store.update("coder", 1, title="Updated", priority="high")
    assert updated is not None
    assert updated.title == "Updated"
    assert updated.priority == "high"

    task = store.get("coder", 1)
    assert task.title == "Updated"


def test_store_get_next(store):
    store.add("coder", Task(id=0, title="Low prio", priority="low"))
    store.add("coder", Task(id=0, title="High prio", priority="high"))
    store.add("coder", Task(id=0, title="Medium prio", priority="medium"))

    next_task = store.get_next("coder")
    assert next_task is not None
    assert next_task.title == "High prio"
    assert next_task.status == TaskStatus.IN_PROGRESS


def test_store_get_next_empty(store):
    assert store.get_next("coder") is None


def test_store_task_done_coder(store):
    store.add("coder", Task(id=0, title="Coder task", file="src/main.py", line=10))
    task = store.task_done_coder(1)

    # Returns verify task in debug
    assert task.status == TaskStatus.PENDING
    assert task.agent_type == "debug"
    assert "Verify" in task.title

    # Source task is deleted
    coder_tasks = store.load("coder")
    assert len(coder_tasks) == 0

    debug_tasks = store.load("debug")
    assert len(debug_tasks) == 1
    assert debug_tasks[0].coder_ref == 1
    assert "Verify" in debug_tasks[0].title
    assert debug_tasks[0].status == TaskStatus.PENDING


def test_store_task_pass_debug(store):
    store.add("coder", Task(id=0, title="Coder task"))
    store.task_done_coder(1)

    debug_task, coder_task = store.task_pass_debug(1)

    assert debug_task.status == TaskStatus.DONE
    assert coder_task is None  # source was already deleted


def test_store_task_fail_debug(store):
    store.add("coder", Task(id=0, title="Coder task", file="src/main.py"))
    store.task_done_coder(1)

    new_task = store.task_fail_debug(1, "Bug not fixed properly")

    assert new_task.agent_type == "coder"
    assert new_task.status == TaskStatus.PENDING
    assert "Re-check" in new_task.title
    assert "Bug not fixed properly" in new_task.spec

    debug_task = store.get("debug", 1)
    assert debug_task.status == TaskStatus.DONE

    coder_tasks = store.load("coder")
    assert len(coder_tasks) == 1  # only re-check, source was deleted


def test_store_list_filtered(store):
    store.add("coder", Task(id=0, title="Pending task", status=TaskStatus.PENDING))
    store.add("coder", Task(id=0, title="Done task", status=TaskStatus.DONE))

    pending = store.list_tasks("coder", TaskStatus.PENDING)
    assert len(pending) == 1
    assert pending[0].title == "Pending task"


def test_store_move(store):
    store.add("coder", Task(id=0, title="Movable"))
    moved = store.move("coder", "debug", 1)

    assert moved is not None
    assert moved.agent_type == "debug"

    assert store.get("coder", 1) is None
    assert store.get("debug", 1) is not None


def test_store_error_no_tasks_dir():
    with pytest.raises(StoreError):
        TaskStore(Path("/nonexistent/path"))


def test_store_unknown_agent(store):
    with pytest.raises(StoreError):
        store.load("nonexistent_agent")
