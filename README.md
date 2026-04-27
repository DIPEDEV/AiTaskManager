# AiTaskManager

Task management system for human+AI teams. Uses plain-text `.tasks` files to coordinate what each agent (human or AI) should do, and ensure nothing gets lost between work and verification phases.

## Why AiTaskManager?

Without a system like this, tasks get lost in conversations: "oh yeah, I had left it there", "that was going to be done by him", "who closed that task?". AI agents are especially prone to this — they generate code, forget about it, and there's no way to track it.

With AiTaskManager:
- Every task has a clear owner (an agent)
- When marked as "done", it automatically goes to the next agent for verification
- If verification fails, the task returns to source with the reason
- Everything is recorded in text files you can review, version with git, and search with grep

**Before AiTaskManager**: 15 Slack tabs, 3 Google docs, 2 email threads, and there are still things nobody did.

**With AiTaskManager**: `task next -t coder`, do the work, `task done`, it gets verified automatically.

## Installation

```bash
pip install --break-system-packages -e .
```

This installs the `task` command globally. Verify with:

```bash
task --help
```

## Architecture

AiTaskManager works with **agents**. An agent is simply a task queue (`coder.tasks`, `debug.tasks`, etc.). Each agent has an associated `.tasks` file.

The key concept is the **pipeline**: when a task is marked as `done`, it disappears from the current agent and appears in the next agent in the chain. This simulates the real workflow:

```
coder (implements) → debug (verifies) → ✓done
                         ↓
                    verify-fail → [Re-check] coder
```

### Why is the pipeline important?

Because in teams with AI, **nobody should mark their own work as "done"**. There should always be another person (or agent) to verify. The pipeline enforces this — you can't pass a task to "done" without it going through verification.

## Commands

### `task init`

```bash
task init                    # Create .tasks/ in current directory
task init -p /path/to/project  # Create at a specific path
```

Creates the `.tasks/` folder with base files (`coder.tasks`, `debug.tasks`) and a YAML `config`.

**When to use it**: every time you start a new project.

---

### `task add`

```bash
task add "Implement OAuth login" -t coder
task add "Fix parser bug" -t coder -p high
task add "Review PR #42" -t reviewer -S review
task add "Planning meeting" -S admin -p low
task add "Fix auth" -f src/auth.py -l 42
task add "Update tests" --tag tests,auth --due 2026-04-30
task add "Implement search" --tag search,v2 --spec "Use vec sqlite for embeddings..."
```

| Flag | Description |
|------|-------------|
| `-t` | Agent owner (default: coder) |
| `-p` | Priority: `high`, `medium`, `low` |
| `-f` | Related file (for context) |
| `-l` | Line number |
| `-S` | Section for grouping |
| `--tag` | Comma-separated tags |
| `--due` | Due date (ISO 8601) |
| `--spec` | Multi-line spec for AI context |
| `--auto-spec` | Auto-generate spec via Anthropic API |

**When to use it**: whenever a new task appears. As early as possible — don't rely on remembering it later.

---

### `task list`

```bash
task list                           # List tasks for default agent (coder)
task list -t debug                  # List for debug agent
task list -a                        # List ALL tasks from all agents
task list -s pending                # Filter by status (pending, in_progress, done)
task list -S bugfix                 # Filter by section
task list --tag auth                # Filter by tag
```

**Why it's better than a doc list**: each task has metadata (priority, file, line, tags, due date, owner agent). You can filter and search without opening a document.

---

### `task show`

```bash
task show 5 -t coder               # Show task 5 from coder
```

Shows all metadata for a task including the `spec` field which is where the AI context goes.

**When to use it**: before starting to work on a task, to understand exactly what needs to be done.

---

### `task next`

```bash
task next -t coder                  # Get next pending task and mark in_progress
task next -t coder -s              # Short format (for Claude Code statusLine)
task next -t debug                 # To verify completed tasks
```

Gets the highest priority task that is `pending`, marks it as `in_progress`, and shows it in detail. Overdue tasks (with due date in the past) are boosted to the top.

**Why it's better than "I choose what to do"**: automatic sorting by priority + overdue prevents you from getting stuck on low-priority tasks while something urgent is waiting.

---

### `task done`

```bash
task done 5 -t coder               # Mark task 5 from coder as done
```

What happens when you do `done`:
1. The task is **deleted** from `coder.tasks`
2. A task `[Verify] <title>` is created in `debug.tasks`
3. If git sync is enabled, it auto-commits

**This is the heart of the system.** `done` doesn't mean "finished forever" — it means "I'm done, I need someone to review it".

---

### `task verify-pass`

```bash
task verify-pass 3 -t debug        # Verification passed, all good
```

Marks the verification task as `done`. The coder→debug flow is closed.

---

### `task verify-fail`

```bash
task verify-fail 3 -t debug -m "Tests need to be updated"
```

What happens:
1. The verification task is marked as `done`
2. A new task `[Re-check]` is created in `coder` with the error message in the spec

The coder receives concrete feedback about what failed, without having to ask around.

---

### `task debug`

```bash
task debug python3 -m pytest tests/ -q
task debug npm run lint
task debug cargo build
```

