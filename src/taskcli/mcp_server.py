from __future__ import annotations

import asyncio
import json
import os
import sys
from typing import Any

from taskcli.config import resolve_root
from taskcli.models import TaskStatus
from taskcli.store import StoreError, TaskStore


def _make_store(scope: str, root_path: str | None = None) -> TaskStore:
    if root_path:
        from pathlib import Path
        return TaskStore(Path(root_path))
    root = resolve_root(scope)  # type: ignore[arg-type]
    return TaskStore(root)


def _serialize_task(task: Any) -> dict[str, Any]:
    return {
        "id": task.id,
        "title": task.title,
        "status": task.status.value,
        "priority": task.priority,
        "spec": task.spec,
        "file": task.file,
        "line": task.line,
        "created": task.created,
        "agent_type": task.agent_type,
        "section": task.section,
        "coder_ref": task.coder_ref,
        "debug_ref": task.debug_ref,
        "source_agent": task.source_agent,
    }


def _serialize_agent(agent: Any) -> dict[str, Any]:
    return {
        "name": agent.name,
        "file": agent.file,
        "description": agent.description,
        "pipeline_to": agent.pipeline_to,
    }


def _make_error(code: int, message: str) -> dict[str, Any]:
    return {"isError": True, "code": code, "message": message}


def _make_result(content: Any) -> dict[str, Any]:
    return {"content": [{"type": "text", "text": json.dumps(content, indent=2)}]}


