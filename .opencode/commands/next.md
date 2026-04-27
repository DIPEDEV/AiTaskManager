---
description: Get and assign the next pending task
agent: build
---

Run `task next -t <agent>` to get the next pending task for your agent type.

1. First, determine which agent you are. Ask the user or check the context:
   - If you're coding: use `-t coder`
   - If you're testing: use `-t tester`
   - If you're reviewing: use `-t reviewer`
   - etc.

2. Run: `task next -t <your-agent>`
   This assigns the next pending task to you (marks it in_progress).

3. Run: `task show <id> -t <your-agent>`
   This shows you the full task details including the spec with implementation instructions.

4. Do the work as described in the task spec.

5. When done: `task done <id> -t <your-agent>`
   This deletes the task from your queue and creates a [Verify] task in the pipeline target.
