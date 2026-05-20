from mini_agent.context import MICRO_COMPACT_PLACEHOLDER, micro_compact_messages


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


def user_tool_result(tool_use_id: str, content: str) -> dict:
    return {
        "role": "user",
        "content": [
            {
                "type": "tool_result",
                "tool_use_id": tool_use_id,
                "content": content,
                "is_error": False,
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
