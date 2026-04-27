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
            coder_ref=int(fields.get("coder_ref", 0)),
            debug_ref=int(fields.get("debug_ref", 0)),
            source_agent=fields.get("source_agent", ""),
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
    if task.coder_ref:
        lines.append(f"coder_ref: {task.coder_ref}")
    if task.debug_ref:
        lines.append(f"debug_ref: {task.debug_ref}")
    if task.source_agent:
        lines.append(f"source_agent: {task.source_agent}")

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
