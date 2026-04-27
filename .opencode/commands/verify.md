---
description: Verify a task (pass or fail with feedback)
agent: build
---

Run the verification workflow on a [Verify] task.

1. `task next -t debug` (or your verify agent type) — get the next [Verify] task
2. `task show <id> -t debug` — read what the coding agent did
3. Verify the work is correct by checking the code changes
4. If CORRECT: `task verify-pass <id> -t debug`
5. If WRONG: `task verify-fail <id> -t debug -m "specific reason what's broken"`

On fail, a [Re-check] task is automatically created back in the source agent.