class MCPServer:
    """Stdio-based MCP server for taskcli."""

    def __init__(self, scope: str = "global", root_path: str | None = None):
        self.scope = os.environ.get("TASKCLI_MCP_SCOPE", scope)
        self._root_path: str | None = os.environ.get("TASKCLI_MCP_ROOT", root_path)
        self.store: TaskStore | None = None
        self._handlers: dict[str, Any] = {
            "tools/list": self._handle_tools_list,
            "tools/call": self._handle_tools_call,
            "resources/list": self._handle_resources_list,
            "resources/read": self._handle_resources_read,
        }

    def _get_store(self) -> TaskStore:
        if self.store is None:
            self.store = _make_store(self.scope, self._root_path)
        return self.store

    def _handle_tools_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        tools = [
            {
                "name": "task_list",
                "description": "List tasks with optional filters",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_type": {"type": "string"},
                        "status": {"type": "string"},
                        "section": {"type": "string"},
                    },
                },
            },
            {
                "name": "task_add",
                "description": "Add a new task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "agent_type": {"type": "string"},
                        "section": {"type": "string"},
                        "priority": {"type": "string"},
                        "spec": {"type": "string"},
                        "file": {"type": "string"},
                        "line": {"type": "integer"},
                    },
                    "required": ["title"],
                },
            },
            {
                "name": "task_show",
                "description": "Show a single task by ID",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "agent_type": {"type": "string"},
                    },
                    "required": ["task_id", "agent_type"],
                },
            },
            {
                "name": "task_next",
                "description": "Get the next pending task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_type": {"type": "string"},
                        "mark_in_progress": {"type": "boolean"},
                    },
                    "required": ["agent_type"],
                },
            },
            {
                "name": "task_done",
                "description": "Complete a task and pipeline to verification",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "agent_type": {"type": "string"},
                    },
                    "required": ["task_id", "agent_type"],
                },
            },
            {
                "name": "task_verify_pass",
                "description": "Pass verification for a task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "agent_type": {"type": "string"},
                    },
                    "required": ["task_id", "agent_type"],
                },
            },
            {
                "name": "task_verify_fail",
                "description": "Fail verification with a reason",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "agent_type": {"type": "string"},
                        "reason": {"type": "string"},
                    },
                    "required": ["task_id", "agent_type", "reason"],
                },
            },
            {
                "name": "task_set_section",
                "description": "Set the section of a task",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "agent_type": {"type": "string"},
                        "section": {"type": "string"},
                    },
                    "required": ["task_id", "agent_type", "section"],
                },
            },
            {
                "name": "task_move",
                "description": "Move a task between agents",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "from_agent": {"type": "string"},
                        "to_agent": {"type": "string"},
                    },
                    "required": ["task_id", "from_agent", "to_agent"],
                },
            },
            {
                "name": "agent_list",
                "description": "List all configured agents",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "agent_add",
                "description": "Add a new agent type",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "description": {"type": "string"},
                        "pipeline_to": {"type": "string"},
                    },
                    "required": ["name"],
                },
            },
            {
                "name": "section_list",
                "description": "List distinct sections for an agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "agent_type": {"type": "string"},
                    },
                    "required": ["agent_type"],
                },
            },
            {
                "name": "task_dispatch",
                "description": "Dispatch a Claude subagent to work on a task (launches claude CLI with task spec as prompt)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "integer"},
                        "agent_type": {"type": "string"},
                        "run": {"type": "boolean"},
                    },
                    "required": ["task_id", "agent_type"],
                },
            },
        ]
        return _make_result({"tools": tools})

    def _handle_tools_call(self, params: dict[str, Any]) -> dict[str, Any]:
        name = params.get("name", "")
        arguments = params.get("arguments", {})
        handlers: dict[str, Any] = {
            "task_list": self._tool_task_list,
            "task_add": self._tool_task_add,
            "task_show": self._tool_task_show,
            "task_next": self._tool_task_next,
            "task_done": self._tool_task_done,
            "task_verify_pass": self._tool_task_verify_pass,
            "task_verify_fail": self._tool_task_verify_fail,
            "task_set_section": self._tool_task_set_section,
            "task_move": self._tool_task_move,
            "agent_list": self._tool_agent_list,
            "agent_add": self._tool_agent_add,
            "section_list": self._tool_section_list,
            "task_dispatch": self._tool_task_dispatch,
        }
        handler = handlers.get(name)
        if handler is None:
            return _make_error(-32601, f"Unknown tool: {name}")
        try:
            return handler(arguments)
        except StoreError as e:
            return _make_error(-32000, str(e))
        except Exception as e:
            return _make_error(-32603, str(e))

    def _tool_task_list(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        agent_type = args.get("agent_type")
        status_str = args.get("status")
        section = args.get("section")
        status = TaskStatus(status_str) if status_str else None
        tasks = store.list_tasks(agent_type=agent_type, status=status, section=section)
        return _make_result([_serialize_task(t) for t in tasks])

    def _tool_task_add(self, args: dict[str, Any]) -> dict[str, Any]:
        from taskcli.models import Task

        store = self._get_store()
        agent_type = args.get("agent_type", "coder")
        task = Task(
            id=0,
            title=args["title"],
            priority=args.get("priority", "medium"),
            spec=args.get("spec", ""),
            file=args.get("file", ""),
            line=args.get("line", 0),
            section=args.get("section", ""),
        )
        created = store.add(agent_type, task)
        return _make_result(_serialize_task(created))

    def _tool_task_show(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        task = store.get(args["agent_type"], args["task_id"])
        if task is None:
            return _make_error(-32000, f"Task {args['task_id']} not found in {args['agent_type']}")
        return _make_result(_serialize_task(task))

    def _tool_task_next(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        mark = args.get("mark_in_progress", True)
        task = store.get_next(args["agent_type"], mark_in_progress=mark)
        if task is None:
            return _make_error(-32000, f"No pending tasks for {args['agent_type']}")
        return _make_result(_serialize_task(task))

    def _tool_task_done(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        result = store.task_done_with_pipeline(args["agent_type"], args["task_id"])
        return _make_result(_serialize_task(result))

    def _tool_task_verify_pass(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        vt, _ = store.task_pass_verify(args["task_id"], args["agent_type"])
        return _make_result(_serialize_task(vt))

    def _tool_task_verify_fail(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        result = store.task_fail_verify(args["task_id"], args["reason"], args["agent_type"])
        return _make_result(_serialize_task(result))

    def _tool_task_set_section(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        task = store.set_section(args["agent_type"], args["task_id"], args["section"])
        if task is None:
            return _make_error(-32000, f"Task {args['task_id']} not found in {args['agent_type']}")
        return _make_result(_serialize_task(task))

    def _tool_task_move(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        task = store.move(args["from_agent"], args["to_agent"], args["task_id"])
        if task is None:
            return _make_error(-32000, f"Task {args['task_id']} not found in {args['from_agent']}")
        return _make_result(_serialize_task(task))

    def _tool_agent_list(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        agents = [_serialize_agent(a) for a in store._agents]
        return _make_result(agents)

    def _tool_agent_add(self, args: dict[str, Any]) -> dict[str, Any]:
        name = args["name"]
        description = args.get("description", "")
        pipeline_to = args.get("pipeline_to", "")
        # just validate the store exists; actual agent add is CLI-side for now
        # This delegates to config CLI which is handled in agent subcommand
        return _make_result({
            "message": f"Agent '{name}' info received. Use 'task agent add {name}' CLI to persist.",
            "name": name,
            "description": description,
            "pipeline_to": pipeline_to,
            "note": "MCP agent_add is informational only; use CLI to persist.",
        })

    def _tool_section_list(self, args: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        sections = store.list_sections(args["agent_type"])
        return _make_result(sections)

    def _tool_task_dispatch(self, args: dict[str, Any]) -> dict[str, Any]:
        from taskcli.claude_dispatch import build_dispatch_command, run_dispatch

        task_id = args["task_id"]
        agent_type = args["agent_type"]
        run_now = args.get("run", False)

        try:
            info = build_dispatch_command(task_id, agent_type)
            if run_now:
                result = run_dispatch(task_id, agent_type)
                return _make_result(result)
            return _make_result(info)
        except Exception as e:
            return _make_error(-32000, str(e))

    def _handle_resources_list(self, _params: dict[str, Any]) -> dict[str, Any]:
        store = self._get_store()
        resources = []
        for agent in store._agents:
            resources.append({
                "uri": f"tasks://{agent.name}",
                "name": f"Tasks for {agent.name}",
                "description": agent.description,
            })
            sections = store.list_sections(agent.name)
            for section in sections:
                resources.append({
                    "uri": f"tasks://{agent.name}/{section}",
                    "name": f"Tasks for {agent.name}/{section}",
                    "description": f"Tasks in section '{section}' for {agent.name}",
                })
        resources.append({
            "uri": "tasks://config",
            "name": "Agent configuration",
            "description": "List of all configured agents and their pipelines",
        })

        prompt_resources = [
            {
                "uri": "prompt://start-day",
                "name": "Start day routine",
                "description": "Review today's tasks and overdue, start with highest priority",
            },
            {
                "uri": "prompt://review-work",
                "name": "Review work section",
                "description": "Review all tasks in 'work' section and triage",
            },
            {
                "uri": "prompt://triage-inbox",
                "name": "Triage inbox",
                "description": "Run LLM triage on all inbox tasks",
            },
            {
                "uri": "prompt://standup",
                "name": "Daily standup",
                "description": "Generate daily standup from recent done tasks",
            },
        ]

        sub_resources = [
            {
                "uri": "subscribe://tasks/{agent}",
                "name": "Subscribe to task changes",
                "description": "Receive notifications when tasks for an agent change (polling-based)",
            },
        ]
        resources.extend(sub_resources)
        return _make_result({"resources": resources})

    def _handle_resources_read(self, params: dict[str, Any]) -> dict[str, Any]:
        uri = params.get("uri", "")
        store = self._get_store()

        if uri == "tasks://config":
            agents = [_serialize_agent(a) for a in store._agents]
            return _make_result({"agents": agents})

        if uri.startswith("prompt://"):
            prompt_name = uri.replace("prompt://", "")
            prompt_text = self._get_prompt(prompt_name)
            return _make_result({"name": prompt_name, "prompt": prompt_text})

        # tasks://agent or tasks://agent/section
        parts = uri.replace("tasks://", "").split("/", 1)
        agent_type = parts[0]
        section = parts[1] if len(parts) > 1 else None

        tasks = store.list_tasks(agent_type=agent_type, section=section)
        return _make_result([_serialize_task(t) for t in tasks])

    def _get_prompt(self, name: str) -> str:
        prompts = {
            "start-day": "Review all pending tasks. Identify overdue tasks and tasks due today. Start with the highest priority task. For each task you work on, use 'task done <id> -t <agent>' when complete.",
            "review-work": "Review all tasks in the 'work' section. For each task, decide if it should remain in 'work', move to another section, or be marked done if already complete.",
            "triage-inbox": "Run LLM triage on all inbox tasks. For each inbox task, determine its proper section (work/personal/today/backlog/review) and update it using task set-section command.",
            "standup": "Generate a daily standup summary. Look at recently completed tasks (done status) from the past 24 hours. Group them by: what you did, what you're doing next, and any blockers.",
        }
        return prompts.get(name, f"Prompt '{name}' not found.")

    def _handle_request(self, request: dict[str, Any]) -> dict[str, Any]:
        method = request.get("method", "")
        params = request.get("params", {})
        req_id = request.get("id")

        # Handle initialize, notifications, etc.
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "serverInfo": {"name": "taskcli-mcp", "version": "0.1.0"},
                    "capabilities": {"tools": {}, "resources": {}},
                },
            }
        if method == "notifications/initialized":
            return {}  # no response for notifications

        if method == "ping":
            return {"jsonrpc": "2.0", "id": req_id, "result": {}}

        handler = self._handlers.get(method)
        if handler is None:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        try:
            result = handler(params)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": str(e)},
            }

    async def run(self) -> None:
        """Run the MCP server via stdio."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        w_transport, w_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        writer = asyncio.StreamWriter(w_transport, w_protocol, reader, loop)

        buffer = b""
        content_length = 0
        headers_parsed = False

        while True:
            try:
                chunk = await reader.read(4096)
                if not chunk:
                    break
            except Exception:
                break

            buffer += chunk

            while True:
                if not headers_parsed:
                    header_end = buffer.find(b"\r\n\r\n")
                    if header_end == -1:
                        break

                    headers_raw = buffer[:header_end].decode("utf-8")
                    buffer = buffer[header_end + 4:]
                    headers_parsed = True
                    content_length = 0

                    for line in headers_raw.split("\r\n"):
                        if line.lower().startswith("content-length:"):
                            try:
                                content_length = int(line.split(":", 1)[1].strip())
                            except ValueError:
                                pass

                if headers_parsed and content_length > 0:
                    if len(buffer) < content_length:
                        break

                    body_raw = buffer[:content_length].decode("utf-8")
                    buffer = buffer[content_length:]
                    headers_parsed = False
                    content_length = 0

                    try:
                        request = json.loads(body_raw)
                    except json.JSONDecodeError:
                        continue

                    response = self._handle_request(request)
                    if response:
                        resp_bytes = json.dumps(response).encode("utf-8")
                        header = f"Content-Length: {len(resp_bytes)}\r\n\r\n".encode("utf-8")
                        writer.write(header + resp_bytes)
                        await writer.drain()
        writer.close()


def main() -> None:
    """Entry point for the MCP server."""
    scope = os.environ.get("TASKCLI_MCP_SCOPE", "global")
    server = MCPServer(scope)
    asyncio.run(server.run())
