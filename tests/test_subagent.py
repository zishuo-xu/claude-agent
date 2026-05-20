from pathlib import Path

from mini_agent.config import AgentConfig
from mini_agent.llm import FinalResponseEvent, LLMResponse, TextBlock, TextDeltaEvent, ToolUseBlock
from mini_agent.permissions import PermissionMode
from mini_agent.subagent import EXPLORE_AGENT, PLAN_AGENT, VERIFY_AGENT, build_subagent_tools, run_subagent
from mini_agent.tasks import TaskState
from mini_agent.tool_registry import ToolRegistry
from mini_agent.tools import default_tools


class RecordingClient:
    def __init__(self):
        self.stream_calls = []

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])

    def stream_complete(self, **kwargs):
        self.stream_calls.append(kwargs)
        yield FinalResponseEvent(LLMResponse([TextBlock("subagent summary")]))


class EmptyFinalClient:
    def __init__(self):
        self.stream_calls = []

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])

    def stream_complete(self, **kwargs):
        self.stream_calls.append(kwargs)
        yield TextDeltaEvent("partial investigation")
        yield FinalResponseEvent(LLMResponse([]))


class LoopingToolClient:
    def __init__(self):
        self.stream_calls = []
        self.complete_calls = []

    def complete(self, **kwargs):
        self.complete_calls.append(kwargs)
        return LLMResponse([TextBlock("Findings:\nfinalized from captured transcript")])

    def stream_complete(self, **kwargs):
        self.stream_calls.append(kwargs)
        yield FinalResponseEvent(LLMResponse([ToolUseBlock(id=f"call_{len(self.stream_calls)}", name="list_files", input={"path": "."})]))


def make_config(tmp_path: Path) -> AgentConfig:
    return AgentConfig(
        workspace=tmp_path,
        provider="openai-compatible",
        model="fake-model",
        fallback_model=None,
        base_url=None,
        max_turns=3,
        permission_mode=PermissionMode.PLAN,
        context_char_budget=80_000,
    )


def test_subagent_tools_are_registered_as_read_only(tmp_path: Path):
    registry = ToolRegistry(default_tools(tmp_path, TaskState()))
    tools = build_subagent_tools(client=RecordingClient(), config=make_config(tmp_path), tool_registry=registry)

    assert set(tools) == {"explore_agent", "plan_agent", "verify_agent"}
    assert tools["explore_agent"].read_only({"prompt": "inspect"})
    assert tools["plan_agent"].read_only({"prompt": "plan"})
    assert tools["verify_agent"].read_only({"prompt": "verify"})


def test_subagent_receives_only_read_only_tools(tmp_path: Path):
    registry = ToolRegistry(default_tools(tmp_path, TaskState()))
    client = RecordingClient()

    result = run_subagent(
        definition=EXPLORE_AGENT,
        prompt="inspect files",
        client=client,
        config=make_config(tmp_path),
        tool_registry=registry,
    )

    tool_names = {tool["name"] for tool in client.stream_calls[0]["tools"]}
    assert result == "subagent summary"
    assert "read_file" in tool_names
    assert "search_text" in tool_names
    assert "write_file" not in tool_names
    assert "apply_edit" not in tool_names
    assert "run_shell" not in tool_names


def test_subagent_returns_stream_text_when_final_content_is_empty(tmp_path: Path):
    registry = ToolRegistry(default_tools(tmp_path, TaskState()))
    client = EmptyFinalClient()

    result = run_subagent(
        definition=EXPLORE_AGENT,
        prompt="inspect files",
        client=client,
        config=make_config(tmp_path),
        tool_registry=registry,
    )

    assert result == "partial investigation"


def test_subagent_finalizes_captured_output_after_turn_limit(tmp_path: Path):
    registry = ToolRegistry(default_tools(tmp_path, TaskState()))
    client = LoopingToolClient()

    result = run_subagent(
        definition=EXPLORE_AGENT,
        prompt="inspect files",
        client=client,
        config=make_config(tmp_path),
        tool_registry=registry,
    )

    assert result == "Findings:\nfinalized from captured transcript"
    assert len(client.stream_calls) == EXPLORE_AGENT.max_turns
    assert len(client.complete_calls) == 1
    assert "Captured transcript:" in client.complete_calls[0]["messages"][0]["content"]


def test_subagent_uses_agent_specific_system_prompt(tmp_path: Path):
    registry = ToolRegistry(default_tools(tmp_path, TaskState()))
    client = RecordingClient()

    run_subagent(
        definition=EXPLORE_AGENT,
        prompt="inspect files",
        client=client,
        config=make_config(tmp_path),
        tool_registry=registry,
    )

    system_prompt = client.stream_calls[0]["system"]
    assert "Explore subagent" in system_prompt
    assert "strictly read-only" in system_prompt
    assert "Findings:" in system_prompt
    assert "Relevant files:" in system_prompt
    assert "Open questions:" in system_prompt
    assert "return a final answer" in system_prompt
    assert "Use at most 3 focused tool calls" in system_prompt
    assert "If evidence is incomplete" in system_prompt


def test_subagent_default_turn_limit_matches_tool_call_budget():
    assert EXPLORE_AGENT.max_turns == 4
    assert PLAN_AGENT.max_turns == 4
    assert VERIFY_AGENT.max_turns == 4


def test_plan_subagent_prompt_has_structured_output_contract(tmp_path: Path):
    registry = ToolRegistry(default_tools(tmp_path, TaskState()))
    client = RecordingClient()

    run_subagent(
        definition=PLAN_AGENT,
        prompt="plan an implementation",
        client=client,
        config=make_config(tmp_path),
        tool_registry=registry,
    )

    system_prompt = client.stream_calls[0]["system"]
    assert "Plan subagent" in system_prompt
    assert "Goal:" in system_prompt
    assert "Steps:" in system_prompt
    assert "Critical files:" in system_prompt
    assert "Risks:" in system_prompt
    assert "Use at most 3 focused tool calls" in system_prompt


def test_verify_subagent_uses_verification_prompt(tmp_path: Path):
    registry = ToolRegistry(default_tools(tmp_path, TaskState()))
    client = RecordingClient()

    run_subagent(
        definition=VERIFY_AGENT,
        prompt="verify the latest changes",
        client=client,
        config=make_config(tmp_path),
        tool_registry=registry,
    )

    system_prompt = client.stream_calls[0]["system"]
    assert "Verification subagent" in system_prompt
    assert "Result: passed | failed | inconclusive" in system_prompt
    assert "Checks:" in system_prompt
    assert "Evidence:" in system_prompt
    assert "Risks:" in system_prompt
    assert "Do not create, edit, delete" in system_prompt
    assert "Do not use shell pipelines" in system_prompt
    assert "Result: inconclusive" in system_prompt
