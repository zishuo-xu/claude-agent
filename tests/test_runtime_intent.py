from pathlib import Path

from mini_agent.config import AgentConfig
from mini_agent.focus import FocusKind
from mini_agent.intent import Intent, classify_intent
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


class PreflightBlockedClient(FakeClient):
    def __init__(self):
        super().__init__()
        self.stream_calls = 0

    def stream_complete(self, **_kwargs):
        self.stream_calls += 1
        yield FinalResponseEvent(LLMResponse([TextBlock("should not be called")]))


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


class FinalSummaryWithExtraToolClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(
            LLMResponse(
                [
                    TextBlock("压力测试结果：通过\n\n通过标准对照：全部通过\n\n是否需要修复：不需要"),
                    ToolUseBlock(id="call_1", name="write_file", input={"path": "x.txt", "content": "oops"}),
                ]
            )
        )

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class StreamedFinalSummaryWithExtraToolClient:
    def stream_complete(self, **_kwargs):
        yield TextDeltaEvent("压力测试结果：通过\n\n通过标准对照：全部通过\n\n是否需要修复：不需要")
        yield FinalResponseEvent(
            LLMResponse([ToolUseBlock(id="call_1", name="write_file", input={"path": "x.txt", "content": "oops"})])
        )

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class PermissionDeniedThenAnswerClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(
                LLMResponse([ToolUseBlock(id="call_1", name="write_file", input={"path": "x.txt", "content": "x"})])
            )
        else:
            yield FinalResponseEvent(LLMResponse([TextBlock("permission boundary explained")]))

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


