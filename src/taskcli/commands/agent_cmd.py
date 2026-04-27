from __future__ import annotations

from pathlib import Path

import yaml
from rich.console import Console

from taskcli.config import find_tasks_root, get_config_path, load_config, get_agent
from taskcli.parser import write_tasks_file

console = Console()


def add(
    name: str,
    description: str = "",
    pipeline_to: str = "",
) -> None:
    """Add a new agent type to .tasks/config and create its tasks file."""
    root = find_tasks_root()
    if root is None:
        console.print("[red]No .tasks directory found. Run 'task init' first.[/red]")
        return

    config_path = get_config_path(root)
    if config_path is None:
        console.print("[red]No .tasks/config found. Run 'task init' first.[/red]")
        return

    agents = load_config(config_path)

    if get_agent(name, agents):
        console.print(f"[yellow]Agent '{name}' already exists.[/yellow]")
        return

    if not description:
        description = f"{name.capitalize()} tasks"

    task_file = f"{name}.tasks"

    with open(config_path) as f:
        data = yaml.safe_load(f) or {}

    if "agents" not in data:
        data["agents"] = {}

    data["agents"][name] = {
        "file": task_file,
        "description": description,
        "pipeline_to": pipeline_to,
    }

    with open(config_path, "w") as f:
        yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)

    write_tasks_file(
        str(root / task_file),
        [],
        f"{task_file} - Tasks for {name} agent",
    )

    console.print(f"[green]Agent '{name}' added.[/green]")
    console.print(f"  File:      {task_file}")
    console.print(f"  Pipelines: {pipeline_to or '(none)'}")


def list_agents() -> None:
    """List all configured agent types."""
    agents = load_config()

    if not agents:
        console.print("[dim]No agents configured.[/dim]")
        return

    console.print("[bold]Configured agents:[/bold]")
    for agent in agents:
        pipeline = f" → {agent.pipeline_to}" if agent.pipeline_to else ""
        console.print(
            f"  [cyan]{agent.name}[/cyan]"
            f"  ({agent.file})"
            f"{pipeline}"
            f"  — {agent.description}"
        )
