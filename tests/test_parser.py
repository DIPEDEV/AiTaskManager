from taskcli.parser import parse_tasks, format_task, format_tasks
from taskcli.models import Task, TaskStatus


def test_parse_single_task():
    content = """---
-- comment
---

--- task:1
status: pending
priority: high
title: Fix auth bug
spec: 
file: src/auth/login.ts
line: 42
created: 2026-04-26T10:00:00
agent_type: coder
---
"""
    tasks = parse_tasks(content)
    assert len(tasks) == 1
    t = tasks[0]
    assert t.id == 1
    assert t.title == "Fix auth bug"
    assert t.status == TaskStatus.PENDING
    assert t.priority == "high"
    assert t.file == "src/auth/login.ts"
    assert t.line == 42


def test_parse_multi_task():
    content = """--- task:1
status: pending
title: Task one
spec: 
---
--- task:2
status: done
title: Task two
spec: 
---
"""
    tasks = parse_tasks(content)
    assert len(tasks) == 2
    assert tasks[0].id == 1
    assert tasks[1].id == 2
    assert tasks[1].status == TaskStatus.DONE


def test_parse_with_spec_multiline():
    content = """--- task:1
status: pending
title: Complex task
spec: |
  Line one
  Line two
  Line three
file: src/main.py
---
"""
    tasks = parse_tasks(content)
    assert len(tasks) == 1
    assert tasks[0].spec == "Line one\nLine two\nLine three"


def test_parse_empty():
    tasks = parse_tasks("")
    assert tasks == []


def test_parse_garbage():
    tasks = parse_tasks("some random\ntext without tasks")
    assert tasks == []


def test_format_task():
    task = Task(
        id=1,
        title="Test",
        status=TaskStatus.PENDING,
        priority="medium",
    )
    output = format_task(task)
    assert "task:1" in output
    assert "status: pending" in output
    assert "title: Test" in output
    assert "priority: medium" in output


def test_format_task_with_spec():
    task = Task(
        id=1,
        title="Test",
        spec="Line one\nLine two",
    )
    output = format_task(task)
    assert "spec: |" in output
    assert "  Line one" in output
    assert "  Line two" in output


def test_format_tasks():
    tasks = [
        Task(id=1, title="One"),
        Task(id=2, title="Two"),
    ]
    output = format_tasks(tasks, header="Test header")
    assert "Test header" in output
    assert "--- task:1" in output
    assert "--- task:2" in output


def test_roundtrip():
    task = Task(
        id=42,
        title="Roundtrip test",
        status=TaskStatus.IN_PROGRESS,
        priority="low",
        spec="Multi\nline\nspec",
        file="src/app.py",
        line=100,
        coder_ref=5,
        debug_ref=3,
    )
    formatted = format_task(task)
    parsed = parse_tasks(formatted)
    assert len(parsed) == 1
    p = parsed[0]
    assert p.id == task.id
    assert p.title == task.title
    assert p.status == task.status
    assert p.priority == task.priority
    assert p.spec == task.spec
    assert p.file == task.file
    assert p.line == task.line
    assert p.coder_ref == task.coder_ref
    assert p.debug_ref == task.debug_ref


def test_task_status_icon():
    assert Task(id=1, title="t", status=TaskStatus.PENDING).status_icon == "○"
    assert Task(id=1, title="t", status=TaskStatus.IN_PROGRESS).status_icon == "◉"
    assert Task(id=1, title="t", status=TaskStatus.NEEDS_VERIFICATION).status_icon == "◇"
    assert Task(id=1, title="t", status=TaskStatus.DONE).status_icon == "✓"
