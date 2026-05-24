from pathlib import Path

from mini_agent.config import AgentConfig
from mini_agent.llm import FinalResponseEvent, LLMResponse, TextBlock
from mini_agent.permissions import PermissionMode
from mini_agent.runtime import AgentRuntime
from mini_agent.tools import default_tools


class FinalAnswerClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(LLMResponse([TextBlock("ok")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


def make_runtime(tmp_path: Path) -> AgentRuntime:
    return AgentRuntime(
        client=FinalAnswerClient(),
        config=AgentConfig(
            workspace=tmp_path,
            provider="openai-compatible",
            model="fake-model",
            fallback_model=None,
            base_url=None,
            max_turns=1,
            permission_mode=PermissionMode.DONT_ASK,
            context_char_budget=80_000,
        ),
        tools=default_tools(tmp_path),
        event_handler=None,
    )


def test_runtime_state_tracks_turn_scoped_tool_rounds_separately(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_turn_tool_rounds = 3

    runtime.run_user_turn("你好")

    assert runtime.state.current_turn_tool_rounds == 0
    assert runtime.state.current_intent is not None
    assert runtime.state.messages[-1]["role"] == "assistant"
