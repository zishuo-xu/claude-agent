from pathlib import Path

from mini_agent.intent import classify_intent
from mini_agent.tasks import TaskState
from mini_agent.tool_core import build_tool
from mini_agent.tool_registry import ToolRegistry


def test_registry_exposes_builtin_tools_for_project_questions(tmp_path: Path):
    registry = ToolRegistry.with_builtin_tools(tmp_path, TaskState())

    tool_names = {
        spec["name"]
        for spec in registry.api_specs_for_intent(classify_intent("解释这个项目架构"))
    }

    assert "read_file" in tool_names
    assert "search_text" in tool_names
    assert "list_tasks" in tool_names


def test_registry_hides_tools_for_general_learning_requests(tmp_path: Path):
    registry = ToolRegistry.with_builtin_tools(tmp_path, TaskState())

    assert registry.api_specs_for_intent(classify_intent("我想学习 Python")) == []


def test_registry_exposes_only_requested_subagent_tool(tmp_path: Path):
    registry = ToolRegistry.with_builtin_tools(tmp_path, TaskState())
    registry.register(
        build_tool(
            name="explore_agent",
            description="Explore subagent",
            input_schema={"type": "object", "properties": {"prompt": {"type": "string"}}},
            call=lambda _args: "ok",
            read_only=lambda _args: True,
        )
    )

    tool_names = {
        spec["name"]
        for spec in registry.api_specs_for_intent(classify_intent("用 explore_agent 找出 runtime 的职责"))
    }

    assert tool_names == {"explore_agent"}
