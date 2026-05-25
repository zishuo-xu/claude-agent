from mini_agent.context import COMPACTABLE_TOOL_NAMES, DEFAULT_KEEP_RECENT_TOOL_RESULTS, MICRO_COMPACT_PLACEHOLDER, micro_compact_messages


def assistant_tool_use(tool_use_id: str, name: str) -> dict:
    return {
        "role": "assistant",
        "content": [
            {
                "type": "tool_use",
                "id": tool_use_id,
                "name": name,
                "input": {"path": "README.md"},
            }
        ],
    }


def user_tool_result(tool_use_id: str, content: str, *, is_error: bool = False) -> dict:
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": content,
                "is_error": is_error,
            }
        ],
    }


def test_micro_compact_clears_old_tool_results_and_keeps_recent_ones():
    messages = []
    for index in range(4):
        tool_use_id = f"call_{index}"
        messages.append(assistant_tool_use(tool_use_id, "read_file"))
        messages.append(user_tool_result(tool_use_id, f"large result {index}"))

    result = micro_compact_messages(messages, keep_recent_tool_results=2)

    assert result.compacted_count == 2
    assert result.messages[1]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)
    assert result.messages[3]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)
    assert result.messages[5]["content"][0]["content"] == "large result 2"
    assert result.messages[7]["content"][0]["content"] == "large result 3"


def test_micro_compact_does_not_clear_user_text_or_assistant_text():
    messages = [
        {"role": "user", "content": "please inspect this project"},
        {"role": "assistant", "content": [{"type": "text", "text": "I will inspect it."}]},
        assistant_tool_use("call_1", "read_file"),
        user_tool_result("call_1", "large result 1"),
        assistant_tool_use("call_2", "read_file"),
        user_tool_result("call_2", "large result 2"),
    ]

    result = micro_compact_messages(messages, keep_recent_tool_results=1)

    assert result.messages[0]["content"] == "please inspect this project"
    assert result.messages[1]["content"][0]["text"] == "I will inspect it."
    assert result.messages[3]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)
    assert result.messages[5]["content"][0]["content"] == "large result 2"


def test_micro_compact_ignores_non_compactable_tools():
    messages = [
        assistant_tool_use("call_1", "set_tasks"),
        user_tool_result("call_1", "task state"),
        assistant_tool_use("call_2", "read_file"),
        user_tool_result("call_2", "large result 2"),
    ]

    result = micro_compact_messages(messages, keep_recent_tool_results=0)

    assert result.compacted_count == 1
    assert result.messages[1]["content"][0]["content"] == "task state"
    assert result.messages[3]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)


def test_micro_compact_keeps_error_tool_results():
    messages = [
        assistant_tool_use("call_1", "read_file"),
        user_tool_result("call_1", "FileNotFoundError: missing file", is_error=True),
        assistant_tool_use("call_2", "read_file"),
        user_tool_result("call_2", "large result 2"),
        assistant_tool_use("call_3", "search_text"),
        user_tool_result("call_3", "large result 3"),
    ]

    result = micro_compact_messages(messages, keep_recent_tool_results=0)

    assert result.compacted_count == 2
    assert result.messages[1]["content"][0]["content"] == "FileNotFoundError: missing file"
    assert result.messages[3]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)
    assert result.messages[5]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)


def test_micro_compact_keeps_default_recent_six_compactable_results():
    messages = []
    for index in range(8):
        tool_use_id = f"call_{index}"
        messages.append(assistant_tool_use(tool_use_id, "read_file"))
        messages.append(user_tool_result(tool_use_id, f"large result {index}"))

    result = micro_compact_messages(messages)

    assert result.compacted_count == 2
    assert DEFAULT_KEEP_RECENT_TOOL_RESULTS == 6
    assert result.messages[1]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)
    assert result.messages[3]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)
    assert [result.messages[index]["content"][0]["content"] for index in range(5, 16, 2)] == [
        "large result 2",
        "large result 3",
        "large result 4",
        "large result 5",
        "large result 6",
        "large result 7",
    ]


def test_micro_compact_does_not_clear_tool_result_without_matching_tool_use():
    messages = [
        user_tool_result("orphan_call", "manual tool result should stay"),
        assistant_tool_use("call_1", "read_file"),
        user_tool_result("call_1", "large result 1"),
    ]

    result = micro_compact_messages(messages, keep_recent_tool_results=0)

    assert result.compacted_count == 1
    assert result.messages[0]["content"][0]["content"] == "manual tool result should stay"
    assert result.messages[2]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)


def test_default_compactable_tool_set_excludes_task_tools():
    assert {"set_tasks", "update_task", "list_tasks"}.isdisjoint(COMPACTABLE_TOOL_NAMES)
    assert {"read_file", "search_text", "run_shell"}.issubset(COMPACTABLE_TOOL_NAMES)
