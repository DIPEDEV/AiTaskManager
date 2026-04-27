import json
import tempfile
from pathlib import Path

import pytest

from taskcli.mcp_server import MCPServer, _make_error, _make_result, _serialize_task, _serialize_agent
from taskcli.models import Task, AgentConfig
from taskcli.config import CONFIG_DIR, write_default_config
from taskcli.parser import write_tasks_file
from taskcli.store import TaskStore


@pytest.fixture
def tasks_dir():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / CONFIG_DIR
        root.mkdir()
        write_default_config(root)
        write_tasks_file(str(root / "coder.tasks"), [], "coder.tasks - test")
        write_tasks_file(str(root / "debug.tasks"), [], "debug.tasks - test")
        yield root


@pytest.fixture
def server(tasks_dir):
    return MCPServer(scope="project", root_path=str(tasks_dir))


def test_handle_initialize(server):
    result = server._handle_request({"method": "initialize", "id": 1, "params": {}})
    assert result["jsonrpc"] == "2.0"
    assert result["id"] == 1
    assert result["result"]["protocolVersion"] == "2024-11-05"
    assert result["result"]["serverInfo"]["name"] == "taskcli-mcp"
    assert "tools" in result["result"]["capabilities"]
    assert "resources" in result["result"]["capabilities"]


def test_handle_ping(server):
    result = server._handle_request({"method": "ping", "id": 1, "params": {}})
    assert result["jsonrpc"] == "2.0"
    assert result["result"] == {}


def test_handle_unknown_method(server):
    result = server._handle_request({"method": "unknown/method", "id": 1, "params": {}})
    assert result["error"]["code"] == -32601
    assert "Method not found" in result["error"]["message"]


def test_handle_notification_no_response(server):
    result = server._handle_request({"method": "notifications/initialized", "params": {}})
    assert result == {}


def test_tool_task_list(server, tasks_dir):
    store = TaskStore(tasks_dir)
    store.add("coder", Task(id=0, title="Task A", section="work"))
    store.add("coder", Task(id=0, title="Task B"))

    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_list", "arguments": {"agent_type": "coder"}},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert len(content) == 2
    assert content[0]["title"] == "Task A"
    assert content[1]["title"] == "Task B"


def test_tool_task_add(server, tasks_dir):
    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_add", "arguments": {
            "title": "New MCP task",
            "agent_type": "coder",
            "priority": "high",
            "section": "api",
        }},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert content["title"] == "New MCP task"
    assert content["priority"] == "high"
    assert content["section"] == "api"
    assert content["id"] == 1


def test_tool_task_show(server, tasks_dir):
    store = TaskStore(tasks_dir)
    store.add("coder", Task(id=0, title="Show me"))

    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_show", "arguments": {"task_id": 1, "agent_type": "coder"}},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert content["title"] == "Show me"


def test_tool_task_show_not_found(server):
    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_show", "arguments": {"task_id": 999, "agent_type": "coder"}},
    })
    result = response["result"]
    assert result["isError"] is True
    assert "not found" in result["message"]


def test_tool_task_next(server, tasks_dir):
    store = TaskStore(tasks_dir)
    store.add("coder", Task(id=0, title="Important", priority="high"))
    store.add("coder", Task(id=0, title="Later", priority="low"))

    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_next", "arguments": {"agent_type": "coder"}},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert content["title"] == "Important"
    assert content["status"] == "in_progress"


def test_tool_task_next_empty(server):
    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_next", "arguments": {"agent_type": "coder"}},
    })
    result = response["result"]
    assert result["isError"] is True
    assert "No pending tasks" in result["message"]


def test_tool_task_done(server, tasks_dir):
    store = TaskStore(tasks_dir)
    store.add("coder", Task(id=0, title="Pipeline me"))

    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_done", "arguments": {"task_id": 1, "agent_type": "coder"}},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert "Verify" in content["title"]
    assert content["agent_type"] == "debug"

    assert store.get("coder", 1) is None


def test_tool_task_verify_pass(server, tasks_dir):
    store = TaskStore(tasks_dir)
    store.add("coder", Task(id=0, title="Verify me"))
    store.task_done_with_pipeline("coder", 1)

    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_verify_pass", "arguments": {"task_id": 1, "agent_type": "debug"}},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert content["status"] == "done"


def test_tool_task_verify_fail(server, tasks_dir):
    store = TaskStore(tasks_dir)
    store.add("coder", Task(id=0, title="Fail me"))
    store.task_done_with_pipeline("coder", 1)

    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_verify_fail", "arguments": {
            "task_id": 1, "agent_type": "debug", "reason": "Not fixed"
        }},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert "Re-check" in content["title"]
    assert content["agent_type"] == "coder"


