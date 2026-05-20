from mini_agent.runtime import SYSTEM_PROMPT


def test_system_prompt_limits_general_learning_requests():
    assert "general learning requests" in SYSTEM_PROMPT
    assert "do not inspect the workspace" in SYSTEM_PROMPT
    assert "unless the user explicitly asks to use the project" in SYSTEM_PROMPT


def test_system_prompt_requires_real_tool_calls():
    assert "actual tool call interface" in SYSTEM_PROMPT
    assert "Do not print XML, JSON, or markdown pseudo tool calls" in SYSTEM_PROMPT
    assert "explore_agent, plan_agent, or verify_agent" in SYSTEM_PROMPT
