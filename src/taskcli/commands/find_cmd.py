from __future__ import annotations

from pathlib import Path

import typer

from taskcli.store import TaskStore, StoreError
from taskcli.embeddings import EmbeddingsIndex

find_app = typer.Typer(help="Semantic search over tasks")


@find_app.command(name="run")
def run_cmd(
    query: str = "",
    top_k: int = 5,
    rebuild: bool = False,
) -> None:
    """Search tasks semantically using embeddings."""
    from rich.console import Console
    from rich.table import Table

    console = Console()

    if not query:
        console.print("[dim]Usage: task find 'authentication bug'[/dim]")
        return

    try:
        store = TaskStore()
    except StoreError as e:
        console.print(f"[red]Error: {e}[/red]")
        return

    root = Path.home() / ".tasks"
    if not root.exists():
        root = Path.cwd()

    idx = EmbeddingsIndex(root)

    if rebuild:
        all_tasks = store.list_tasks()
        index = idx.build_index(all_tasks)
        idx.save_index(index)
        console.print(f"[green]Index built with {len(index)} tasks.[/green]")
        return

    index = idx.load_index()
    if not index:
        all_tasks = store.list_tasks()
        index = idx.build_index(all_tasks)
        idx.save_index(index)

    results = idx.search(query, index, top_k)

    if not results:
        console.print("[dim]No results found.[/dim]")
        return

    table = Table(title=f"Search results for: {query}")
    table.add_column("Score", style="dim")
    table.add_column("Agent")
    table.add_column("ID")
    table.add_column("Title")

    for key, score in results:
        agent, task_id = key.split(":", 1)
        task = store.get(agent, int(task_id))
        title = task.title if task else "(deleted)"
        table.add_row(f"{score:.3f}", agent, task_id, title)

    console.print(table)


def search_tasks(query: str, top_k: int = 5) -> list[dict]:
    """Python API for semantic task search."""
    from pathlib import Path

    try:
        store = TaskStore()
    except StoreError:
        return []

    root = Path.home() / ".tasks"
    if not root.exists():
        root = Path.cwd()

    idx = EmbeddingsIndex(root)
    index = idx.load_index()

    if not index:
        all_tasks = store.list_tasks()
        index = idx.build_index(all_tasks)
        idx.save_index(index)

    results = idx.search(query, index, top_k)
    output = []
    for key, score in results:
        agent, task_id = key.split(":", 1)
        task = store.get(agent, int(task_id))
        if task:
            output.append({
                "agent": agent,
                "id": int(task_id),
                "title": task.title,
                "score": score,
            })
    return output