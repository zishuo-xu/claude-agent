from pathlib import Path

from mini_agent.config import AgentConfig
from mini_agent.intent import classify_intent
from mini_agent.permissions import PermissionMode
from mini_agent.runtime import AgentRuntime
from mini_agent.tasks import TaskState
from mini_agent.tools import default_tools


class FakeClient:
    pass


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
