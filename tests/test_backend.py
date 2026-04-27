import json
import tempfile
from pathlib import Path

import pytest

from taskcli.backend import (
    StorageBackend,
    PlainTextBackend,
    JSONLBackend,
    SQLiteBackend,
    LockedBackend,
    create_backend,
)
from taskcli.models import Task, TaskStatus
from taskcli.config import CONFIG_DIR, write_default_config


@pytest.fixture
def plaintext_root():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / CONFIG_DIR
        root.mkdir()
        yield root


@pytest.fixture
def jsonl_root():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / CONFIG_DIR
        root.mkdir()
        yield root


@pytest.fixture
def sqlite_root():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / CONFIG_DIR
        root.mkdir()
        yield root


# ── PlainTextBackend ──

def test_plaintext_load_empty(plaintext_root):
    backend = PlainTextBackend(plaintext_root)
    assert backend.load("coder") == []


def test_plaintext_save_and_load(plaintext_root):
    backend = PlainTextBackend(plaintext_root)
    tasks = [Task(id=1, title="Task 1", agent_type="coder")]
    backend.save("coder", tasks)
    loaded = backend.load("coder")
    assert len(loaded) == 1
    assert loaded[0].title == "Task 1"


def test_plaintext_exists(plaintext_root):
    backend = PlainTextBackend(plaintext_root)
    assert not backend.exists("coder")
    backend.save("coder", [])
    assert backend.exists("coder")


def test_plaintext_ensure(plaintext_root):
    backend = PlainTextBackend(plaintext_root)
    backend.ensure("coder")
    assert backend.exists("coder")


# ── JSONLBackend ──

def test_jsonl_load_empty(jsonl_root):
    backend = JSONLBackend(jsonl_root)
    assert backend.load("coder") == []


def test_jsonl_save_and_load(jsonl_root):
    backend = JSONLBackend(jsonl_root)
    tasks = [
        Task(id=1, title="First", priority="high", status=TaskStatus.PENDING),
        Task(id=2, title="Second", priority="low", status=TaskStatus.DONE),
    ]
    backend.save("coder", tasks)
    loaded = backend.load("coder")
    assert len(loaded) == 2
    assert loaded[0].title == "First"
    assert loaded[0].priority == "high"
    assert loaded[1].title == "Second"
    assert loaded[1].status == TaskStatus.DONE


def test_jsonl_roundtrip_all_fields(jsonl_root):
    backend = JSONLBackend(jsonl_root)
    task = Task(
        id=3,
        title="Complex task",
        status=TaskStatus.IN_PROGRESS,
        priority="medium",
        spec="Multi\nline\nspec",
        file="src/main.py",
        line=42,
        agent_type="debug",
        section="backend",
        coder_ref=1,
        debug_ref=2,
        source_agent="coder",
    )
    backend.save("debug", [task])
    loaded = backend.load("debug")
    assert len(loaded) == 1
    t = loaded[0]
    assert t.id == 3
    assert t.title == "Complex task"
    assert t.status == TaskStatus.IN_PROGRESS
    assert t.priority == "medium"
    assert t.spec == "Multi\nline\nspec"
    assert t.file == "src/main.py"
    assert t.line == 42
    assert t.agent_type == "debug"
    assert t.section == "backend"
    assert t.coder_ref == 1
    assert t.debug_ref == 2
    assert t.source_agent == "coder"


def test_jsonl_exists(jsonl_root):
    backend = JSONLBackend(jsonl_root)
    assert not backend.exists("coder")
    backend.save("coder", [Task(id=1, title="X")])
    assert backend.exists("coder")


def test_jsonl_skips_malformed_lines(jsonl_root):
    backend = JSONLBackend(jsonl_root)
    filepath = jsonl_root / "coder.jsonl"
    filepath.write_text(
        '{"id": 1, "title": "good"}\n'
        'bad line\n'
        '{"id": 2, "title": "also good"}\n',
    )
    loaded = backend.load("coder")
    assert len(loaded) == 2
    titles = {t.title for t in loaded}
    assert titles == {"good", "also good"}


# ── SQLiteBackend ──

def test_sqlite_load_empty(sqlite_root):
    backend = SQLiteBackend(sqlite_root)
    assert backend.load("coder") == []


def test_sqlite_save_and_load(sqlite_root):
    backend = SQLiteBackend(sqlite_root)
    tasks = [
        Task(id=1, title="Task A", priority="high"),
        Task(id=2, title="Task B", status=TaskStatus.DONE),
    ]
    backend.save("coder", tasks)
    loaded = backend.load("coder")
    assert len(loaded) == 2
    assert loaded[0].title == "Task A"
    assert loaded[0].priority == "high"
    assert loaded[1].title == "Task B"
    assert loaded[1].status == TaskStatus.DONE


