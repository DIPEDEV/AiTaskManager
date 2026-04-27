from __future__ import annotations

from pathlib import Path

from rich.console import Console

from taskcli.config import CONFIG_DIR, write_default_config
from taskcli.parser import write_tasks_file

console = Console()

AI_INSTRUCTIONS = """# Task CLI — AI Agent Instructions

This file tells you (the AI agent) how to use the `task` CLI to manage work.  
**Read this before doing anything else.**

## Quick Reference

| Command | What it does |
|---------|-------------|
| `task next -t <agent>` | Get and assign the next pending task (auto `in_progress`) |
| `task show <id> -t <agent>` | View full task details including spec |
| `task done <id> -t <agent>` | Done → deleted from source, create `[Verify]` in pipeline target |
| `task verify-pass <id> -t <agent>` | Verification passed → mark verify task `done` |
| `task verify-fail <id> -m "reason"` | Verification failed → mark done + create `[Re-check]` in source |
| `task add "title" -t <agent> -s "spec"` | Add a new task with multi-line spec |
| `task list -t <agent>` | List tasks for an agent type |
| `task agent add <name> -d "desc"` | Create a new agent type |
| `task agent list` | Show all configured agents and their pipelines |
| `task --debug <command>` | Run a command, capture errors as debug tasks |
| `task tui` | Launch interactive terminal UI |

## How the Pipeline Works

Every agent can have a `pipeline_to` target. When you run `task done` on a task:

1. **Source task is DELETED** from the source agent's file
2. **A `[Verify]` task is CREATED** in the pipeline target agent

Example — coder → debug pipeline:
```
Before:  coder.tasks → [○ Fix login]
         debug.tasks → (empty)

$ task done 1 -t coder

After:   coder.tasks → (empty, task deleted)
         debug.tasks → [○ [Verify] Fix login]
```

## Verification Flow

When you see `[Verify]` tasks in your queue:

| Result | Command | Effect |
|--------|---------|--------|
| Fix is correct | `task verify-pass <id> -t <agent>` | Mark verify task `done` ✓ |
| Fix is wrong | `task verify-fail <id> -m "reason"` | Mark verify `done` + create `[Re-check]` back in source |

```
task done (coder)          verify-pass (debug)
  ──────────► [Verify] in debug ──────────► done ✓

               verify-fail (debug)
             ──────────► [Re-check] back in coder + debug done
```

## Statuses

```
pending → in_progress → [done] → source deleted, [Verify] in pipeline target
                                                     │
                                    verify-pass ─────┤→ done ✓
                                    verify-fail ─────┤→ done + [Re-check] in source
```

## Agent Types (Dynamic)

Default agents created by `task init`:
| Agent | File | Pipeline |
|-------|------|----------|
| `coder` | `coder.tasks` | → `debug` |
| `debug` | `debug.tasks` | (none) |

Create your own with `task agent add`:
```bash
task agent add tester -d "QA testing" --pipeline-to debug
task agent add reviewer -d "Code review" --pipeline-to coder
task agent add architect -d "Feature design" --pipeline-to coder
```

Agent config is stored in `.tasks/config` (YAML). Example:
```yaml
agents:
  coder:
    file: coder.tasks
    description: Code implementation tasks
    pipeline_to: debug
  debug:
    file: debug.tasks
    description: Debugging and verification tasks
  tester:
    file: tester.tasks
    description: QA testing
    pipeline_to: debug
```

## Workflow (any coding agent, e.g. coder)

1. `task next -t <agent>` — get the next task (auto-assigned to you)
2. `task show <id> -t <agent>` — read the spec/context if needed
3. Implement the fix in the code
4. `task done <id> -t <agent>` — task deleted from your queue, verify task created downstream

## Workflow (any verification agent, e.g. debug/tester)

1. `task next -t <agent>` — get a `[Verify]` task
2. `task show <id> -t <agent>` — read the spec to understand what was done
3. Verify the fix/change is correct
4. `task verify-pass <id> -t <agent>` if OK
5. `task verify-fail <id> -m "what's wrong"` if NOT OK (creates `[Re-check]` in source)

## Adding Tasks with Specs

Use `-s` for multi-line AI context:
```bash
task add "Fix login timeout" \
  -t coder \
  -p high \
  -f src/auth/login.ts \
  -l 42 \
  -s "The login function:
  1. Doesn't handle 401 responses
  2. Needs redirect to /login on expired tokens
  3. Must clear stale tokens from storage"
```

## Adding Tasks for Other Agents

```bash
task add "Write API integration tests" -t tester -p medium -f tests/api.test.ts
task add "Review PR #42" -t reviewer -p high -s "Focus on auth module changes"
```

## TUI (Interactive Mode)

`task tui` opens a terminal UI. Keys:

| Key | Action |
|-----|--------|
| `a` | Create new task (modal with dropdowns, `Ctrl+S` to submit) |
| `n` | Get next pending task for current agent |
| `d` | Mark selected task as done (triggers pipeline if configured) |
| `p` | Pass verification on selected `[Verify]` task |
| `f` | Fail verification on selected `[Verify]` task |
| `Tab` | Switch between agent tabs |
| `q` | Quit |

Arrow keys navigate, Enter selects. Task detail shows in the right panel.

## .tasks File Format

Tasks are stored in plain text `.tasks` files. Each task is a YAML-like block:
```
--- task:1
status: pending
priority: high
title: Fix auth
spec: |
  Multi
  line
  spec
file: src/main.ts
line: 10
source_agent: coder
coder_ref: 1
created: 2026-01-01T00:00:00
---
```

**Fields:**
| Field | Required | Purpose |
|-------|----------|---------|
| `status` | yes | `pending`, `in_progress`, or `done` |
| `priority` | yes | `high`, `medium`, or `low` |
| `title` | yes | Short description |
| `spec` | no | Multi-line context for the AI (use `\\|` for indented block) |
| `file` | no | Source file location |
| `line` | no | Line number |
| `source_agent` | no | Which agent created this (for `[Verify]` and `[Re-check]` tasks) |
| `coder_ref` | no | Original task ID (for `[Verify]` tasks) |
| `created` | auto | ISO timestamp |

You can read/write `.tasks` files directly if you prefer raw file access over CLI.
"""


def run(output_dir: Path | None = None) -> None:
    """Initialize .tasks directory in current or specified directory."""
    base = (output_dir or Path.cwd()).resolve()
    tasks_dir = base / CONFIG_DIR

    if tasks_dir.exists():
        console.print(f"[yellow].tasks/ already exists in {base}[/yellow]")
        return

    tasks_dir.mkdir(parents=True, exist_ok=True)

    write_default_config(tasks_dir)
    write_tasks_file(
        str(tasks_dir / "coder.tasks"),
        [],
        "coder.tasks - Tasks for coder agent",
    )
    write_tasks_file(
        str(tasks_dir / "debug.tasks"),
        [],
        "debug.tasks - Tasks for debug agent",
    )

    ai_file = tasks_dir / "AI.md"
    ai_file.write_text(AI_INSTRUCTIONS)

    console.print(f"[green]Initialized .tasks/ in {base}[/green]")
    console.print("  Created: config, coder.tasks, debug.tasks, AI.md")
