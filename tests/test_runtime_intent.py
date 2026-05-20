from pathlib import Path

from mini_agent.config import AgentConfig
from mini_agent.intent import classify_intent
from mini_agent.llm import FinalResponseEvent, LLMResponse, TextBlock, TextDeltaEvent, ToolUseBlock
from mini_agent.permissions import PermissionMode
from mini_agent.runtime import AgentRuntime
from mini_agent.tasks import TaskState
from mini_agent.tool_core import build_tool
from mini_agent.tools import default_tools


class FakeClient:
    def __init__(self):
        self.complete_calls = 0

    def stream_complete(self, **_kwargs):
        yield TextDeltaEvent("hello")
        yield FinalResponseEvent(LLMResponse([TextBlock("hello")]))

    def complete(self, **_kwargs):
        self.complete_calls += 1
        return LLMResponse([TextBlock("summary")])


class ToolUseClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(LLMResponse([ToolUseBlock(id="call_1", name="run_shell", input={"command": ""})]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class PseudoToolMarkupClient:
    def stream_complete(self, **_kwargs):
        text = 'I will inspect.\n<tool_call>\n{"name": "explore_agent", "arguments": {"query": "inspect runtime"}}\n</tool_call>'
        yield TextDeltaEvent(text)
        yield FinalResponseEvent(LLMResponse([TextBlock(text)]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class StreamTextOnlyClient:
    def stream_complete(self, **_kwargs):
        yield TextDeltaEvent("stream-only text")
        yield FinalResponseEvent(LLMResponse([]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class RequestedToolThenAnswerClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(LLMResponse([ToolUseBlock(id="call_1", name="explore_agent", input={"prompt": "inspect"})]))
        else:
            yield FinalResponseEvent(LLMResponse([TextBlock("done")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


def make_runtime(tmp_path: Path) -> AgentRuntime:
    task_state = TaskState()
    return AgentRuntime(
        client=FakeClient(),  # type: ignore[arg-type]
        config=AgentConfig(
            workspace=tmp_path,
            provider="openai-compatible",
            model="fake-model",
            fallback_model=None,
            base_url=None,
            max_turns=1,
            permission_mode=PermissionMode.PLAN,
            context_char_budget=80_000,
        ),
        tools=default_tools(tmp_path, task_state),
        task_state=task_state,
    )


def make_runtime_with_client(tmp_path: Path, client) -> AgentRuntime:
    task_state = TaskState()
    return AgentRuntime(
        client=client,
        config=AgentConfig(
            workspace=tmp_path,
            provider="openai-compatible",
            model="fake-model",
            fallback_model=None,
            base_url=None,
            max_turns=1,
            permission_mode=PermissionMode.PLAN,
            context_char_budget=80_000,
        ),
        tools=default_tools(tmp_path, task_state),
        task_state=task_state,
    )


def test_runtime_hides_tools_for_general_learning(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("我想学习 Python")

    assert runtime._available_tool_specs() == []


def test_runtime_exposes_tools_for_project_question(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("解释这个项目架构")

    tool_names = {tool["name"] for tool in runtime._available_tool_specs()}

    assert "read_file" in tool_names
    assert "search_text" in tool_names


def test_runtime_prompt_includes_current_intent(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("你好")

    prompt = runtime._system_prompt()

    assert "Current user intent: casual_chat" in prompt
    assert "Do not use tools" in prompt


def test_runtime_prompt_includes_task_state(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.task_state.set_tasks(["Inspect files"])

    prompt = runtime._system_prompt()

    assert "Current tasks:" in prompt
    assert "t1 [todo] Inspect files" in prompt


def test_runtime_stream_model_call_returns_final_response(tmp_path: Path, capsys):
    runtime = make_runtime(tmp_path)

    response = runtime._stream_model_call(
        model="fake-model",
        max_tokens=10,
        system="system",
        messages=[],
        tools=[],
    )

    captured = capsys.readouterr()
    assert captured.out == "hello"
    assert response.content[0].text == "hello"


def test_runtime_stream_model_call_suppresses_pseudo_tool_markup(tmp_path: Path, capsys):
    runtime = make_runtime_with_client(tmp_path, PseudoToolMarkupClient())

    response = runtime._stream_model_call(
        model="fake-model",
        max_tokens=10,
        system="system",
        messages=[],
        tools=[],
    )

    captured = capsys.readouterr()
    assert captured.out == ""
    assert "explore_agent" in response.content[0].text


def test_runtime_stream_model_call_preserves_stream_text_when_final_content_is_empty(tmp_path: Path, capsys):
    runtime = make_runtime_with_client(tmp_path, StreamTextOnlyClient())

    response = runtime._stream_model_call(
        model="fake-model",
        max_tokens=10,
        system="system",
        messages=[],
        tools=[],
    )

    captured = capsys.readouterr()
    assert captured.out == "stream-only text"
    assert response.content[0].text == "stream-only text"


def test_runtime_normalizes_pseudo_tool_markup(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.tools["explore_agent"] = runtime.tools["read_file"]
    text = '<tool_call><invoke name="explore_agent"><query>inspect runtime</query></invoke></tool_call>'

    content = runtime._normalize_pseudo_tool_call([TextBlock(text)])

    assert len(content) == 1
    assert content[0].type == "tool_use"
    assert content[0].name == "explore_agent"
    assert content[0].input == {"prompt": "inspect runtime"}


def test_runtime_normalizes_json_pseudo_tool_markup(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.tools["explore_agent"] = runtime.tools["read_file"]
    text = '<tool_call>{"name": "explore_agent", "arguments": {"query": "inspect runtime"}}</tool_call>'

    content = runtime._normalize_pseudo_tool_call([TextBlock(text)])

    assert len(content) == 1
    assert content[0].type == "tool_use"
    assert content[0].name == "explore_agent"
    assert content[0].input == {"prompt": "inspect runtime"}


def test_runtime_micro_compacts_before_full_compact(tmp_path: Path, capsys):
    runtime = make_runtime(tmp_path)
    runtime.config.context_char_budget = 5_000
    for index in range(8):
        tool_use_id = f"call_{index}"
        runtime.state.messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": "read_file",
                        "input": {"path": "README.md"},
                    }
                ],
            }
        )
        runtime.state.messages.append(
            {
                "role": "user",
                "content": [
                    {
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": "x" * 500,
                        "is_error": False,
                    }
                ],
            }
        )

    runtime._compact_if_needed()

    captured = capsys.readouterr()
    assert "micro-compacted" in captured.out
    assert runtime.client.complete_calls == 0  # type: ignore[attr-defined]
    assert runtime.state.summary is None


def test_runtime_full_compact_still_runs_when_micro_compact_is_not_enough(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.config.context_char_budget = 100
    for index in range(8):
        runtime.state.messages.append({"role": "user", "content": f"regular message {'x' * 200} {index}"})

    runtime._compact_if_needed()

    assert runtime.client.complete_calls == 1  # type: ignore[attr-defined]
    assert runtime.state.summary == "summary"
    assert len(runtime.state.messages) == 4


def test_runtime_validates_tool_input_before_permission(tmp_path: Path, capsys):
    runtime = make_runtime_with_client(tmp_path, ToolUseClient())

    runtime.run_user_turn("run empty shell")

    captured = capsys.readouterr()
    assert "Invalid tool input: command must be a non-empty string" in captured.out
    tool_results = runtime.state.messages[-1]["content"]
    assert tool_results[0]["is_error"] is True
    assert "command must be a non-empty string" in tool_results[0]["content"]


def test_runtime_disables_requested_subagent_tool_after_one_use(tmp_path: Path):
    client = RequestedToolThenAnswerClient()
    runtime = make_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 3
    runtime.tool_registry.register(
        build_tool(
            name="explore_agent",
            description="Explore subagent",
            input_schema={"type": "object", "properties": {"prompt": {"type": "string"}}},
            call=lambda _args: "explore result",
            read_only=lambda _args: True,
        )
    )

    result = runtime.run_user_turn("用 explore_agent 找出 runtime 的职责")

    assert result == "done"
    assert client.tool_names_by_call[0] == ["explore_agent"]
    assert client.tool_names_by_call[1] == []
