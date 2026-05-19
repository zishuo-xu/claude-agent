from mini_agent.runtime import SYSTEM_PROMPT


def test_system_prompt_limits_general_learning_requests():
    assert "general learning requests" in SYSTEM_PROMPT
    assert "do not inspect the workspace" in SYSTEM_PROMPT
    assert "unless the user explicitly asks to use the project" in SYSTEM_PROMPT
