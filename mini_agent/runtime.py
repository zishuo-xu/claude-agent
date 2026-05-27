from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import AgentConfig
from .context_preflight import build_full_compact_summary_prompt, run_context_preflight
from .events import (
    EventHandler,
    PermissionRequestHandler,
    RuntimeEvent,
    print_runtime_event,
    prompt_permission_request,
)
from .focus import ConversationFocus
from .intent import Intent, IntentDecision, intent_prompt
from .llm import FinalResponseEvent, LLMClient, TextBlock
from .permissions import PermissionContext, PermissionRule
from .pseudo_tools import contains_pseudo_tool_call, normalize_pseudo_tool_call
from .tasks import TaskState
from .tool_core import Tool
from .tool_executor import ToolTurnExecutor
from .tool_registry import ToolRegistry
from .working_state import CANCELLED_INTENT_REASON, WorkingState, should_keep_pending_task


SYSTEM_PROMPT = """You are a Claude Code inspired learning agent.

Operating principles:
- Work in a tight observe-think-act loop.
- Follow the current user intent guidance when it is provided.
- When the user provides numbered steps, a checklist, or a named test case, treat it as the execution contract:
  complete those items directly and do not replace them with a different interpretation of the task.
- Inspect before editing.
- Prefer the smallest tool call that advances the task.
- Explain meaningful actions briefly before using tools.
- When a tool is needed, use the actual tool call interface. Do not print XML, JSON, or markdown pseudo tool calls as plain text.
- Only explain architecture, tools, permissions, or implementation details when the user asks for them or when they are necessary to complete the task.
- Keep file operations inside the workspace.
- Prefer the project virtualenv command `.venv/bin/python` for Python tests or project scripts when it exists.
- Do not install packages into system Python or use `--break-system-packages`; ask before adding dependencies.
- For multi-step coding tasks, create a short 3-6 item todo list with task tools before substantial work, then update it as phases start or finish.
- Do not use task tools for casual chat, general learning questions, or simple one-step requests.
- If a command or edit is risky, ask for confirmation through the permission system.
- When you finish, summarize what changed and how it was verified.
- After giving a final result or pass/fail verification summary, stop and wait for the next user message.
  Do not combine that final summary with more tool calls.
"""


@dataclass
class AgentState:
    messages: list[dict[str, Any]] = field(default_factory=list)
    events: list[RuntimeEvent] = field(default_factory=list)
    turn_count: int = 0
    current_turn_tool_rounds: int = 0
    current_turn_mutating_tools: bool = False
    summary: str | None = None
    current_intent: IntentDecision | None = None


