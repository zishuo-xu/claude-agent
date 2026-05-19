from mini_agent.llm import OpenAICompatibleLLM


def test_openai_adapter_converts_tool_use_and_tool_result_messages():
    messages = [
        {"role": "user", "content": "list files"},
        {
            "role": "assistant",
            "content": [
                {"type": "text", "text": "I will inspect the workspace."},
                {"type": "tool_use", "id": "call_1", "name": "list_files", "input": {"path": "."}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": "README.md", "is_error": False}
            ],
        },
    ]

    converted = OpenAICompatibleLLM._to_openai_messages("system prompt", messages)

    assert converted[0] == {"role": "system", "content": "system prompt"}
    assert converted[2]["role"] == "assistant"
    assert converted[2]["tool_calls"][0]["function"]["name"] == "list_files"
    assert converted[3] == {"role": "tool", "tool_call_id": "call_1", "content": "README.md"}


def test_openai_adapter_preserves_reasoning_content_for_next_turn():
    messages = [
        {
            "role": "assistant",
            "content": [
                {"type": "reasoning", "content": "private reasoning that provider requires"},
                {"type": "tool_use", "id": "call_1", "name": "list_files", "input": {"path": "."}},
            ],
        },
        {
            "role": "user",
            "content": [
                {"type": "tool_result", "tool_use_id": "call_1", "content": "README.md", "is_error": False}
            ],
        },
    ]

    converted = OpenAICompatibleLLM._to_openai_messages("system prompt", messages)

    assert converted[1]["reasoning_content"] == "private reasoning that provider requires"
    assert converted[1]["tool_calls"][0]["id"] == "call_1"


def test_openai_adapter_converts_anthropic_tool_schema_to_function_schema():
    tools = [
        {
            "name": "read_file",
            "description": "Read a file.",
            "input_schema": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        }
    ]

    converted = OpenAICompatibleLLM._to_openai_tools(tools)

    assert converted[0]["type"] == "function"
    assert converted[0]["function"]["name"] == "read_file"
    assert converted[0]["function"]["parameters"]["required"] == ["path"]
