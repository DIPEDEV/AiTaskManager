from __future__ import annotations

import asyncio
import os
from pathlib import Path

from rich.console import Console

from taskcli.mcp_server import MCPServer

console = Console()


def run(scope: str = "global", root: str | None = None) -> None:
    if scope not in ("global", "project", "auto"):
        console.print(f"[red]Error: invalid scope '{scope}'. Must be one of: global, project, auto[/red]")
        return

    root_path: Path | None = None
    if root:
        root_path = Path(root).expanduser().resolve()
        if not root_path.exists():
            console.print(f"[red]Error: root path '{root_path}' does not exist[/red]")
            return
        if not root_path.is_dir():
            console.print(f"[red]Error: root path '{root_path}' is not a directory[/red]")
            return
        os.environ["TASKCLI_MCP_ROOT"] = str(root_path)

    console.print(f"[bold cyan]Starting task MCP server...[/bold cyan]")
    console.print(f"  Scope: [green]{scope}[/green]")
    if root_path:
        console.print(f"  Root:  [green]{root_path}[/green]")
    console.print("[dim]Listening on stdio...[/dim]")

    server = MCPServer(scope=scope, root_path=str(root_path) if root_path else None)
    asyncio.run(server.run())
