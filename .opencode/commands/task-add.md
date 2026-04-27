---
description: Add a new task for the AI pipeline
agent: build
---

Run `task add "<title>" -t <agent> -p <priority> -f <file> -l <line> -s "<spec>"` to create a new task.

1. Ask the user for the task title (required)
2. Ask which agent should do it: `-t coder`, `-t tester`, `-t reviewer`, etc.
3. Optional flags:
   - `-p high|medium|low` — priority (default: medium)
   - `-f src/file.ts` — source file location
   - `-l 42` — line number
   - `-s "multi-line spec"` — detailed instructions for the AI agent

Example:
```
task add "Fix login timeout" \
  -t coder \
  -p high \
  -f src/auth/login.ts \
  -l 42 \
  -s "The login function:
  1. Doesn't handle 401 responses
  2. Needs redirect to /login on expired tokens
  3. Must clear stale tokens"
```
