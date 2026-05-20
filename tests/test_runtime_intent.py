from pathlib import Path

from mini_agent.config import AgentConfig
from mini_agent.intent import classify_intent
from mini_agent.llm import FinalResponseEvent, LLMResponse, TextBlock, TextDeltaEvent
from mini_agent.permissions import PermissionMode
from mini_agent.runtime import AgentRuntime
from mini_agent.tasks import TaskState
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
