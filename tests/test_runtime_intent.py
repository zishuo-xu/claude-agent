from pathlib import Path

from mini_agent.config import AgentConfig
from mini_agent.intent import classify_intent
from mini_agent.llm import FinalResponseEvent, LLMResponse, ReasoningBlock, TextBlock, TextDeltaEvent, ToolUseBlock
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


class RecordingCompactClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.complete_kwargs = []

    def complete(self, **kwargs):
        self.complete_calls += 1
        self.complete_kwargs.append(kwargs)
        return LLMResponse([TextBlock("summary preserving old goal")])


class ToolUseClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(LLMResponse([ToolUseBlock(id="call_1", name="run_shell", input={"command": ""})]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class WriteFileToolClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(
            LLMResponse([ToolUseBlock(id="call_1", name="write_file", input={"path": "x.txt", "content": "x"})])
        )

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class UnknownToolClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(LLMResponse([ToolUseBlock(id="call_1", name="missing_tool", input={})]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class AlwaysToolClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(LLMResponse([ToolUseBlock(id="call_1", name="read_file", input={"path": "README.md"})]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class FallbackModelClient:
    def __init__(self):
        self.models = []

    def stream_complete(self, **kwargs):
        self.models.append(kwargs["model"])
        if kwargs["model"] == "fake-model":
            raise RuntimeError("primary unavailable")
        yield FinalResponseEvent(LLMResponse([TextBlock("fallback ok")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class FailingModelClient:
    def stream_complete(self, **_kwargs):
        raise RuntimeError("model down")

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


class EmptyResponseClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(LLMResponse([]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class WhitespaceResponseClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(LLMResponse([TextBlock("  \n")]))

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


class ProjectQuestionToolThenAnswerClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(LLMResponse([ToolUseBlock(id="call_1", name="read_file", input={"path": "docs/architecture.md"})]))
        else:
            yield FinalResponseEvent(LLMResponse([TextBlock("architecture summary")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class ProjectQuestionListThenReadClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(LLMResponse([ToolUseBlock(id="call_1", name="list_files", input={"path": "."})]))
        elif self.stream_calls == 2:
            yield FinalResponseEvent(
                LLMResponse([ToolUseBlock(id="call_2", name="read_file", input={"path": "docs/architecture.md"})])
            )
        else:
            yield FinalResponseEvent(LLMResponse([TextBlock("architecture summary")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class HiddenProjectListFilesClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(LLMResponse([ToolUseBlock(id="call_1", name="list_files", input={"path": "."})]))
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


def make_silent_runtime_with_client(tmp_path: Path, client) -> AgentRuntime:
    runtime = make_runtime_with_client(tmp_path, client)
    runtime.event_handler = None
    return runtime


def test_runtime_hides_tools_for_general_learning(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("我想学习 Python")

    assert runtime._available_tool_specs() == []


def test_runtime_exposes_tools_for_project_question(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("看看这个项目")

    tool_names = {tool["name"] for tool in runtime._available_tool_specs()}

    assert tool_names == {"list_files", "read_file", "search_text"}
    assert "read_file" in tool_names
    assert "search_text" in tool_names


def test_runtime_hides_list_files_for_project_question_with_clear_docs(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("解释这个项目架构")

    tool_names = {tool["name"] for tool in runtime._available_tool_specs()}

    assert tool_names == {"read_file", "search_text"}


def test_runtime_rejects_hidden_tool_execution_for_project_question(tmp_path: Path):
    client = HiddenProjectListFilesClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 2

    result = runtime.run_user_turn("这个项目结构是什么？")

    assert result == "done"
    assert client.tool_names_by_call == [["read_file", "search_text"], ["read_file", "search_text"]]
    tool_errors = [event for event in runtime.state.events if event.type == "tool_error"]
    assert tool_errors[0].payload["name"] == "list_files"
    assert tool_errors[0].payload["category"] == "unknown_tool"
    assert runtime.state.messages[-2]["content"][0]["content"] == "Unknown tool: list_files"


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


def test_runtime_records_lightweight_events_for_final_answer(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, FakeClient())

    result = runtime.run_user_turn("你好")

    assert result == "hello"
    event_types = [event.type for event in runtime.state.events]
    assert event_types == [
        "turn_start",
        "model_start",
        "text_delta",
        "assistant_message",
        "turn_transition",
        "final_answer",
    ]
    assert runtime.state.events[1].payload["visible_tools"] == 0
    assert runtime.state.events[-2].payload["reason"] == "final_answer"


def test_runtime_loop_has_named_stage_methods(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, FakeClient())

    assert callable(runtime._begin_turn)
    assert callable(runtime._record_assistant_response)
    assert callable(runtime._handle_final_answer)
    assert callable(runtime._handle_tool_turn)


def test_runtime_records_tool_events_and_next_turn_transition(tmp_path: Path):
    client = ProjectQuestionToolThenAnswerClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 3
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text("architecture", encoding="utf-8")

    result = runtime.run_user_turn("解释当前项目架构")

    assert result == "architecture summary"
    event_types = [event.type for event in runtime.state.events]
    assert "tool_start" in event_types
    assert "tool_result" in event_types
    assert [event.payload["reason"] for event in runtime.state.events if event.type == "turn_transition"] == [
        "tool_use",
        "next_turn",
        "final_answer",
    ]


def test_runtime_can_disable_event_printing(tmp_path: Path, capsys):
    runtime = make_silent_runtime_with_client(tmp_path, FakeClient())

    runtime.run_user_turn("你好")

    captured = capsys.readouterr()
    assert captured.out == ""


def test_runtime_uses_permission_handler_for_ask_decisions(tmp_path: Path, capsys):
    runtime = make_silent_runtime_with_client(tmp_path, WriteFileToolClient())
    runtime.permission_handler = lambda _name, _input, _reason: False

    runtime.run_user_turn("新增 tmp/x.txt，内容是 x")

    captured = capsys.readouterr()
    assert captured.out == ""
    event_types = [event.type for event in runtime.state.events]
    assert "permission_request" in event_types
    tool_results = runtime.state.messages[-1]["content"]
    assert tool_results[0]["is_error"] is True
    assert tool_results[0]["content"] == "Permission rejected by user"
    assert not (tmp_path / "x.txt").exists()


def test_runtime_emits_tool_error_for_invalid_tool_input(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, ToolUseClient())

    runtime.run_user_turn("请调用 run_shell，command 为空字符串")

    tool_errors = [event for event in runtime.state.events if event.type == "tool_error"]
    assert tool_errors[0].payload["name"] == "run_shell"
    assert tool_errors[0].payload["category"] == "validation"


def test_runtime_emits_tool_error_for_unknown_tool(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, UnknownToolClient())

    runtime.run_user_turn("use unknown tool")

    tool_errors = [event for event in runtime.state.events if event.type == "tool_error"]
    assert tool_errors[0].payload["name"] == "missing_tool"
    assert tool_errors[0].payload["category"] == "unknown_tool"
    assert runtime.state.messages[-1]["content"][0]["content"] == "Unknown tool: missing_tool"


def test_runtime_emits_turn_limit_when_tool_loop_exhausts_max_turns(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, AlwaysToolClient())
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")

    result = runtime.run_user_turn("keep reading")

    assert result == ""
    event_types = [event.type for event in runtime.state.events]
    assert "turn_limit_reached" in event_types
    assert event_types[-1] == "stopped"


def test_runtime_emits_model_error_before_fallback(tmp_path: Path):
    client = FallbackModelClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.config.fallback_model = "fallback-model"

    result = runtime.run_user_turn("hello")

    assert result == "fallback ok"
    assert client.models == ["fake-model", "fallback-model"]
    event_types = [event.type for event in runtime.state.events]
    assert "model_error" in event_types
    assert "model_fallback" in event_types


def test_runtime_emits_model_error_before_raising_without_fallback(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, FailingModelClient())

    try:
        runtime.run_user_turn("hello")
    except RuntimeError as exc:
        assert str(exc) == "model down"
    else:
        raise AssertionError("expected model failure")

    model_errors = [event for event in runtime.state.events if event.type == "model_error"]
    assert model_errors[0].payload["model"] == "fake-model"
    assert model_errors[0].payload["error_type"] == "RuntimeError"


def test_runtime_returns_fallback_for_empty_casual_response(tmp_path: Path, capsys):
    runtime = make_runtime_with_client(tmp_path, EmptyResponseClient())

    result = runtime.run_user_turn("你好")

    captured = capsys.readouterr()
    assert result == "你好，我在。"
    assert "你好，我在。" in captured.out


def test_runtime_returns_fallback_for_whitespace_response(tmp_path: Path, capsys):
    runtime = make_runtime_with_client(tmp_path, WhitespaceResponseClient())

    result = runtime.run_user_turn("解释当前项目架构")

    captured = capsys.readouterr()
    assert result == "我没有生成可见回复。你刚才的问题是：解释当前项目架构"
    assert "我没有生成可见回复" in captured.out


def test_runtime_normalizes_pseudo_tool_markup(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.tools["explore_agent"] = runtime.tools["read_file"]
    text = '<tool_call><invoke name="explore_agent"><query>inspect runtime</query></invoke></tool_call>'

    content = runtime._normalize_pseudo_tool_call([TextBlock(text)])

    assert len(content) == 1
    assert content[0].type == "tool_use"
    assert content[0].name == "explore_agent"
    assert content[0].input == {"prompt": "inspect runtime"}


def test_runtime_preserves_reasoning_when_normalizing_pseudo_tool_markup(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.tools["explore_agent"] = runtime.tools["read_file"]
    text = '<tool_call>{"name": "explore_agent", "arguments": {"query": "inspect runtime"}}</tool_call>'

    content = runtime._normalize_pseudo_tool_call([ReasoningBlock("thinking state"), TextBlock(text)])

    assert len(content) == 2
    assert content[0].type == "reasoning"
    assert content[0].content == "thinking state"
    assert content[1].type == "tool_use"
    assert content[1].name == "explore_agent"


def test_runtime_normalizes_json_pseudo_tool_markup(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.tools["explore_agent"] = runtime.tools["read_file"]
    text = '<tool_call>{"name": "explore_agent", "arguments": {"query": "inspect runtime"}}</tool_call>'

    content = runtime._normalize_pseudo_tool_call([TextBlock(text)])

    assert len(content) == 1
    assert content[0].type == "tool_use"
    assert content[0].name == "explore_agent"
    assert content[0].input == {"prompt": "inspect runtime"}


def test_runtime_normalizes_function_parameter_pseudo_tool_markup(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    text = "<tool_call><function=read_file><parameter=file_path>README.md</parameter></function></tool_call>"

    content = runtime._normalize_pseudo_tool_call([TextBlock(text)])

    assert len(content) == 1
    assert content[0].type == "tool_use"
    assert content[0].name == "read_file"
    assert content[0].input == {"path": "README.md"}


def test_runtime_does_not_normalize_hidden_pseudo_tool_markup(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("这个项目结构是什么？")
    text = '<tool_call>{"name": "list_files", "arguments": {"path": "."}}</tool_call>'

    content = runtime._normalize_pseudo_tool_call([TextBlock(text)])

    assert len(content) == 1
    assert content[0].type == "text"
    assert content[0].text == text


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


def test_runtime_full_compact_preserves_old_goal_in_summary_prompt_and_recent_messages(tmp_path: Path):
    client = RecordingCompactClient()
    runtime = make_runtime_with_client(tmp_path, client)
    runtime.config.context_char_budget = 100
    runtime.state.messages = [
        {"role": "user", "content": "User goal: refactor runtime without losing tests."},
        {"role": "assistant", "content": "I will inspect the runtime first."},
        {"role": "user", "content": "Older detail " + ("x" * 200)},
        {"role": "assistant", "content": "Older response " + ("y" * 200)},
        {"role": "user", "content": "Recent user asks to keep README updated."},
        {"role": "assistant", "content": "Recent assistant confirms README update."},
        {"role": "user", "content": "Recent user asks to run tests."},
        {"role": "assistant", "content": "Recent assistant will run pytest."},
    ]

    runtime._compact_if_needed()

    summary_prompt = client.complete_kwargs[0]["messages"][0]["content"]
    assert "User goal: refactor runtime without losing tests." in summary_prompt
    assert runtime.state.summary == "summary preserving old goal"
    assert runtime.state.messages == [
        {"role": "user", "content": "Recent user asks to keep README updated."},
        {"role": "assistant", "content": "Recent assistant confirms README update."},
        {"role": "user", "content": "Recent user asks to run tests."},
        {"role": "assistant", "content": "Recent assistant will run pytest."},
    ]


def test_runtime_injects_full_compact_summary_into_system_prompt(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.summary = "Preserve user goal and edited files."

    prompt = runtime._system_prompt()

    assert "Conversation summary so far:" in prompt
    assert "Preserve user goal and edited files." in prompt


def test_project_question_prompt_prefers_doc_entry_points(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("解释当前项目架构")

    prompt = runtime._system_prompt()

    assert "Use the smallest useful read path" in prompt
    assert "README.md" in prompt
    assert "docs/context-map.md" in prompt
    assert "docs/architecture.md" in prompt
    assert "Use list_files only when the target file is unclear" in prompt
    assert "Answer the user's specific question directly and concisely" in prompt
    assert "Do not restate whole documents" in prompt
    assert "unless the user explicitly asks for detail" in prompt


def test_runtime_validates_tool_input_before_permission(tmp_path: Path, capsys):
    runtime = make_runtime_with_client(tmp_path, ToolUseClient())

    runtime.run_user_turn("请调用 run_shell，command 为空字符串")

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


def test_runtime_disables_project_question_tools_after_one_tool_round(tmp_path: Path):
    client = ProjectQuestionToolThenAnswerClient()
    runtime = make_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 3
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text("architecture", encoding="utf-8")

    result = runtime.run_user_turn("解释当前项目架构")

    assert result == "architecture summary"
    assert client.tool_names_by_call[0] == ["read_file", "search_text"]
    assert client.tool_names_by_call[1] == []


def test_runtime_allows_project_question_to_read_after_listing_files(tmp_path: Path):
    client = ProjectQuestionListThenReadClient()
    runtime = make_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 4
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text("architecture", encoding="utf-8")

    result = runtime.run_user_turn("看看这个项目")

    assert result == "architecture summary"
    assert client.tool_names_by_call[0] == ["list_files", "read_file", "search_text"]
    assert client.tool_names_by_call[1] == ["list_files", "read_file", "search_text"]
    assert client.tool_names_by_call[2] == []
