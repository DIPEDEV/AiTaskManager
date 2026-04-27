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
