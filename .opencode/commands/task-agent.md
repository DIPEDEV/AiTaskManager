---
description: Create or list agent types
agent: build
---

Manage agent types in the task pipeline.

- List all agents: `task agent list`
- Add new agent: `task agent add <name> -d "description" --pipeline-to <target>`

Examples:
```
task agent add tester -d "QA testing" --pipeline-to debug
task agent add reviewer -d "Code review" --pipeline-to coder
task agent add architect -d "Feature design" --pipeline-to coder
```

Agents with `pipeline_to` will send their completed tasks to the target agent for verification.
