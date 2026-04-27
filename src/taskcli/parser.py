from __future__ import annotations

from typing import TextIO

from taskcli.models import Task, TaskStatus

TASK_SEPARATOR = "--- task:"
FIELD_SEPARATOR = ": "
SPEC_INDICATOR = "|"


def parse_tasks(content: str) -> list[Task]:
    """Parse .tasks file content into Task objects."""
    tasks: list[Task] = []
    blocks = content.split("--- task:")
    for block in blocks:
        block = block.strip()
        if not block:
            continue
        task = _parse_task_block(block)
        if task:
            tasks.append(task)
    return tasks


def _parse_task_block(block: str) -> Task | None:
    """Parse a single task block."""
    lines = block.split("\n")
    if not lines:
        return None

    try:
        task_id = int(lines[0].strip())
    except (ValueError, IndexError):
        return None

    fields: dict = {"id": task_id}
    spec_lines: list[str] = []
    in_spec = False
    current_field = ""

    for line in lines[1:]:
        if in_spec:
            if line.startswith("  ") or line.startswith("\t"):
                spec_lines.append(line.strip())
                continue
            else:
                fields[current_field] = "\n".join(spec_lines)
                in_spec = False
                spec_lines = []

        if not line.strip():
            continue

        if ": " in line:
            key, _, value = line.partition(": ")
            if value.strip() == "|":
                current_field = key.strip()
                in_spec = True
                spec_lines = []
            else:
                fields[key.strip()] = value.strip()
        elif line.strip() == "---":
            continue

    if in_spec:
        fields[current_field] = "\n".join(spec_lines)

    try:
        blocked_str = fields.get("blocked_by", "")
        blocked_by = [int(x.strip()) for x in blocked_str.split(",") if blocked_str.strip()]
        tags_str = fields.get("tags", "")
        tags = [x.strip() for x in tags_str.split(",") if tags_str.strip()]
        return Task(
            id=fields["id"],
            title=fields.get("title", ""),
            status=TaskStatus(fields.get("status", "pending")),
            priority=fields.get("priority", "medium"),
            spec=fields.get("spec", ""),
            file=fields.get("file", ""),
            line=int(fields.get("line", 0)),
            created=fields.get("created", ""),
            agent_type=fields.get("agent_type", "coder"),
            section=fields.get("section", ""),
            coder_ref=int(fields.get("coder_ref", 0)),
            debug_ref=int(fields.get("debug_ref", 0)),
            source_agent=fields.get("source_agent", ""),
            parent_id=int(fields.get("parent_id", 0)),
            blocked_by=blocked_by,
            tags=tags,
            due=fields.get("due", ""),
            recur=fields.get("recur", ""),
            estimate_min=int(fields.get("estimate_min", 0)),
            actual_min=int(fields.get("actual_min", 0)),
            started_at=fields.get("started_at", ""),
            finished_at=fields.get("finished_at", ""),
            attachments=[x.strip() for x in fields.get("attachments", "").split(",") if x.strip()],
        )
    except (KeyError, ValueError):
        return None


def format_task(task: Task) -> str:
    """Format a single Task into .tasks text representation."""
    lines = [f"--- task:{task.id}"]
    lines.append(f"status: {task.status.value}")
    lines.append(f"priority: {task.priority}")
    lines.append(f"title: {task.title}")

    if task.spec:
        lines.append("spec: |")
        for spec_line in task.spec.strip().split("\n"):
            lines.append(f"  {spec_line}")
    else:
        lines.append("spec: ")

    if task.file:
        lines.append(f"file: {task.file}")
    if task.line:
        lines.append(f"line: {task.line}")
    if task.created:
        lines.append(f"created: {task.created}")
    if task.agent_type:
        lines.append(f"agent_type: {task.agent_type}")
    if task.section:
        lines.append(f"section: {task.section}")
    if task.coder_ref:
        lines.append(f"coder_ref: {task.coder_ref}")
    if task.debug_ref:
        lines.append(f"debug_ref: {task.debug_ref}")
    if task.source_agent:
        lines.append(f"source_agent: {task.source_agent}")
    if task.parent_id:
        lines.append(f"parent_id: {task.parent_id}")
    if task.blocked_by:
        lines.append(f"blocked_by: {','.join(str(x) for x in task.blocked_by)}")
    if task.tags:
        lines.append(f"tags: {','.join(task.tags)}")
    if task.due:
        lines.append(f"due: {task.due}")
    if task.recur:
        lines.append(f"recur: {task.recur}")
    if task.estimate_min:
        lines.append(f"estimate_min: {task.estimate_min}")
    if task.actual_min:
        lines.append(f"actual_min: {task.actual_min}")
    if task.started_at:
        lines.append(f"started_at: {task.started_at}")
    if task.finished_at:
        lines.append(f"finished_at: {task.finished_at}")
    if task.attachments:
        lines.append(f"attachments: {','.join(task.attachments)}")

    lines.append("---")
    return "\n".join(lines)


def format_tasks(tasks: list[Task], header: str | None = None) -> str:
    """Format a list of Tasks into .tasks file content."""
    lines = []
    if header:
        lines.append(f"--\n-- {header}\n--\n")
    for task in tasks:
        lines.append(format_task(task))
        lines.append("")
    return "\n".join(lines)


def parse_tasks_file(filepath: str) -> list[Task]:
    """Read and parse a .tasks file."""
    try:
        with open(filepath) as f:
            content = f.read()
        return parse_tasks(content)
    except FileNotFoundError:
        return []


def write_tasks_file(filepath: str, tasks: list[Task], header: str | None = None) -> None:
    """Write tasks to a .tasks file."""
    content = format_tasks(tasks, header)
    with open(filepath, "w") as f:
        f.write(content)
        if content and not content.endswith("\n"):
            f.write("\n")
