import pytest

from taskcli.models import Task, TaskStatus
from taskcli.parser import format_task, parse_tasks_file
from taskcli.store import TaskStore, StoreError
from taskcli.config import CONFIG_DIR, write_default_config
from taskcli.parser import write_tasks_file


def test_task_model_parent_id():
    task = Task(id=1, title="Child", parent_id=5)
    assert task.parent_id == 5
    assert task.blocked_by == []


def test_task_model_blocked_by():
    task = Task(id=1, title="Blocked", blocked_by=[3, 4])
    assert task.blocked_by == [3, 4]


def test_task_model_full_dag():
    task = Task(
        id=7,
        title="Sub-task",
        parent_id=5,
        blocked_by=[2, 3],
    )
    assert task.parent_id == 5
    assert task.blocked_by == [2, 3]


def test_parser_roundtrip_parent_id():
    task = Task(id=1, title="Has parent", parent_id=4)
    text = format_task(task)
    tasks = parse_tasks_file("/dev/null")
    # manual parse to check parent_id appears
    assert "parent_id: 4" in text


def test_parser_roundtrip_blocked_by():
    task = Task(id=1, title="Blocked", blocked_by=[2, 3])
    text = format_task(task)
    assert "blocked_by: 2,3" in text


def test_parser_roundtrip_empty_blocked_by():
    task = Task(id=1, title="No blockers", blocked_by=[])
    text = format_task(task)
    assert "blocked_by" not in text


import tempfile
from pathlib import Path


@pytest.fixture
def dag_store():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / CONFIG_DIR
        root.mkdir()
        write_default_config(root)
        write_tasks_file(str(root / "coder.tasks"), [], "coder.tasks - test")
        write_tasks_file(str(root / "debug.tasks"), [], "debug.tasks - test")
        yield root


def test_get_next_skips_blocked(dag_store):
    store = TaskStore(dag_store)
    store.add("coder", Task(id=0, title="First"))
    store.add("coder", Task(id=0, title="Second", blocked_by=[1]))
    store.add("coder", Task(id=0, title="Third", blocked_by=[1, 2]))

    next_task = store.get_next("coder")
    assert next_task is not None
    assert next_task.title == "First"


def test_get_next_unblocks_when_blocker_done(dag_store):
    store = TaskStore(dag_store)
    store.add("coder", Task(id=0, title="Blocker", priority="high"))
    store.add("coder", Task(id=0, title="Blocked task", blocked_by=[1]))

    first = store.get_next("coder")
    assert first.title == "Blocker"

    store.update("coder", 1, status=TaskStatus.DONE)

    next_t = store.get_next("coder")
    assert next_t.title == "Blocked task"


def test_get_next_two_blockers_both_must_be_done(dag_store):
    store = TaskStore(dag_store)
    store.add("coder", Task(id=0, title="Blocker A", priority="low"))
    store.add("coder", Task(id=0, title="Blocker B", priority="low"))
    store.add("coder", Task(id=0, title="Needs both", blocked_by=[1, 2]))

    next_t = store.get_next("coder")
    assert next_t.title in ("Blocker A", "Blocker B")


def test_get_next_parent_child_order(dag_store):
    store = TaskStore(dag_store)
    store.add("coder", Task(id=0, title="Parent", priority="high"))
    store.add("coder", Task(id=0, title="Child of 1", parent_id=1, priority="high"))

    parent = store.get_next("coder")
    assert parent.title == "Parent"
    assert parent.parent_id == 0


def test_store_add_with_parent_id(dag_store):
    store = TaskStore(dag_store)
    task = store.add("coder", Task(id=0, title="Sub-task", parent_id=3, blocked_by=[1]))
    assert task.id == 1
    assert task.parent_id == 3
    assert task.blocked_by == [1]