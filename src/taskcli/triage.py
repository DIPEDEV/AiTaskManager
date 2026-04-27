from __future__ import annotations

import os


class TriageError(Exception):
    """Error during task triage."""
    pass


SECTIONS = ["inbox", "work", "personal", "today", "backlog", "review"]


def triage_task(title: str, spec: str = "", priority: str = "") -> str:
    """Classify a task into a section using LLM.

    Returns one of: inbox, work, personal, today, backlog, review.
    Falls back to 'inbox' if no API key or on error.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("CLAUDE_API_KEY")
    if not api_key:
        return _rule_based_triage(title, spec, priority)

    try:
        import anthropic
    except ImportError:
        return _rule_based_triage(title, spec, priority)

    prompt = f"""Classify this task into exactly one section from this list:
{', '.join(SECTIONS)}

Task title: {title}
{f'Task spec: {spec}' if spec else ''}
{f'Current priority: {priority}' if priority else ''}

Respond with ONLY the section name, nothing else."""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-20250514",
            max_tokens=32,
            messages=[{"role": "user", "content": prompt}],
        )
        result = message.content[0].text.strip().lower()
        if result in SECTIONS:
            return result
        return _rule_based_triage(title, spec, priority)
    except Exception:
        return _rule_based_triage(title, spec, priority)


def _rule_based_triage(title: str, spec: str, priority: str) -> str:
    """Fallback rule-based triage when no LLM is available."""
    text = f"{title} {spec}".lower()

    if any(k in text for k in ["bug", "fix", "error", "crash", "fail"]):
        return "work"
    if any(k in text for k in ["personal", "home", "life", "hobby"]):
        return "personal"
    if any(k in text for k in ["review", "pr", "code review"]):
        return "review"
    if priority == "high":
        return "today"
    return "inbox"


def triage_inbox(agent_type: str = "coder") -> dict[str, str]:
    """Re-classify all tasks in 'inbox' section.

    Returns a dict of {task_id: new_section}.
    """
    from taskcli.store import TaskStore, StoreError
    from taskcli.models import TaskStatus

    try:
        store = TaskStore()
    except StoreError:
        return {}

    tasks = store.list_tasks(agent_type, status=TaskStatus.PENDING, section="inbox")
    results = {}

    for task in tasks:
        new_section = triage_task(task.title, task.spec, task.priority)
        if new_section != "inbox":
            store.set_section(agent_type, task.id, new_section)
            results[str(task.id)] = new_section

    return results


__all__ = ["triage_task", "triage_inbox", "TriageError"]