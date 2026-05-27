from mini_agent.context import MICRO_COMPACT_PLACEHOLDER
from mini_agent.context_preflight import (
    DEFAULT_FULL_COMPACT_KEEP_RECENT_MESSAGES,
    build_full_compact_summary_prompt,
    run_context_preflight,
)


def assistant_tool_use(tool_use_id: str, name: str = "read_file") -> dict:
    return {
        "role": "assistant",
        "content": [{"type": "tool_use", "id": tool_use_id, "name": name, "input": {"path": "README.md"}}],
    }


def user_tool_result(tool_use_id: str, content: str) -> dict:
    return {
        "role": "user",
        "content": [{"type": "tool_result", "tool_use_id": tool_use_id, "content": content}],
    }


def test_preflight_returns_unchanged_messages_under_budget():
    messages = [{"role": "user", "content": "hello"}]

    result = run_context_preflight(messages, char_budget=100)

    assert result.messages is messages
    assert result.input_chars == result.output_chars
    assert not result.changed
    assert result.notices == []


def test_preflight_micro_compacts_old_tool_results_before_full_compact():
    messages = []
    for index in range(8):
        tool_use_id = f"call_{index}"
        messages.append(assistant_tool_use(tool_use_id))
        messages.append(user_tool_result(tool_use_id, "x" * 100))

    result = run_context_preflight(messages, char_budget=1_200)

    assert result.micro_compacted_count == 2
    assert not result.full_compacted
    assert result.summary is None
    assert result.messages[1]["content"][0]["content"].startswith(MICRO_COMPACT_PLACEHOLDER)
    assert result.notices == ["micro-compacted 2 old tool result(s)"]


def test_preflight_full_compacts_when_micro_compact_is_not_enough():
    calls = []
    messages = [{"role": "user", "content": f"message {index} " + ("x" * 200)} for index in range(10)]

    def summarize(old_messages):
        calls.append(old_messages)
        return "summary"

    result = run_context_preflight(messages, char_budget=100, summarize=summarize)

    assert result.full_compacted
    assert result.summary == "summary"
    assert result.messages == messages[-DEFAULT_FULL_COMPACT_KEEP_RECENT_MESSAGES:]
    assert calls == [messages[:-DEFAULT_FULL_COMPACT_KEEP_RECENT_MESSAGES]]
    assert result.notices == ["compacted older conversation into summary"]


def test_full_compact_summary_prompt_preserves_current_contract():
    prompt = build_full_compact_summary_prompt([{"role": "user", "content": "edit app.py"}])

    assert "Preserve user goals, decisions, file paths, commands, and unresolved work" in prompt
    assert "Do not copy long tool outputs" in prompt
    assert "edit app.py" in prompt
