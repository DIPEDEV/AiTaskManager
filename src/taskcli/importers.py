from __future__ import annotations

import os


class ImporterError(Exception):
    """Error during issue import."""
    pass


def import_github_issues(repo: str, state: str = "open") -> list[dict]:
    """Import GitHub issues as tasks.

    Args:
        repo: "owner/repo" format
        state: "open", "closed", or "all"
    Returns list of task dicts ready for Task creation.
    """
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    import urllib.request
    import json

    url = f"https://api.github.com/repos/{repo}/issues?state={state}&per_page=100"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
    except Exception as e:
        raise ImporterError(f"Failed to fetch GitHub issues: {e}") from e

    tasks = []
    for issue in data:
        if "pull_request" in issue:
            continue
        labels = [l["name"] for l in issue.get("labels", [])]
        priority = "medium"
        if any(l in labels for l in ["critical", "urgent", "p0", "p1"]):
            priority = "high"
        elif any(l in labels for l in ["p3", "low"]):
            priority = "low"

        tasks.append({
            "title": f"[GH-{issue['number']}] {issue['title']}",
            "spec": issue.get("body", "") or "",
            "priority": priority,
            "tags": labels,
            "section": f"github:{repo}",
            "due": "",
            "recur": "",
            "external_url": issue["html_url"],
            "external_id": str(issue["number"]),
        })
    return tasks


def import_github_issues_cmd(repo: str, state: str = "open", agent_type: str = "coder") -> dict:
    """Import GitHub issues as tasks into the store."""
    from taskcli.store import TaskStore, StoreError
    from taskcli.models import Task, TaskStatus

    try:
        store = TaskStore()
    except StoreError as e:
        raise ImporterError(str(e)) from e

    issues = import_github_issues(repo, state)
    created = []
    for issue_data in issues:
        task = Task(
            id=0,
            title=issue_data["title"],
            status=TaskStatus.PENDING,
            priority=issue_data["priority"],
            spec=issue_data["spec"],
            file="",
            line=0,
            section=issue_data["section"],
            tags=issue_data["tags"],
        )
        created_task = store.add(agent_type, task)
        created.append({"id": created_task.id, "title": created_task.title})

    return {"imported": len(created), "tasks": created}


__all__ = ["import_github_issues", "import_github_issues_cmd", "ImporterError"]