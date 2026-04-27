from __future__ import annotations

import subprocess
import sys

import typer

quick_app = typer.Typer(help="Quick-add a task without opening terminal")


@quick_app.command(name="run")
def run_quick(
    title: str = "",
    priority: str = "medium",
    agent_type: str = "coder",
) -> None:
    """Quick-add a task via CLI (designed to be called from hotkey tools).

    Example integration:
    - Raycast: task quick --title "{clipboard}"
    - Alfred: /path/to/task quick --title "{argument}"
    - skhd: /path/to/task quick --title "from skhd"
    """
    if not title:
        typer.echo("[dim]Usage: task quick --title 'My task' [--priority high] [--agent coder][/dim]")
        return

    result = subprocess.run(
        [sys.executable, "-m", "taskcli.main", "add", title, "-t", agent_type, "-p", priority, "--global"],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        typer.echo("[green]Task added.[/green]")
    else:
        typer.echo(f"[red]Error: {result.stderr}[/red]")
        raise typer.Exit(1)


@quick_app.command(name="listen")
def listen_quick(
    port: int = 9234,
) -> None:
    """Start a lightweight HTTP server for quick-add from hotkeys.

    POST /task with JSON {"title": "...", "priority": "high"}

    This allows hotkey tools to POST a task without needing
    the full task CLI in PATH.
    """
    import json
    from http.server import HTTPServer, BaseHTTPRequestHandler

    class QuickHandler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/task":
                self.send_error(404)
                return
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            try:
                data = json.loads(body)
                title = data.get("title", "")
                if not title:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"title required")
                    return

                priority = data.get("priority", "medium")
                result = subprocess.run(
                    [sys.executable, "-m", "taskcli.main", "add", title,
                     "-p", priority, "--global"],
                    capture_output=True,
                )
                if result.returncode == 0:
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(b"ok")
                else:
                    self.send_response(500)
                    self.end_headers()
                    self.wfile.write(result.stderr.encode())
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(str(e).encode())

        def log_message(self, fmt, *args):
            pass

    server = HTTPServer(("localhost", port), QuickHandler)
    typer.echo(f"Quick-add server running on http://localhost:{port}/task")
    typer.echo("POST JSON: {\"title\": \"...\", \"priority\": \"high\"}")
    server.serve_forever()