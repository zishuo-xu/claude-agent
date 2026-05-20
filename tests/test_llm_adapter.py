from types import SimpleNamespace

from mini_agent.llm import FinalResponseEvent, OpenAICompatibleLLM, OpenAIStreamAccumulator, TextDeltaEvent


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


def test_openai_stream_accumulator_rebuilds_text_and_tool_call():
    accumulator = OpenAIStreamAccumulator()

    accumulator.add_text("hel")
    accumulator.add_text("lo")
    accumulator.add_reasoning("think")
    accumulator.add_tool_call_delta(
        SimpleNamespace(
            index=0,
            id="call_1",
            function=SimpleNamespace(name="read_file", arguments='{"path"'),
        )
    )
    accumulator.add_tool_call_delta(
        SimpleNamespace(
            index=0,
            id=None,
            function=SimpleNamespace(name=None, arguments=':"README.md"}'),
        )
    )

    response = accumulator.to_response()

    assert response.content[0].type == "reasoning"
    assert response.content[1].text == "hello"
    assert response.content[2].name == "read_file"
    assert response.content[2].input == {"path": "README.md"}


def test_streaming_code_should_ignore_empty_choices_chunks():
    class FakeCompletions:
        def create(self, **_kwargs):
            yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="hi"))])
            yield SimpleNamespace(choices=[])

    llm = OpenAICompatibleLLM(api_key="test", base_url="https://example.com/v1")
    llm.client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))

    events = list(
        llm.stream_complete(
            model="fake",
            max_tokens=10,
            system="system",
            messages=[{"role": "user", "content": "hi"}],
            tools=[],
        )
    )

    assert isinstance(events[0], TextDeltaEvent)
    assert events[0].text == "hi"
    assert isinstance(events[-1], FinalResponseEvent)
    assert events[-1].response.content[0].text == "hi"