Executes a command. If it fails (non-zero exit), captures the error and creates a task in `debug.tasks` automatically.

**Why it's useful**: when you run tests and they fail, the error is already registered as a task to debug. It doesn't get lost in the terminal output that nobody will reread.

---

### `task tui`

```bash
task tui
```

Visual interface with Textual. Navigate between agents with Tab, edit tasks, use shortcuts:

| Key | Action |
|-----|--------|
| `n` | Next task |
| `d` | Done |
| `p` | Pass (verify) |
| `f` | Fail (verify) |
| `a` | Add task |
| `Tab` | Switch agent |
| `q` | Quit |

---

### `task agent`

```bash
task agent list                     # View agents and their pipelines
task agent add tester -d "QA" --pipeline-to debug  # Create new agent
```

Agents define who does what and who they pass work to when it's ready.

---

### `task sync`

```bash
task sync init                      # Initialize git repo in .tasks/
task sync enable                    # Enable auto-commit
task sync disable                   # Disable
task sync log                       # View commit history
```

Git sync auto-commits every time a `.tasks` file is modified. This gives you a complete change history and the ability to recover if something is lost.

---

### `task mcp`

```bash
task mcp                            # MCP server in global mode
task mcp --scope project           # MCP server with local .tasks/
task mcp --scope auto              # Auto-detect
```

Starts an MCP stdio server to integrate with AIs like Claude Desktop. Add to your `claude_desktop_config.json`:

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

This allows you to use commands like `Task: List`, `Task: Next`, `Task: Done` directly from Claude Code.

---

### `task --global` / `-g`

```bash
task list -g
task next -t coder -g
task add "Random idea" -g
```

Most commands accept `-g` to operate on the global store (`~/.tasks`) instead of the local one (`.tasks/`). Useful for personal tasks that don't belong to a specific project.

---

## How an AI Works with This

The typical workflow with Claude Code (or any AI using the MCP):

1. **Start of day**: AI does `task next -t coder` and gets its highest priority task
2. **Work**: AI implements, using `task show` to see specs and `task add` to create sub-tasks
3. **Done**: when finished, does `task done <id> -t coder` — task goes to debug
4. **Verification**: another AI (or you) does `task next -t debug`, reviews the work, and uses `verify-pass` or `verify-fail`

### Why is the spec so important?

The `spec` field in each task is the **context for the AI**. When you do `task add "Fix bug" --spec "The bug is on line 42 of the parser, the problem occurs when..."`, the AI knows exactly what to do without having to figure it out. This drastically reduces the feedback cycle.

### Auto-spec

If you have an Anthropic API key, you can use `--auto-spec` so the API generates the spec automatically:

```bash
task add "Implement semantic search" --auto-spec
```

The AI analyzes the title and generates an initial specification.

---

## Configuration

`.tasks/config` file:

```yaml
agents:
  coder:
    file: coder.tasks
    description: Feature implementation
    pipeline_to: debug
  debug:
    file: debug.tasks
    description: Verification and debugging
    pipeline_to: ""

  # Custom agents
  tester:
    file: tester.tasks
    description: QA and testing
    pipeline_to: debug

git_sync: true
telemetry: false   # opt-in local stats
```

### Hooks

You can run automatic commands when events occur:

```yaml
agents:
  coder:
    hooks:
      on_done:
        - "echo 'Task #{task_id} completed'"
      on_verify_fail:
        - "echo 'Re-check: #{reason}'"
```

---

## Why Plain Text?

- **Git-friendly**: every change can be tracked, diffed, and rolled back
- **No database needed**: everything lives in files you can read with any editor
- **Easy to integrate**: grep, sed, shell scripts — everything works
- **Portable**: copy `.tasks/` anywhere and keep working

The only tradeoff is there's no automatic merge conflict resolution if two agents edit the same file simultaneously. Optional file locking is available for that if you're working in parallel with multiple AIs.

---

## Glossary

| Term | Meaning |
|------|---------|
| Agent | A task queue with an associated `.tasks` file |
| Pipeline | Flow of tasks between agents (`coder → debug → done`) |
| Store | The `.tasks/` directory with all task files |
| Global store | `~/.tasks/` — personal store shared across projects |
| Verify task | `[Verify]` task that appears in the verification agent |
| Re-check | Task created when a verification fails |
| spec | Specification field with context for the AI |

---

## FAQ

**Can I use this solo?**
Yes. Start with `task init`, use `task add` for your tasks, and `task next` to work through them. The pipeline forces you to verify your own work if you configure `coder → coder` instead of `coder → debug`.

**Can I have multiple agents of the same type?**
Not directly — IDs are per-agent. But you can use **sections** (`-S`) to subdivide, for example `work`, `admin`, `personal` within the same agent.

**What if I don't want tasks to go to debug?**
Set `pipeline_to: ""` on the agent. The task gets marked as `done` directly.

**How do I make the AI use the system automatically?**
With the MCP server (`task mcp`). Integrate it with Claude Desktop and the AI can do `task next`, `task done`, etc. without you having to do it manually.

**Where are the tests?**
```bash
python3 -m pytest tests/ -q
```
