from mini_agent.events import RuntimeEvent, print_runtime_event


def test_print_runtime_event_hides_tool_batch_events_by_default(capsys):
    print_runtime_event(
        RuntimeEvent("tool_batch_start", {"parallel": True, "tools": ["read_file"], "tool_use_ids": ["call_1"]})
    )
    print_runtime_event(
        RuntimeEvent("tool_batch_end", {"parallel": True, "tools": ["read_file"], "tool_use_ids": ["call_1"]})
    )

    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_runtime_event_hides_long_successful_tool_result(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "read_file", "content": "x" * 2_000, "is_error": False}))

    captured = capsys.readouterr()
    assert captured.out == "[tool_result] read_file returned 2000 chars; hidden from display.\n"


def test_print_runtime_event_keeps_short_tool_result_visible(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "read_file", "content": "short result", "is_error": False}))

    captured = capsys.readouterr()
    assert captured.out == "short result\n"


def test_print_runtime_event_keeps_error_tool_result_visible(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "read_file", "content": "error" * 400, "is_error": True}))

    captured = capsys.readouterr()
    assert "hidden from display" not in captured.out
    assert captured.out == ("error" * 400) + "\n"
