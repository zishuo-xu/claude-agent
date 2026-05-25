from mini_agent.llm import ToolUseBlock
from mini_agent.permissions import PermissionContext, PermissionMode
from mini_agent.tool_core import build_tool
from mini_agent.tool_executor import ToolTurnExecutor


def test_tool_turn_executor_returns_error_for_unknown_tool():
    events = []
    executor = ToolTurnExecutor(
        tools={},
        permission_context=PermissionContext(mode=PermissionMode.PLAN),
        emit=lambda event_type, **payload: events.append((event_type, payload)),
        permission_handler=lambda _name, _input, _reason: True,
    )

    result = executor.execute([ToolUseBlock(id="call_1", name="missing_tool", input={})])

    assert result == [
        {
            "type": "tool_result",
            "tool_use_id": "call_1",
            "content": "Unknown tool: missing_tool",
            "is_error": True,
        }
    ]
    tool_errors = [event for event in events if event[0] == "tool_error"]
    assert tool_errors[0][1]["category"] == "unknown_tool"


def test_tool_turn_executor_uses_permission_handler_for_rejection():
    events = []
    tool = build_tool(
        name="write_file",
        description="Write file",
        input_schema={"type": "object"},
        call=lambda _input: "written",
    )
    executor = ToolTurnExecutor(
        tools={"write_file": tool},
        permission_context=PermissionContext(mode=PermissionMode.PLAN),
        emit=lambda event_type, **payload: events.append((event_type, payload)),
        permission_handler=lambda _name, _input, _reason: False,
    )

    result = executor.execute([ToolUseBlock(id="call_1", name="write_file", input={"path": "x.txt"})])

    assert result[0]["is_error"] is True
    assert result[0]["content"] == "Permission rejected by user"
    assert [event[0] for event in events] == [
        "tool_batch_start",
        "tool_start",
        "permission_request",
        "tool_error",
        "tool_result",
        "tool_batch_end",
    ]


def test_tool_turn_executor_denial_discourages_retrying_with_another_tool():
    tool = build_tool(
        name="write_file",
        description="Write file",
        input_schema={"type": "object"},
        call=lambda _input: "written",
    )
    executor = ToolTurnExecutor(
        tools={"write_file": tool},
        permission_context=PermissionContext(mode=PermissionMode.DONT_ASK),
        emit=lambda _event_type, **_payload: None,
        permission_handler=lambda _name, _input, _reason: True,
    )

    result = executor.execute([ToolUseBlock(id="call_1", name="write_file", input={"path": "x.txt"})])

    assert result[0]["is_error"] is True
    assert result[0]["content"].startswith("Permission denied: dontAsk mode refuses actions that need confirmation.")
    assert "Do not retry the same action with another tool" in result[0]["content"]


def test_tool_turn_executor_rejects_unknown_input_fields():
    events = []
    tool = build_tool(
        name="read_file",
        description="Read",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        call=lambda _input: "read",
        read_only=lambda _input: True,
    )
    executor = ToolTurnExecutor(
        tools={"read_file": tool},
        permission_context=PermissionContext(mode=PermissionMode.BYPASS),
        emit=lambda event_type, **payload: events.append((event_type, payload)),
        permission_handler=lambda _name, _input, _reason: True,
    )

    result = executor.execute([ToolUseBlock(id="call_1", name="read_file", input={"path": "agent.py", "limit": "50"})])

    assert result[0]["is_error"] is True
    assert result[0]["content"] == "Invalid tool input: unknown input field(s): limit"
    tool_errors = [event for event in events if event[0] == "tool_error"]
    assert tool_errors[0][1]["category"] == "validation"


def test_tool_turn_executor_rejects_missing_required_input_fields():
    tool = build_tool(
        name="read_file",
        description="Read",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
        call=lambda _input: "read",
        read_only=lambda _input: True,
    )
    executor = ToolTurnExecutor(
        tools={"read_file": tool},
        permission_context=PermissionContext(mode=PermissionMode.BYPASS),
        emit=lambda _event_type, **_payload: None,
        permission_handler=lambda _name, _input, _reason: True,
    )

    result = executor.execute([ToolUseBlock(id="call_1", name="read_file", input={})])

    assert result[0]["is_error"] is True
    assert result[0]["content"] == "Invalid tool input: missing required input field(s): path"


def test_tool_turn_executor_rejects_schema_type_mismatches():
    tool = build_tool(
        name="run_shell",
        description="Run",
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_seconds": {"type": "integer"},
            },
            "required": ["command"],
        },
        call=lambda _input: "ran",
        read_only=lambda _input: True,
    )
    executor = ToolTurnExecutor(
        tools={"run_shell": tool},
        permission_context=PermissionContext(mode=PermissionMode.BYPASS),
        emit=lambda _event_type, **_payload: None,
        permission_handler=lambda _name, _input, _reason: True,
    )

    result = executor.execute([ToolUseBlock(id="call_1", name="run_shell", input={"command": "pwd", "timeout_seconds": "5"})])

    assert result[0]["is_error"] is True
    assert result[0]["content"] == "Invalid tool input: invalid type for timeout_seconds: expected integer"


