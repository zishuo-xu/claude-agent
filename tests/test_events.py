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