class SplitStreamTextClient:
    def stream_complete(self, **_kwargs):
        yield TextDeltaEvent("hello ")
        yield TextDeltaEvent("stream")
        yield FinalResponseEvent(LLMResponse([TextBlock("hello stream")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class FinalTextWithoutDeltaClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(LLMResponse([TextBlock("final-only text")]))

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


class ProjectQAAcceptanceMultiReadClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(
                LLMResponse([ToolUseBlock(id="call_1", name="read_file", input={"path": "docs/architecture.md"})])
            )
        elif self.stream_calls == 2:
            yield FinalResponseEvent(
                LLMResponse([ToolUseBlock(id="call_2", name="read_file", input={"path": "docs/current-features.md"})])
            )
        elif self.stream_calls == 3:
            yield FinalResponseEvent(
                LLMResponse([ToolUseBlock(id="call_3", name="read_file", input={"path": "docs/roadmap.md"})])
            )
        elif self.stream_calls == 4:
            yield FinalResponseEvent(
                LLMResponse([ToolUseBlock(id="call_4", name="read_file", input={"path": "docs/context-map.md"})])
            )
        else:
            yield FinalResponseEvent(LLMResponse([TextBlock("项目问答验收总结")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class ClarifyThenWriteClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(LLMResponse([TextBlock("请确认风格、设定、长度和文件名？")]))
        elif self.stream_calls == 2:
            yield FinalResponseEvent(
                LLMResponse(
                    [
                        ToolUseBlock(
                            id="call_1",
                            name="write_file",
                            input={
                                "path": "novel.md",
                                "content": "# 校园长篇\n\n人物设定和第一批正文。",
                            },
                        )
                    ]
                )
            )
        else:
            yield FinalResponseEvent(LLMResponse([TextBlock("已创建 novel.md，后续可以继续追加。")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class ReadOnlyThenClarifyThenWriteClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(LLMResponse([ToolUseBlock(id="call_1", name="list_files", input={"path": "."})]))
        elif self.stream_calls == 2:
            yield FinalResponseEvent(LLMResponse([TextBlock("请确认风格、设定、长度和文件名？")]))
        elif self.stream_calls == 3:
            yield FinalResponseEvent(
                LLMResponse(
                    [
                        ToolUseBlock(
                            id="call_2",
                            name="write_file",
                            input={"path": "novel.md", "content": "# 第一批\n"},
                        )
                    ]
                )
            )
        else:
            yield FinalResponseEvent(LLMResponse([TextBlock("已创建 novel.md，后续可以继续追加。")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class ContinueAfterWriteClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(
                LLMResponse(
                    [
                        ToolUseBlock(
                            id="call_1",
                            name="write_file",
                            input={"path": "novel.md", "content": "# 第一批\n"},
                        )
                    ]
                )
            )
        elif self.stream_calls == 2:
            yield FinalResponseEvent(LLMResponse([TextBlock("已创建 novel.md，后续可以继续追加。")]))
        elif self.stream_calls == 3:
            yield FinalResponseEvent(
                LLMResponse(
                    [
                        ToolUseBlock(
                            id="call_2",
                            name="edit_file",
                            input={
                                "path": "novel.md",
                                "old": "# 第一批\n",
                                "new": "# 第一批\n\n第二批正文。\n",
                            },
                        )
                    ]
                )
            )
        else:
            yield FinalResponseEvent(LLMResponse([TextBlock("已追加第二批。")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class DocumentOutputFollowupClient:
    def __init__(self):
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        yield FinalResponseEvent(
            LLMResponse(
                [
                    ToolUseBlock(
                        id="call_1",
                        name="write_file",
                        input={"path": "output.md", "content": "# 心动频率\n\n小说大纲"},
                    )
                ]
            )
        )

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class LongConversationFocusClient:
    def __init__(self):
        self.stream_calls = 0
        self.tool_names_by_call = []

    def stream_complete(self, **kwargs):
        self.stream_calls += 1
        self.tool_names_by_call.append([tool["name"] for tool in kwargs["tools"]])
        if self.stream_calls == 1:
            yield FinalResponseEvent(
                LLMResponse(
                    [
                        ToolUseBlock(
                            id="call_1",
                            name="write_file",
                            input={"path": "novel.md", "content": "# 第一批\n"},
                        )
                    ]
                )
            )
        elif self.stream_calls == 2:
            yield FinalResponseEvent(LLMResponse([TextBlock("已创建 novel.md，后续可以继续追加。")]))
        elif self.stream_calls == 3:
            yield FinalResponseEvent(
                LLMResponse(
                    [
                        ToolUseBlock(
                            id="call_2",
                            name="edit_file",
                            input={
                                "path": "novel.md",
                                "old": "# 第一批\n",
                                "new": "# 第一批\n\n第二批正文。\n",
                            },
                        )
                    ]
                )
            )
        elif self.stream_calls == 4:
            yield FinalResponseEvent(LLMResponse([TextBlock("已追加第二批。后续可以继续追加。")]))
        elif self.stream_calls == 5:
            yield FinalResponseEvent(
                LLMResponse([ToolUseBlock(id="call_3", name="read_file", input={"path": "docs/architecture.md"})])
            )
        elif self.stream_calls == 6:
            yield FinalResponseEvent(LLMResponse([TextBlock("architecture summary")]))
        elif self.stream_calls == 7:
            yield FinalResponseEvent(
                LLMResponse(
                    [
                        ToolUseBlock(
                            id="call_4",
                            name="edit_file",
                            input={
                                "path": "novel.md",
                                "old": "第二批正文。\n",
                                "new": "第二批正文。\n\n第三批正文。\n",
                            },
                        )
                    ]
                )
            )
        else:
            yield FinalResponseEvent(LLMResponse([TextBlock("已追加第三批。")]))

    def complete(self, **_kwargs):
        return LLMResponse([TextBlock("summary")])


class ClarifyClient:
    def stream_complete(self, **_kwargs):
        yield FinalResponseEvent(LLMResponse([TextBlock("请确认文件名和内容风格？")]))

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


def test_runtime_inherits_pending_coding_task_for_supplemental_reply(tmp_path: Path):
    client = ClarifyThenWriteClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 2
    runtime.permission_handler = lambda _name, _input, _reason: True

    first = runtime.run_user_turn("可以，并且保持为文件，要求至少5个女主角")
    second = runtime.run_user_turn("温馨、1+5、大学、长篇、目标50w字、先写5w字")

    assert first == "请确认风格、设定、长度和文件名？"
    assert second == "已创建 novel.md，后续可以继续追加。"
    assert runtime.working_state.waiting_for_user is True
    assert client.tool_names_by_call[0] == []
    assert "write_file" in client.tool_names_by_call[1]
    assert (tmp_path / "novel.md").exists()


def test_runtime_keeps_pending_task_after_clarification_without_tools(tmp_path: Path):
    client = ReadOnlyThenClarifyThenWriteClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 3
    runtime.permission_handler = lambda _name, _input, _reason: True

    first = runtime.run_user_turn("保存为文件，要求至少2个角色，先问我风格和文件名")
    second = runtime.run_user_turn("温馨，文件名 novel.md，先写一小段")

    assert first == "请确认风格、设定、长度和文件名？"
    assert second == "已创建 novel.md，后续可以继续追加。"
    assert client.tool_names_by_call[0] == []
    assert "write_file" in client.tool_names_by_call[2]
    assert (tmp_path / "novel.md").exists()


def test_runtime_allows_continue_after_completed_file_chunk(tmp_path: Path):
    client = ContinueAfterWriteClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 2
    runtime.permission_handler = lambda _name, _input, _reason: True

    first = runtime.run_user_turn("保存为文件，文件名 novel.md，先写一小段")
    second = runtime.run_user_turn("继续，追加一小段")

    assert first == "已创建 novel.md，后续可以继续追加。"
    assert second == "已追加第二批。"
    assert "write_file" in client.tool_names_by_call[0]
    assert "edit_file" in client.tool_names_by_call[2]
    assert "第二批正文" in (tmp_path / "novel.md").read_text(encoding="utf-8")


def test_runtime_document_output_followup_uses_conversation_not_project_reads(tmp_path: Path):
    client = DocumentOutputFollowupClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.permission_handler = lambda _name, _input, _reason: True
    runtime.focus.kind = FocusKind.CONTENT
    runtime.focus.topic = "小说"
    runtime.state.messages.append(
        {
            "role": "assistant",
            "content": [{"type": "text", "text": "# 心动频率\n\n小说大纲"}],
        }
    )

    runtime.run_user_turn("直接输出为文档")

    assert "write_file" in client.tool_names_by_call[0]
    assert "list_files" not in client.tool_names_by_call[0]
    assert "read_file" not in client.tool_names_by_call[0]
    assert "search_text" not in client.tool_names_by_call[0]


def test_runtime_save_followup_uses_focus_without_project_reads(tmp_path: Path):
    client = DocumentOutputFollowupClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.permission_handler = lambda _name, _input, _reason: True
    runtime.focus.kind = FocusKind.CONTENT
    runtime.focus.topic = "小说"

    runtime.run_user_turn("保存一下")

    assert "write_file" in client.tool_names_by_call[0]
    assert "list_files" not in client.tool_names_by_call[0]
    assert "read_file" not in client.tool_names_by_call[0]
    assert "search_text" not in client.tool_names_by_call[0]


def test_runtime_long_conversation_can_switch_project_then_return_to_file_task(tmp_path: Path):
    client = LongConversationFocusClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 2
    runtime.permission_handler = lambda _name, _input, _reason: True
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text("# Architecture\n", encoding="utf-8")

    first = runtime.run_user_turn("写一个校园小说开头，保存到 novel.md")
    second = runtime.run_user_turn("继续")
    project = runtime.run_user_turn("解释当前项目架构")
    third = runtime.run_user_turn("继续写 novel.md 的下一段")

    assert first == "已创建 novel.md，后续可以继续追加。"
    assert second == "已追加第二批。后续可以继续追加。"
    assert project == "architecture summary"
    assert third == "已追加第三批。"
    assert "write_file" in client.tool_names_by_call[0]
    assert "edit_file" in client.tool_names_by_call[2]
    assert client.tool_names_by_call[4] == ["read_file"]
    assert "edit_file" in client.tool_names_by_call[6]
    assert "第三批正文" in (tmp_path / "novel.md").read_text(encoding="utf-8")


def test_runtime_clears_pending_task_when_user_cancels(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, ClarifyClient())

    runtime.run_user_turn("保存为文件，要求至少5个女主角")
    result = runtime.run_user_turn("算了")
    decision = runtime.working_state.resolve_intent("继续", runtime.focus)

    assert result == "请确认文件名和内容风格？"
    assert decision.intent == classify_intent("继续").intent
    assert runtime.working_state.waiting_for_user is False
    assert runtime.focus.kind == FocusKind.NONE


def test_runtime_does_not_run_tools_after_final_verification_summary(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, FinalSummaryWithExtraToolClient())
    runtime.config.max_turns = 2

    result = runtime.run_user_turn("执行压力测试并报告结果")

    assert "压力测试结果：通过" in result
    assert not (tmp_path / "x.txt").exists()
    assert not any(event.type == "tool_start" for event in runtime.state.events)


def test_runtime_does_not_run_tools_after_streamed_final_verification_summary(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, StreamedFinalSummaryWithExtraToolClient())
    runtime.config.max_turns = 2

    result = runtime.run_user_turn("执行压力测试并报告结果")

    assert "压力测试结果：通过" in result
    assert not (tmp_path / "x.txt").exists()
    assert not any(event.type == "tool_start" for event in runtime.state.events)


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

    assert tool_names == {"read_file"}


def test_runtime_guides_hidden_tool_execution_for_project_question(tmp_path: Path):
    client = HiddenProjectListFilesClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 2

    result = runtime.run_user_turn("这个项目结构是什么？")

    assert result == "done"
    assert client.tool_names_by_call == [["read_file"], ["read_file"]]
    tool_errors = [event for event in runtime.state.events if event.type == "tool_error"]
    assert tool_errors[0].payload["name"] == "list_files"
    assert tool_errors[0].payload["category"] == "unavailable_tool"
    tool_result = runtime.state.messages[-2]["content"][0]
    assert tool_result["is_error"] is False
    assert "not available for this request" in tool_result["content"]
    assert "read_file" in tool_result["content"]


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

    assert "Current tasks (live task state):" in prompt
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


def test_runtime_stream_model_call_emits_text_deltas_incrementally(tmp_path: Path):
    runtime = make_silent_runtime_with_client(tmp_path, SplitStreamTextClient())

    response = runtime._stream_model_call(
        model="fake-model",
        max_tokens=10,
        system="system",
        messages=[],
        tools=[],
    )

    assert [event.payload["text"] for event in runtime.state.events if event.type == "text_delta"] == [
        "hello ",
        "stream",
    ]
    assert response.content[0].text == "hello stream"


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


def test_runtime_stream_model_call_prints_final_text_without_delta(tmp_path: Path, capsys):
    runtime = make_runtime_with_client(tmp_path, FinalTextWithoutDeltaClient())

    response = runtime._stream_model_call(
        model="fake-model",
        max_tokens=10,
        system="system",
        messages=[],
        tools=[],
    )

    captured = capsys.readouterr()
    assert captured.out == "final-only text"
    assert response.content[0].text == "final-only text"


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


def test_runtime_disables_tools_after_permission_denial(tmp_path: Path):
    client = PermissionDeniedThenAnswerClient()
    runtime = make_silent_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 2
    runtime.config.permission_mode = PermissionMode.DONT_ASK
    runtime.permission_context.mode = PermissionMode.DONT_ASK

    result = runtime.run_user_turn("新增 x.txt，内容是 x")

    assert result == "permission boundary explained"
    assert client.tool_names_by_call[0]
    assert client.tool_names_by_call[1] == []
    tool_results = runtime.state.messages[-2]["content"]
    assert tool_results[0]["is_error"] is True
    assert "Do not retry the same action with another tool" in tool_results[0]["content"]


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


def test_runtime_blocks_model_call_when_preflight_still_exceeds_budget(tmp_path: Path):
    client = PreflightBlockedClient()
    runtime = make_runtime_with_client(tmp_path, client)
    runtime.config.context_char_budget = 50
    runtime.state.messages = [
        {"role": "user", "content": f"old message {index} " + ("x" * 200)}
        for index in range(7)
    ]

    text = runtime.run_user_turn("继续")

    assert client.complete_calls == 1
    assert client.stream_calls == 0
    assert "上下文太长" in text
    assert any(event.type == "context_notice" for event in runtime.state.events)
    assert any(event.type == "turn_transition" and event.payload["reason"] == "context_blocked" for event in runtime.state.events)


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
    assert "Preserve user goals, decisions, file paths, commands, and unresolved work" in summary_prompt
    assert "Do not copy long tool outputs, casual chatter, or repeated details" in summary_prompt
    assert runtime.state.summary == "summary preserving old goal"
    assert runtime.state.messages == [
        {"role": "user", "content": "Recent user asks to keep README updated."},
        {"role": "assistant", "content": "Recent assistant confirms README update."},
        {"role": "user", "content": "Recent user asks to run tests."},
        {"role": "assistant", "content": "Recent assistant will run pytest."},
    ]


def test_runtime_compacts_realistic_long_task_without_losing_key_context(tmp_path: Path):
    client = RecordingCompactClient()
    runtime = make_runtime_with_client(tmp_path, client)
    runtime.config.context_char_budget = 600
    runtime.state.messages = [
        {"role": "user", "content": "User goal: refactor context handling without losing task intent."},
        {"role": "assistant", "content": "I will inspect context.py and runtime.py first."},
    ]
    for index, tool_name in enumerate(["read_file", "search_text", "run_shell", "read_file", "search_text", "run_shell", "read_file", "search_text"]):
        tool_use_id = f"call_{index}"
        runtime.state.messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": tool_name,
                        "input": {"path": "mini_agent/context.py", "command": ".venv/bin/python -m pytest"},
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
                        "content": f"{tool_name} output references mini_agent/runtime.py and pytest " + ("x" * 300),
                        "is_error": False,
                    }
                ],
            }
        )
    runtime.state.messages.extend(
        [
            {"role": "user", "content": "Recent decision: keep compaction lightweight."},
            {"role": "assistant", "content": "I will add focused tests only."},
            {"role": "user", "content": "Unresolved: verify summary injection still works."},
            {"role": "assistant", "content": "Next step is running the compact tests."},
        ]
    )

    runtime._compact_if_needed()

    summary_prompt = client.complete_kwargs[0]["messages"][0]["content"]
    assert "User goal: refactor context handling without losing task intent." in summary_prompt
    assert "mini_agent/context.py" in summary_prompt
    assert "mini_agent/runtime.py" in summary_prompt
    assert ".venv/bin/python -m pytest" in summary_prompt
    assert "old tool result cleared by micro-compact" in summary_prompt
    assert runtime.state.summary == "summary preserving old goal"
    assert runtime.state.messages == [
        {"role": "user", "content": "Recent decision: keep compaction lightweight."},
        {"role": "assistant", "content": "I will add focused tests only."},
        {"role": "user", "content": "Unresolved: verify summary injection still works."},
        {"role": "assistant", "content": "Next step is running the compact tests."},
    ]


def test_runtime_context_stress_keeps_pending_task_across_compaction(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.config.context_char_budget = 500
    runtime.working_state.mark_waiting(intent=classify_intent("保存为文件，先问我风格和文件名"), goal="write story")
    runtime.state.messages = [
        {"role": "user", "content": "User goal: write tmp/story.md after collecting style and filename."},
        {"role": "assistant", "content": "请确认风格和文件名？"},
    ]
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
                        "input": {"path": "docs/current-features.md"},
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
                        "content": f"large read result {index} " + ("x" * 300),
                        "is_error": False,
                    }
                ],
            }
        )
    runtime.state.messages.extend(
        [
            {"role": "user", "content": "Recent user supplied style: 温馨, filename: tmp/story.md."},
            {"role": "assistant", "content": "I will write the first chunk next."},
            {"role": "user", "content": "Recent user says: continue after first chunk."},
            {"role": "assistant", "content": "Continuation should keep the file task active."},
        ]
    )

    runtime._compact_if_needed()
    decision = runtime.working_state.resolve_intent("温馨，文件名 tmp/story.md，先写一小段")

    assert runtime.working_state.waiting_for_user is True
    assert decision.intent == Intent.CODING_TASK
    assert decision.allow_tools is True
    assert runtime.state.summary == "summary"
    assert len(runtime.state.messages) == 4


def test_runtime_context_stress_keeps_task_state_separate_after_full_compact(tmp_path: Path):
    client = RecordingCompactClient()
    runtime = make_runtime_with_client(tmp_path, client)
    runtime.config.context_char_budget = 500
    runtime.task_state.set_tasks(["Write first chunk", "Append second chunk"])
    runtime.task_state.update_task("t1", "done", "tmp/story.md created")
    runtime.task_state.update_task("t2", "in_progress", "waiting for continue")
    runtime.state.messages = [
        {"role": "user", "content": "User goal: write a long story to tmp/story.md in chunks."},
        {"role": "assistant", "content": "I will create a todo list and write in batches."},
    ]
    for index in range(7):
        tool_use_id = f"call_{index}"
        runtime.state.messages.append(
            {
                "role": "assistant",
                "content": [
                    {
                        "type": "tool_use",
                        "id": tool_use_id,
                        "name": "write_file" if index == 0 else "read_file",
                        "input": {"path": "tmp/story.md"},
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
                        "content": f"chunk evidence {index} " + ("x" * 350),
                        "is_error": False,
                    }
                ],
            }
        )
    runtime.state.messages.extend(
        [
            {"role": "user", "content": "Recent: keep writing after context compaction."},
            {"role": "assistant", "content": "I will preserve the task state separately."},
            {"role": "user", "content": "Recent: verify tmp/story.md remains the target."},
            {"role": "assistant", "content": "Next action is appending to tmp/story.md."},
        ]
    )

    runtime._compact_if_needed()
    prompt = runtime._system_prompt()

    assert runtime.state.summary == "summary preserving old goal"
    assert "Current tasks (live task state):" in prompt
    assert "Conversation summary so far (historical context, not the current task list):" in prompt
    assert "t1 [done] Write first chunk - tmp/story.md created" in prompt
    assert "t2 [in_progress] Append second chunk - waiting for continue" in prompt
    assert prompt.index("Conversation summary so far") < prompt.index("Current tasks (live task state):")


def test_runtime_injects_full_compact_summary_into_system_prompt(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.summary = "Preserve user goal and edited files."

    prompt = runtime._system_prompt()

    assert "Conversation summary so far (historical context, not the current task list):" in prompt
    assert "Preserve user goal and edited files." in prompt


def test_runtime_prompt_keeps_task_state_and_summary_separate(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.task_state.set_tasks(["Run tests", "Update docs"])
    runtime.task_state.update_task("t1", "in_progress", "pytest running")
    runtime.state.summary = "Historical decision: keep context compaction lightweight."

    prompt = runtime._system_prompt()

    task_index = prompt.index("Current tasks (live task state):")
    summary_index = prompt.index("Conversation summary so far (historical context, not the current task list):")
    assert summary_index < task_index
    assert "t1 [in_progress] Run tests - pytest running" in prompt
    assert "t2 [todo] Update docs" in prompt
    assert "Historical decision: keep context compaction lightweight." in prompt


def test_runtime_prompt_orders_dynamic_context_sections(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("解释当前项目架构")
    runtime.state.summary = "Historical decision: keep prompt context lightweight."
    runtime.task_state.set_tasks(["Verify prompt boundary"])

    prompt = runtime._system_prompt()

    assert prompt.index("Operating principles:") < prompt.index("Workspace root:")
    assert prompt.index("Workspace root:") < prompt.index("Current user intent: project_question")
    assert prompt.index("Current user intent: project_question") < prompt.index(
        "Conversation summary so far (historical context, not the current task list):"
    )
    assert prompt.index("Conversation summary so far") < prompt.index("Current tasks (live task state):")


def test_project_question_prompt_prefers_doc_entry_points(tmp_path: Path):
    runtime = make_runtime(tmp_path)
    runtime.state.current_intent = classify_intent("解释当前项目架构")

    prompt = runtime._system_prompt()

    assert "Use the smallest useful read path" in prompt
    assert "docs/architecture.md" in prompt
    assert "docs/current-features.md" in prompt
    assert "docs/roadmap.md" in prompt
    assert "next-step or roadmap questions use docs/roadmap.md" in prompt
    assert "broad project overview questions use README.md or docs/context-map.md" in prompt
    assert "Use list_files only when the target file is unclear" in prompt
    assert "Answer the user's specific question directly and concisely" in prompt
    assert "Do not restate whole documents" in prompt
    assert "unless the user explicitly asks for detail" in prompt
    assert "preserve that count and list exactly" in prompt
    assert "3-6 short bullets" in prompt
    assert "Do not use emoji, tables, directory trees" in prompt
    assert "Always provide a visible final answer" in prompt


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
    assert client.tool_names_by_call[0] == ["read_file"]
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


def test_runtime_allows_project_qa_acceptance_to_read_multiple_docs(tmp_path: Path):
    client = ProjectQAAcceptanceMultiReadClient()
    runtime = make_runtime_with_client(tmp_path, client)
    runtime.config.max_turns = 5
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "architecture.md").write_text("architecture", encoding="utf-8")
    (tmp_path / "docs" / "current-features.md").write_text("features", encoding="utf-8")
    (tmp_path / "docs" / "roadmap.md").write_text("roadmap", encoding="utf-8")
    (tmp_path / "docs" / "context-map.md").write_text("context", encoding="utf-8")

    result = runtime.run_user_turn("做一次项目问答压力测试：1. 问当前项目架构是什么 2. 问怎么启动 3. 问下一步")

    assert result == "项目问答验收总结"
    assert client.tool_names_by_call[0] == ["read_file"]
    assert client.tool_names_by_call[1] == ["read_file"]
    assert client.tool_names_by_call[2] == ["read_file"]
    assert client.tool_names_by_call[3] == ["read_file"]
    assert client.tool_names_by_call[4] == []
