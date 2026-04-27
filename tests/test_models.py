from taskcli.models import Task, TaskStatus


def test_section_default_empty():
    task = Task(id=1, title="No section")
    assert task.section == ""


def test_post_init_sets_created():
    task = Task(id=1, title="Test")
    assert task.created != ""
    assert "T" in task.created


def test_post_init_preserves_existing_created():
    task = Task(id=1, title="Test", created="2024-01-01T00:00:00")
    assert task.created == "2024-01-01T00:00:00"


def test_section_field_accepts_value():
    task = Task(id=1, title="Test", section="work")
    assert task.section == "work"


def test_stats_icon_pending():
    assert Task(id=1, title="t", status=TaskStatus.PENDING).status_icon == "\u25cb"


def test_stats_icon_in_progress():
    assert Task(id=1, title="t", status=TaskStatus.IN_PROGRESS).status_icon == "\u25c9"


def test_priority_color():
    assert Task(id=1, title="t", priority="high").priority_color == "red"
    assert Task(id=1, title="t", priority="medium").priority_color == "yellow"
    assert Task(id=1, title="t", priority="low").priority_color == "green"


def test_source_agent_default_empty():
    task = Task(id=1, title="t")
    assert task.source_agent == ""


def test_coder_ref_default_zero():
    task = Task(id=1, title="t")
    assert task.coder_ref == 0


def test_debug_ref_default_zero():
    task = Task(id=1, title="t")
    assert task.debug_ref == 0