def test_tool_turn_executor_rejects_schema_enum_mismatches():
    tool = build_tool(
        name="update_task",
        description="Update",
        input_schema={
            "type": "object",
            "properties": {
                "id": {"type": "string"},
                "status": {"type": "string", "enum": ["todo", "in_progress", "done", "blocked"]},
            },
            "required": ["id", "status"],
        },
        call=lambda _input: "updated",
        read_only=lambda _input: True,
    )
    executor = ToolTurnExecutor(
        tools={"update_task": tool},
        permission_context=PermissionContext(mode=PermissionMode.BYPASS),
        emit=lambda _event_type, **_payload: None,
        permission_handler=lambda _name, _input, _reason: True,
    )

    result = executor.execute([ToolUseBlock(id="call_1", name="update_task", input={"id": "t1", "status": "later"})])

    assert result[0]["is_error"] is True
    assert result[0]["content"] == (
        "Invalid tool input: invalid value for status: expected one of todo, in_progress, done, blocked"
    )


def test_tool_turn_executor_partitions_contiguous_parallel_safe_tools():
    executor = ToolTurnExecutor(
        tools={
            "read_file": build_tool(
                name="read_file",
                description="Read",
                input_schema={"type": "object"},
                call=lambda _input: "read",
                read_only=lambda _input: True,
                concurrency_safe=lambda _input: True,
            ),
            "search_text": build_tool(
                name="search_text",
                description="Search",
                input_schema={"type": "object"},
                call=lambda _input: "search",
                read_only=lambda _input: True,
                concurrency_safe=lambda _input: True,
            ),
            "write_file": build_tool(
                name="write_file",
                description="Write",
                input_schema={"type": "object"},
                call=lambda _input: "write",
            ),
        },
        permission_context=PermissionContext(mode=PermissionMode.BYPASS),
        emit=lambda _event_type, **_payload: None,
        permission_handler=lambda _name, _input, _reason: True,
    )

    batches = executor._partition_tool_uses(
        [
            ToolUseBlock(id="call_1", name="read_file", input={}),
            ToolUseBlock(id="call_2", name="search_text", input={}),
            ToolUseBlock(id="call_3", name="write_file", input={}),
            ToolUseBlock(id="call_4", name="read_file", input={}),
            ToolUseBlock(id="call_5", name="missing_tool", input={}),
        ]
    )

    assert [(batch.parallel, [tool_use.id for tool_use in batch.tool_uses]) for batch in batches] == [
        (True, ["call_1", "call_2"]),
        (False, ["call_3"]),
        (True, ["call_4"]),
        (False, ["call_5"]),
    ]


def test_tool_turn_executor_preserves_original_result_order_across_batches():
    executor = ToolTurnExecutor(
        tools={
            "read_file": build_tool(
                name="read_file",
                description="Read",
                input_schema={"type": "object"},
                call=lambda tool_input: f"read:{tool_input['index']}",
                read_only=lambda _input: True,
                concurrency_safe=lambda _input: True,
            ),
            "write_file": build_tool(
                name="write_file",
                description="Write",
                input_schema={"type": "object"},
                call=lambda tool_input: f"write:{tool_input['index']}",
            ),
        },
        permission_context=PermissionContext(mode=PermissionMode.BYPASS),
        emit=lambda _event_type, **_payload: None,
        permission_handler=lambda _name, _input, _reason: True,
    )

    result = executor.execute(
        [
            ToolUseBlock(id="call_1", name="read_file", input={"index": 1}),
            ToolUseBlock(id="call_2", name="read_file", input={"index": 2}),
            ToolUseBlock(id="call_3", name="write_file", input={"index": 3}),
            ToolUseBlock(id="call_4", name="read_file", input={"index": 4}),
        ]
    )

    assert [item["tool_use_id"] for item in result] == ["call_1", "call_2", "call_3", "call_4"]
    assert [item["content"] for item in result] == ["read:1", "read:2", "write:3", "read:4"]


def test_tool_turn_executor_emits_batch_events_without_changing_tool_results():
    events = []
    executor = ToolTurnExecutor(
        tools={
            "read_file": build_tool(
                name="read_file",
                description="Read",
                input_schema={"type": "object"},
                call=lambda tool_input: f"read:{tool_input['index']}",
                read_only=lambda _input: True,
                concurrency_safe=lambda _input: True,
            ),
            "write_file": build_tool(
                name="write_file",
                description="Write",
                input_schema={"type": "object"},
                call=lambda tool_input: f"write:{tool_input['index']}",
            ),
        },
        permission_context=PermissionContext(mode=PermissionMode.BYPASS),
        emit=lambda event_type, **payload: events.append((event_type, payload)),
        permission_handler=lambda _name, _input, _reason: True,
    )

    result = executor.execute(
        [
            ToolUseBlock(id="call_1", name="read_file", input={"index": 1}),
            ToolUseBlock(id="call_2", name="read_file", input={"index": 2}),
            ToolUseBlock(id="call_3", name="write_file", input={"index": 3}),
        ]
    )

    batch_events = [event for event in events if event[0].startswith("tool_batch_")]

    assert [item["tool_use_id"] for item in result] == ["call_1", "call_2", "call_3"]
    assert batch_events == [
        ("tool_batch_start", {"parallel": True, "tools": ["read_file", "read_file"], "tool_use_ids": ["call_1", "call_2"]}),
        ("tool_batch_end", {"parallel": True, "tools": ["read_file", "read_file"], "tool_use_ids": ["call_1", "call_2"]}),
        ("tool_batch_start", {"parallel": False, "tools": ["write_file"], "tool_use_ids": ["call_3"]}),
        ("tool_batch_end", {"parallel": False, "tools": ["write_file"], "tool_use_ids": ["call_3"]}),
    ]