def test_tool_task_set_section(server, tasks_dir):
    store = TaskStore(tasks_dir)
    store.add("coder", Task(id=0, title="Set section"))

    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_set_section", "arguments": {
            "task_id": 1, "agent_type": "coder", "section": "backend"
        }},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert content["section"] == "backend"


def test_tool_task_set_section_not_found(server):
    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_set_section", "arguments": {
            "task_id": 999, "agent_type": "coder", "section": "nope"
        }},
    })
    result = response["result"]
    assert result["isError"] is True
    assert "not found" in result["message"]


def test_tool_task_move(server, tasks_dir):
    store = TaskStore(tasks_dir)
    store.add("coder", Task(id=0, title="Movable"))

    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_move", "arguments": {
            "task_id": 1, "from_agent": "coder", "to_agent": "debug"
        }},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert content["agent_type"] == "debug"
    assert store.get("coder", 1) is None
    assert store.get("debug", 1) is not None


def test_tool_task_move_not_found(server):
    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "task_move", "arguments": {
            "task_id": 999, "from_agent": "coder", "to_agent": "debug"
        }},
    })
    result = response["result"]
    assert result["isError"] is True
    assert "not found" in result["message"]


def test_tool_agent_list(server):
    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "agent_list", "arguments": {}},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert len(content) == 2
    names = {a["name"] for a in content}
    assert "coder" in names
    assert "debug" in names


def test_tool_agent_add(server):
    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "agent_add", "arguments": {
            "name": "reviewer", "description": "Code review", "pipeline_to": "coder"
        }},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert content["name"] == "reviewer"
    assert "informational" in content["note"]


def test_tool_section_list(server, tasks_dir):
    store = TaskStore(tasks_dir)
    store.add("coder", Task(id=0, title="A", section="api"))
    store.add("coder", Task(id=0, title="B", section="ui"))
    store.add("coder", Task(id=0, title="C"))

    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "section_list", "arguments": {"agent_type": "coder"}},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    assert set(content) == {"api", "ui"}


def test_handle_tools_call_unknown_tool(server):
    response = server._handle_request({
        "method": "tools/call",
        "id": 1,
        "params": {"name": "nonexistent_tool", "arguments": {}},
    })
    result = response["result"]
    assert result["isError"] is True
    assert result["code"] == -32601


def test_handle_tools_list(server):
    response = server._handle_request({
        "method": "tools/list",
        "id": 1,
        "params": {},
    })
    tools = json.loads(response["result"]["content"][0]["text"])["tools"]
    tool_names = {t["name"] for t in tools}
    expected = {"task_list", "task_add", "task_show", "task_next", "task_done",
                "task_verify_pass", "task_verify_fail", "task_set_section",
                "task_move", "agent_list", "agent_add", "section_list", "task_dispatch"}
    assert tool_names == expected


def test_handle_resources_list(server):
    response = server._handle_request({
        "method": "resources/list",
        "id": 1,
        "params": {},
    })
    resources = json.loads(response["result"]["content"][0]["text"])["resources"]
    uris = {r["uri"] for r in resources}
    assert "tasks://coder" in uris
    assert "tasks://debug" in uris
    assert "tasks://config" in uris


def test_handle_resources_read_config(server):
    response = server._handle_request({
        "method": "resources/read",
        "id": 1,
        "params": {"uri": "tasks://config"},
    })
    content = json.loads(response["result"]["content"][0]["text"])
    names = {a["name"] for a in content["agents"]}
    assert "coder" in names
    assert "debug" in names


def test_serialize_task():
    task = Task(id=5, title="Test", section="work", coder_ref=3, source_agent="coder")
    serialized = _serialize_task(task)
    assert serialized["id"] == 5
    assert serialized["title"] == "Test"
    assert serialized["section"] == "work"
    assert serialized["status"] == "pending"


def test_serialize_agent():
    agent = AgentConfig(name="reviewer", file="rev.tasks", description="Reviews", pipeline_to="coder")
    serialized = _serialize_agent(agent)
    assert serialized["name"] == "reviewer"
    assert serialized["pipeline_to"] == "coder"


def test_make_error():
    err = _make_error(-32000, "Something wrong")
    assert err["isError"] is True
    assert err["code"] == -32000
    assert err["message"] == "Something wrong"


def test_make_result():
    result = _make_result(["a", "b"])
    assert result["content"][0]["type"] == "text"
    assert json.loads(result["content"][0]["text"]) == ["a", "b"]
