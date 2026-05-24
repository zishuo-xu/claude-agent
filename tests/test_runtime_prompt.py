from mini_agent.runtime import SYSTEM_PROMPT


def test_system_prompt_keeps_high_level_runtime_principles():
    assert "Follow the current user intent guidance" in SYSTEM_PROMPT
    assert "Work in a tight observe-think-act loop" in SYSTEM_PROMPT
    assert "Inspect before editing" in SYSTEM_PROMPT
    assert "When you finish, summarize what changed and how it was verified" in SYSTEM_PROMPT


def test_system_prompt_requires_real_tool_calls():
    assert "actual tool call interface" in SYSTEM_PROMPT
    assert "Do not print XML, JSON, or markdown pseudo tool calls" in SYSTEM_PROMPT


def test_system_prompt_does_not_duplicate_intent_specific_rules():
    assert "general learning requests" not in SYSTEM_PROMPT
    assert "For greetings or casual chat" not in SYSTEM_PROMPT