class AgentRuntime:
    def __init__(
        self,
        *,
        client: LLMClient,
        config: AgentConfig,
        tools: dict[str, Tool] | ToolRegistry,
        task_state: TaskState | None = None,
        permission_rules: list[PermissionRule] | None = None,
        system_prompt: str = SYSTEM_PROMPT,
        event_handler: EventHandler | None = print_runtime_event,
        permission_handler: PermissionRequestHandler = prompt_permission_request,
    ):
        self.client = client
        self.config = config
        self.system_prompt = system_prompt
        self.tool_registry = tools if isinstance(tools, ToolRegistry) else ToolRegistry(tools)
        self.tools = self.tool_registry.all()
        self.task_state = task_state or TaskState()
        self.state = AgentState()
        self.focus = ConversationFocus()
        self.working_state = WorkingState()
        self.permission_context = PermissionContext(mode=config.permission_mode, rules=permission_rules or [])
        self.event_handler = event_handler
        self.permission_handler = permission_handler

    def run_user_turn(self, user_input: str, intent_override: IntentDecision | None = None) -> str:
        self.state.current_intent = intent_override or self.working_state.resolve_intent(user_input, self.focus)
        self.state.current_turn_tool_rounds = 0
        self.state.current_turn_mutating_tools = False
        self.state.messages.append({"role": "user", "content": user_input})
        for _ in range(self.config.max_turns):
            self._begin_turn()
            response = self._call_model(self.config.model)
            response.content = self._normalize_pseudo_tool_call(response.content)
            if self._should_treat_as_final_text(response.content):
                final_content = self._without_tool_uses(response.content)
                self._record_assistant_response(final_content)
                return self._handle_final_answer(final_content, user_input)
            self._record_assistant_response(response.content)

            tool_uses = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
            if not tool_uses:
                return self._handle_final_answer(response.content, user_input)

            self._handle_tool_turn(tool_uses)

        self._emit("turn_limit_reached", max_turns=self.config.max_turns)
        self._emit("stopped", max_turns=self.config.max_turns)
        return ""

    def _begin_turn(self) -> None:
        self.state.turn_count += 1
        self._emit(
            "turn_start",
            turn=self.state.turn_count,
            intent=self.state.current_intent.intent.value if self.state.current_intent else None,
        )
        self._compact_if_needed()

    def _record_assistant_response(self, content: list[Any]) -> None:
        self.state.messages.append(
            {
                "role": "assistant",
                "content": [self._block_to_dict(block) for block in content],
            }
        )
        self._emit(
            "assistant_message",
            turn=self.state.turn_count,
            has_text=self._has_text(content),
            tools=[block.name for block in content if getattr(block, "type", None) == "tool_use"],
        )

    def _handle_final_answer(self, content: list[Any], user_input: str) -> str:
        text = self._content_text(content).strip()
        if not text:
            text = self._empty_response_fallback(user_input)
            self._emit("text_delta", text=text)
        self._update_working_state_after_final_answer(text, user_input)
        self._emit("turn_transition", reason="final_answer", turn=self.state.turn_count)
        self._emit("final_answer", text=text)
        return text

    def _handle_tool_turn(self, tool_uses: list[Any]) -> None:
        if self._has_mutating_tool_use(tool_uses):
            self.state.current_turn_mutating_tools = True
            self.working_state.clear()
        self._emit(
            "turn_transition",
            reason="tool_use",
            turn=self.state.turn_count,
            tools=[tool_use.name for tool_use in tool_uses],
        )
        tool_results = self._execute_tool_uses(tool_uses)
        self.state.messages.append({"role": "user", "content": tool_results})
        self._disable_tools_after_permission_denial(tool_results)
        self._disable_tools_after_project_question_use(tool_uses)
        self._emit("turn_transition", reason="next_turn", turn=self.state.turn_count)

    def _update_working_state_after_final_answer(self, text: str, user_input: str) -> None:
        self.focus.update_after_final_answer(
            intent=self.state.current_intent,
            user_input=user_input,
            final_text=text,
        )
        if self.state.current_intent and self.state.current_intent.reason == CANCELLED_INTENT_REASON:
            self.working_state.clear()
            self.focus.clear()
            return
        if should_keep_pending_task(self.state.current_intent, text, self.state.current_turn_mutating_tools):
            self.working_state.mark_waiting(intent=self.state.current_intent, goal=user_input)
            return
        self.working_state.clear()

    def _has_mutating_tool_use(self, tool_uses: list[Any]) -> bool:
        for tool_use in tool_uses:
            tool = self.tools.get(tool_use.name)
            if not tool:
                continue
            if not tool.read_only(tool_use.input):
                return True
        return False

    def _should_treat_as_final_text(self, content: list[Any]) -> bool:
        has_tool_use = any(getattr(block, "type", None) == "tool_use" for block in content)
        if not has_tool_use:
            return False
        text = self._content_text(content)
        if not text:
            return False
        return self._looks_like_final_verification_text(text)

    def _looks_like_final_verification_text(self, text: str) -> bool:
        lowered = text.lower()
        return (
            ("压力测试结果" in text and ("通过" in text or "未通过" in text))
            or ("通过标准对照" in text and "是否需要修复" in text)
            or ("verification result" in lowered and ("passed" in lowered or "failed" in lowered))
            or ("result:" in lowered and ("passed" in lowered or "failed" in lowered))
        )

    def _without_tool_uses(self, content: list[Any]) -> list[Any]:
        return [block for block in content if getattr(block, "type", None) != "tool_use"]

    def _call_model(self, model: str) -> Any:
        tools = self._available_tool_specs()
        self._emit("model_start", model=model, visible_tools=len(tools))
        try:
            return self._call_model_once(model=model, tools=tools)
        except Exception as exc:
            self._emit("model_error", model=model, error_type=type(exc).__name__, message=str(exc))
            if not self.config.fallback_model or self.config.fallback_model == model:
                raise
            self._emit("model_fallback", from_model=model, to_model=self.config.fallback_model)
            try:
                return self._call_model_once(model=self.config.fallback_model, tools=tools)
            except Exception as fallback_exc:
                self._emit(
                    "model_error",
                    model=self.config.fallback_model,
                    error_type=type(fallback_exc).__name__,
                    message=str(fallback_exc),
                )
                raise

    def _call_model_once(self, *, model: str, tools: list[dict[str, Any]]) -> Any:
        return self._stream_model_call(
            model=model,
            max_tokens=4096,
            system=self._system_prompt(),
            messages=self.state.messages,
            tools=tools,
        )

    def _stream_model_call(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> Any:
        final_response = None
        streamed_text = ""
        emitted_stream_text = False
        suppress_stream_text = False
        for event in self.client.stream_complete(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools,
        ):
            if event.type == "text_delta":
                streamed_text += event.text
                if self._contains_pseudo_tool_call(streamed_text):
                    suppress_stream_text = True
                    continue
                if not suppress_stream_text:
                    self._emit("text_delta", text=event.text)
                    emitted_stream_text = True
            elif isinstance(event, FinalResponseEvent):
                final_response = event.response
        if final_response is None:
            raise RuntimeError("stream completed without final response")
        if (
            streamed_text
            and any(getattr(block, "type", None) == "tool_use" for block in final_response.content)
            and self._looks_like_final_verification_text(streamed_text)
        ):
            final_response.content = [TextBlock(streamed_text)]
        if streamed_text and not final_response.content:
            final_response.content = [TextBlock(streamed_text)]
        final_text = self._content_text(final_response.content)
        if final_text and not emitted_stream_text and not self._contains_pseudo_tool_call(final_text):
            self._emit("text_delta", text=final_text)
        return final_response

    def _system_prompt(self) -> str:
        sections = [
            self.system_prompt,
            f"Workspace root: {self.config.workspace}",
        ]
        if self.state.current_intent:
            sections.append(intent_prompt(self.state.current_intent))
        if self.state.summary:
            sections.append(
                "Conversation summary so far (historical context, not the current task list):\n"
                f"{self.state.summary}"
            )
        sections.append(self.task_state.prompt_summary())
        return "\n\n".join(sections)

    def _available_tool_specs(self) -> list[dict[str, Any]]:
        return self.tool_registry.api_specs_for_intent(self.state.current_intent)

    def _available_tools(self) -> dict[str, Tool]:
        return self.tool_registry.available_for_intent(self.state.current_intent)

    def _disable_tools_after_project_question_use(self, tool_uses: list[Any]) -> None:
        decision = self.state.current_intent
        if not decision or decision.intent != Intent.PROJECT_QUESTION:
            return
        if decision.requested_tool and not any(tool_use.name == decision.requested_tool for tool_use in tool_uses):
            return
        self.state.current_turn_tool_rounds += 1
        used_names = {tool_use.name for tool_use in tool_uses}
        if not decision.requested_tool and used_names <= {"list_files"} and self.state.current_turn_tool_rounds < 2:
            return
        if (
            decision.reason == "project Q&A acceptance request"
            and used_names <= {"read_file"}
            and self.state.current_turn_tool_rounds < 4
        ):
            return
        self.state.current_intent = IntentDecision(
            intent=decision.intent,
            reason=f"{decision.reason}; project question tools already ran",
            allow_tools=False,
        )

    def _disable_tools_after_permission_denial(self, tool_results: list[dict[str, Any]]) -> None:
        if not self.state.current_intent:
            return
        denied = any(
            result.get("is_error") is True
            and str(result.get("content", "")).startswith(("Permission denied:", "Permission rejected by user"))
            for result in tool_results
        )
        if not denied:
            return
        decision = self.state.current_intent
        self.state.current_intent = IntentDecision(
            intent=decision.intent,
            reason=f"{decision.reason}; permission denied, tools disabled for this turn",
            allow_tools=False,
        )

    def _empty_response_fallback(self, user_input: str) -> str:
        decision = self.state.current_intent
        if decision and decision.intent == Intent.CASUAL_CHAT:
            return "你好，我在。"
        if decision and decision.intent == Intent.GENERAL_LEARNING:
            return "我可以给你一个简洁的学习建议，也可以根据你的基础继续细化。"
        return f"我没有生成可见回复。你刚才的问题是：{user_input}"

    def _normalize_pseudo_tool_call(self, content_blocks: list[Any]) -> list[Any]:
        return normalize_pseudo_tool_call(
            content_blocks,
            available_tool_names=set(self._available_tools()),
            tool_use_id=f"pseudo_tool_{self.state.turn_count}",
        )

    def _compact_if_needed(self) -> None:
        result = run_context_preflight(
            self.state.messages,
            char_budget=self.config.context_char_budget,
            summarize=self._summarize_old_messages,
        )
        self.state.messages = result.messages
        if result.summary is not None:
            self.state.summary = result.summary
        for notice in result.notices:
            self._emit("context_notice", message=notice)

    def _summarize_old_messages(self, old_messages: list[dict[str, Any]]) -> str:
        response = self.client.complete(
            model=self.config.model,
            max_tokens=1024,
            system="You summarize agent transcripts accurately and concisely.",
            messages=[{"role": "user", "content": build_full_compact_summary_prompt(old_messages)}],
        )
        return "\n".join(block.text for block in response.content if getattr(block, "type", None) == "text")

    def _execute_tool_uses(self, tool_uses: list[Any]) -> list[dict[str, Any]]:
        available_tools = self._available_tools()
        executor = ToolTurnExecutor(
            tools=available_tools,
            permission_context=self.permission_context,
            emit=self._emit,
            permission_handler=self.permission_handler,
        )
        if all(tool_use.name not in self.tools or tool_use.name in available_tools for tool_use in tool_uses):
            return executor.execute(tool_uses)

        results: list[dict[str, Any]] = []
        for tool_use in tool_uses:
            if tool_use.name in self.tools and tool_use.name not in available_tools:
                results.append(self._unavailable_tool_result(tool_use))
                continue
            results.extend(executor.execute([tool_use]))
        return results

    def _unavailable_tool_result(self, tool_use: Any) -> dict[str, Any]:
        visible = ", ".join(self._available_tools()) or "no tools"
        content = (
            f"Tool {tool_use.name} is not available for this request. "
            f"Use the currently visible tools ({visible}) or answer from available context."
        )
        self._emit("tool_error", name=tool_use.name, category="unavailable_tool", error_type=None, content=content)
        return {
            "type": "tool_result",
            "tool_use_id": tool_use.id,
            "content": content,
            "is_error": False,
        }

    @staticmethod
    def _block_to_dict(block: Any) -> dict[str, Any]:
        if hasattr(block, "to_dict"):
            return block.to_dict()
        if isinstance(block, dict):
            return block
        raise TypeError(f"unsupported content block: {block!r}")

    def _emit(self, event_type: str, **payload: Any) -> None:
        event = RuntimeEvent(event_type, payload)
        self.state.events.append(event)
        if self.event_handler:
            self.event_handler(event)

    @staticmethod
    def _has_text(content_blocks: list[Any]) -> bool:
        return any(getattr(block, "type", None) == "text" for block in content_blocks)

    @staticmethod
    def _content_text(content_blocks: list[Any]) -> str:
        return "\n".join(block.text for block in content_blocks if getattr(block, "type", None) == "text")

    @staticmethod
    def _contains_pseudo_tool_call(text: str) -> bool:
        return contains_pseudo_tool_call(text)
