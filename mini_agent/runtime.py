from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .config import AgentConfig
from .context import count_message_chars, micro_compact_messages
from .events import (
    EventHandler,
    PermissionRequestHandler,
    RuntimeEvent,
    print_runtime_event,
    prompt_permission_request,
)
from .intent import Intent, IntentDecision, intent_prompt
from .llm import FinalResponseEvent, LLMClient, TextBlock
from .permissions import PermissionContext, PermissionRule
from .pseudo_tools import contains_pseudo_tool_call, normalize_pseudo_tool_call
from .tasks import TaskState
from .tool_core import Tool
from .tool_executor import ToolTurnExecutor
from .tool_registry import ToolRegistry
from .working_state import WorkingState, should_keep_pending_task


SYSTEM_PROMPT = """You are a Claude Code inspired learning agent.

Operating principles:
- Work in a tight observe-think-act loop.
- Follow the current user intent guidance when it is provided.
- Inspect before editing.
- Prefer the smallest tool call that advances the task.
- Explain meaningful actions briefly before using tools.
- When a tool is needed, use the actual tool call interface. Do not print XML, JSON, or markdown pseudo tool calls as plain text.
- Only explain architecture, tools, permissions, or implementation details when the user asks for them or when they are necessary to complete the task.
- Keep file operations inside the workspace.
- Prefer python3 over python when running Python scripts unless the user specifically requests python.
- For multi-step coding tasks, create a short 3-6 item todo list with task tools before substantial work, then update it as phases start or finish.
- Do not use task tools for casual chat, general learning questions, or simple one-step requests.
- If a command or edit is risky, ask for confirmation through the permission system.
- When you finish, summarize what changed and how it was verified.
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
        self.working_state = WorkingState()
        self.permission_context = PermissionContext(mode=config.permission_mode, rules=permission_rules or [])
        self.event_handler = event_handler
        self.permission_handler = permission_handler

    def run_user_turn(self, user_input: str, intent_override: IntentDecision | None = None) -> str:
        self.state.current_intent = intent_override or self.working_state.resolve_intent(user_input)
        self.state.current_turn_tool_rounds = 0
        self.state.current_turn_mutating_tools = False
        self.state.messages.append({"role": "user", "content": user_input})
        for _ in range(self.config.max_turns):
            self._begin_turn()
            response = self._call_model(self.config.model)
            response.content = self._normalize_pseudo_tool_call(response.content)
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
        for event in self.client.stream_complete(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools,
        ):
            if event.type == "text_delta":
                streamed_text += event.text
            elif isinstance(event, FinalResponseEvent):
                final_response = event.response
        if final_response is None:
            raise RuntimeError("stream completed without final response")
        if streamed_text and not final_response.content:
            final_response.content = [TextBlock(streamed_text)]
        final_text = self._content_text(final_response.content)
        if streamed_text and not self._contains_pseudo_tool_call(final_text):
            self._emit("text_delta", text=streamed_text)
        elif final_text and not self._contains_pseudo_tool_call(final_text):
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
        total_chars = count_message_chars(self.state.messages)
        if total_chars <= self.config.context_char_budget:
            return

        micro_result = micro_compact_messages(self.state.messages)
        if micro_result.changed:
            self.state.messages = micro_result.messages
            self._emit("context_notice", message=f"micro-compacted {micro_result.compacted_count} old tool result(s)")
            total_chars = count_message_chars(self.state.messages)
            if total_chars <= self.config.context_char_budget:
                return

        if len(self.state.messages) < 8:
            return

        old_messages = self.state.messages[:-4]
        recent_messages = self.state.messages[-4:]
        summary_prompt = (
            "Summarize this conversation for continuing a coding task. "
            "Preserve user goals, decisions, file paths, commands, and unresolved work. "
            "Do not copy long tool outputs, casual chatter, or repeated details.\n\n"
            f"{old_messages}"
        )
        response = self.client.complete(
            model=self.config.model,
            max_tokens=1024,
            system="You summarize agent transcripts accurately and concisely.",
            messages=[{"role": "user", "content": summary_prompt}],
        )
        self.state.summary = "\n".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        )
        self.state.messages = recent_messages
        self._emit("context_notice", message="compacted older conversation into summary")

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