def test_sqlite_overwrite_replace(sqlite_root):
    backend = SQLiteBackend(sqlite_root)
    backend.save("coder", [Task(id=1, title="Old")])
    backend.save("coder", [Task(id=2, title="New")])
    loaded = backend.load("coder")
    assert len(loaded) == 1
    assert loaded[0].title == "New"


def test_sqlite_isolated_agents(sqlite_root):
    backend = SQLiteBackend(sqlite_root)
    backend.save("coder", [Task(id=1, title="Coder task")])
    backend.save("debug", [Task(id=1, title="Debug task")])
    assert len(backend.load("coder")) == 1
    assert len(backend.load("debug")) == 1
    assert backend.load("coder")[0].title == "Coder task"
    assert backend.load("debug")[0].title == "Debug task"


def test_sqlite_roundtrip_all_fields(sqlite_root):
    backend = SQLiteBackend(sqlite_root)
    task = Task(
        id=7,
        title="All fields",
        status=TaskStatus.NEEDS_VERIFICATION,
        priority="low",
        spec="Spec text",
        file="tests/test.py",
        line=99,
        agent_type="tester",
        section="qa",
        coder_ref=3,
        debug_ref=4,
        source_agent="reviewer",
    )
    backend.save("tester", [task])
    loaded = backend.load("tester")
    assert len(loaded) == 1
    t = loaded[0]
    assert t.id == 7
    assert t.title == "All fields"
    assert t.status == TaskStatus.NEEDS_VERIFICATION
    assert t.priority == "low"
    assert t.spec == "Spec text"
    assert t.file == "tests/test.py"
    assert t.line == 99
    assert t.agent_type == "tester"
    assert t.section == "qa"
    assert t.coder_ref == 3
    assert t.debug_ref == 4
    assert t.source_agent == "reviewer"


def test_sqlite_exists(sqlite_root):
    backend = SQLiteBackend(sqlite_root)
    assert not backend.exists("coder")
    backend.save("coder", [Task(id=1, title="X")])
    assert backend.exists("coder")


# ── Factory ──

def test_create_backend_defaults_to_plaintext(plaintext_root):
    backend = create_backend("nonexistent", plaintext_root)
    assert isinstance(backend, LockedBackend)
    assert isinstance(backend.inner, PlainTextBackend)


def test_create_backend_plaintext(plaintext_root):
    backend = create_backend("plaintext", plaintext_root)
    assert isinstance(backend, LockedBackend)
    assert isinstance(backend.inner, PlainTextBackend)


def test_create_backend_jsonl(jsonl_root):
    backend = create_backend("jsonl", jsonl_root)
    assert isinstance(backend, LockedBackend)
    assert isinstance(backend.inner, JSONLBackend)


def test_create_backend_sqlite(sqlite_root):
    backend = create_backend("sqlite", sqlite_root)
    assert isinstance(backend, LockedBackend)
    assert isinstance(backend.inner, SQLiteBackend)


def test_create_backend_no_lock(jsonl_root):
    backend = create_backend("jsonl", jsonl_root, lock_for_writes=False)
    assert isinstance(backend, JSONLBackend)
    assert not isinstance(backend, LockedBackend)


# ── Integration: TaskStore with different backends ──

from taskcli.store import TaskStore, StoreError
from taskcli.parser import write_tasks_file


@pytest.fixture
def backend_store(sqlite_root):
    """TaskStore with SQLite backend."""
    write_default_config(sqlite_root)
    write_tasks_file(str(sqlite_root / "coder.tasks"), [], "coder.tasks - test")
    write_tasks_file(str(sqlite_root / "debug.tasks"), [], "debug.tasks - test")
    backend = SQLiteBackend(sqlite_root)
    return TaskStore(sqlite_root, backend=backend)


def test_store_with_sqlite_add(backend_store):
    task = Task(id=0, title="SQLite task")
    result = backend_store.add("coder", task)
    assert result.id == 1
    assert result.title == "SQLite task"


def test_store_with_sqlite_pipeline(backend_store):
    backend_store.add("coder", Task(id=0, title="Pipeline test"))
    verify = backend_store.task_done_coder(1)
    assert "Verify" in verify.title
    assert verify.agent_type == "debug"

    coder_tasks = backend_store.load("coder")
    assert len(coder_tasks) == 0

    debug_tasks = backend_store.load("debug")
    assert len(debug_tasks) == 1


def test_store_with_sqlite_verify_pass(backend_store):
    backend_store.add("coder", Task(id=0, title="To verify"))
    backend_store.task_done_coder(1)
    debug_task, _ = backend_store.task_pass_debug(1)
    assert debug_task.status == TaskStatus.DONE


def test_store_with_sqlite_verify_fail(backend_store):
    backend_store.add("coder", Task(id=0, title="Failed"))
    backend_store.task_done_coder(1)
    new_task = backend_store.task_fail_debug(1, "Not right")
    assert new_task.agent_type == "coder"
    assert "Re-check" in new_task.title
    assert "Not right" in new_task.spec
