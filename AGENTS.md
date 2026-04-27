# taskCLI — AI Agent Task Management

This project provides the `task` CLI for managing agent work queues using plain-text `.tasks` files.

## CRITICAL: Task Workflow

**Always use the `task` CLI for task management.** Read `.tasks/AI.md` for full documentation.

### Startup — first thing you must do

1. If `.tasks/` directory does not exist, run: `task init`
2. If you need extra agent types (tester, reviewer, etc.): `task agent add <name> -d "description" --pipeline-to <target>`
3. Read `.tasks/AI.md` to understand the full pipeline

### Standard workflow

```
task next -t <agent>        # Get your next pending task (auto-assigned to you)
task show <id> -t <agent>   # Read the task spec and context
# ... do the work ...
task done <id> -t <agent>   # Delete from your queue, create [Verify] in pipeline target
```

### Verification workflow (e.g., review/debug/test)

```
task next -t <agent>               # Get a [Verify] task
task show <id> -t <agent>          # Read what was done
task verify-pass <id> -t <agent>   # If the work is correct ✓
task verify-fail <id> -m "reason"  # If wrong → creates [Re-check] in source
```

### Key behaviors to understand

- **Done deletes from source** — the original task is removed, only `[Verify]` remains in pipeline target
- **Any agent can have `pipeline_to`** — not just coder→debug
- **`source_agent` field** on tasks tells you which agent created them
- **Task IDs are per-agent** — id=1 in coder is different from id=1 in debug

## Building and Testing

- **Build/install**: `pip install --break-system-packages -e .` or `./install.sh` for system-wide
- **Run tests**: `python3 -m pytest tests/ -q`
- **Type check**: `python3 -m mypy src/taskcli/` (if mypy available)
- **Entry point**: `src/taskcli/main.py` → `entry()` function (handles `--debug` flag before typer)

## Project Structure

```
src/taskcli/
├── main.py          # CLI entry (typer), --debug pre-scan, agent subcommand
├── models.py        # Task, TaskStatus, AgentConfig dataclasses
├── store.py         # TaskStore CRUD, pipeline logic
├── parser.py        # Parse/write .tasks plain-text format
├── config.py        # YAML config reader/writer
├── commands/        # CLI subcommands (init, add, done, next, show, list, verify, agent)
└── tui/
    └── app.py       # Textual TUI app (dynamic tabs, task creation modal)
tests/
├── test_parser.py
├── test_store.py
├── test_pipeline.py
└── test_config.py
```

## Conventions

- Python 3.10+ with `from __future__ import annotations`
- Typer for CLI, Rich for output, Textual for TUI
- Plain-text `.tasks` files (YAML-like blocks, not JSON/YAML files)
- Generic pipeline methods (`task_done_with_pipeline`, `task_pass_verify`, `task_fail_verify`) over hardcoded agent names
- Legacy methods (`task_done_coder`, `task_pass_debug`, `task_fail_debug`) delegate to generic versions
- `install.sh` auto-detects OS and installs the `task` CLI command

## Global Mode (`--global` / `-g`)

Most commands support `-g` / `--global` to operate on the global `~/.tasks` store instead of the local `.tasks/` directory:

```bash
task list -g              # List tasks from global store
task next -t coder -g     # Get next coder task from global
task add "Quick idea" -g   # Add task to global store
```

The global store is at `~/.tasks` (configurable via `TASKCLI_GLOBAL_ROOT` env var).

## Sections

Tasks support a `--section` / `-S` flag to group them:

```bash
task add "Fix auth bug" -S bugfix -t coder
task add "Refactor API" -S refactor -t coder
task list -S bugfix      # Filter by section
```

Sections are free-form strings. Use them to organize tasks by theme, project, or workflow stage.

## MCP Server (`task mcp`)

The CLI includes an MCP (Model Context Protocol) stdio server for integration with AI tools like Claude Desktop.

```bash
task mcp                     # Start server (scope: global)
task mcp --scope project     # Use project .tasks/ instead of ~/.tasks
task mcp --scope auto        # Auto-detect (project if found, else global)
```

### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "taskcli": {
      "command": "task",
      "args": ["mcp", "--scope", "global"]
    }
  }
}
```

### Available MCP Tools

| Tool | Description |
|------|-------------|
| `task_list` | List tasks with optional filters (agent_type, status, section) |
| `task_add` | Add a new task |
| `task_show` | Show a single task by ID |
| `task_next` | Get the next pending task |
| `task_done` | Complete a task (pipelines to verification) |
| `task_verify_pass` | Pass verification |
| `task_verify_fail` | Fail verification with reason |
| `task_set_section` | Set task section |
| `task_move` | Move task between agents |
| `task_dispatch` | Dispatch a Claude subagent to work on a task |
| `agent_list` | List all configured agents |
| `section_list` | List sections for an agent |

### Available MCP Resources

```
tasks://{agent}              # Tasks for an agent
tasks://{agent}/{section}    # Tasks in a section
tasks://config               # Agent configuration
prompt://start-day           # Start day routine prompt
prompt://review-work         # Review work section prompt
prompt://triage-inbox        # Triage inbox prompt
prompt://standup             # Daily standup prompt
subscribe://tasks/{agent}    # Subscribe to task changes
```
