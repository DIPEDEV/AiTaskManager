---
name: task-workflow
description: Use the task CLI for AI agent task management — init, next, show, done, verify-pass, verify-fail, debug
---

## What this skill covers

The `task` CLI manages agent work queues using plain-text `.tasks` files. It supports multi-agent pipelines where completed tasks flow from one agent (e.g., coder) to another for verification (e.g., debug).

## Startup — first thing you must do

1. If `.tasks/` directory does not exist, run: `task init`
2. If the project needs extra agent types: `task agent add <name> -d "description" --pipeline-to <target>`
3. Read `.tasks/AI.md` for the full pipeline documentation if it exists

## Standard workflow (any agent)

```
task next -t <agent>        # Get your next pending task (auto-assigns to you)
task show <id> -t <agent>   # Read the task spec and context
# ... do the work ...
task done <id> -t <agent>   # Delete from your queue, create [Verify] in pipeline target
```

## Verification workflow

```
task next -t <agent>               # Get a [Verify] task
task show <id> -t <agent>          # Read what was done
task verify-pass <id> -t <agent>   # If the work is correct
task verify-fail <id> -m "reason"  # If wrong → creates [Re-check] back in source agent
```

## Key behaviors

- **Done DELETES the source task** — the original task is removed, only `[Verify]` remains in the pipeline target agent
- **Any agent can have `pipeline_to`** — not just coder→debug. Use `task agent list` to see all pipelines
- **`source_agent` field** on verify tasks tells you which agent created them
- **Task IDs are per-agent** — id=1 in coder is DIFFERENT from id=1 in debug. Always use `-t <agent>` flag
- **verify-fail creates `[Re-check]`** back in the source agent with the failure reason in the spec

## Listing and adding tasks

```
task list -t <agent>     # List tasks for one agent
task list -a             # List ALL tasks across all agents
task add "title" -t <agent> -p high|medium|low -f src/file.ts -l 42 -s "multi-line context"
```

## Adding agent types

```
task agent add tester -d "QA testing" --pipeline-to debug
task agent add reviewer -d "Code review" --pipeline-to coder
task agent add architect -d "Feature design" --pipeline-to coder
task agent list           # Show all configured agents and their pipelines
```

## Error capture

When running tests, linters, or builds that fail, capture the error as a debug task:

```
task debug <command...>    # Run command, auto-create debug task if it fails
```

Examples:
```
task debug python3 -m pytest tests/ -q
task debug python3 -m mypy src/
task debug npm run lint
task debug cargo build
task debug go test ./...
```

If the command **fails** (non-zero exit):
- Errors are parsed to extract **file**, **line**, and **message**
- A new task is auto-created in `debug.tasks` with title `Debug: <command>`
- The spec contains the full error output

If the command **succeeds**: nothing is created.

Use this EVERY TIME you run tests or lint — it automatically feeds failures into the debug pipeline.

## TUI

`task tui` opens a terminal UI. Keys: `a` add task, `n` next, `d` done, `p` pass, `f` fail, `Tab` switch agent, `q` quit.
