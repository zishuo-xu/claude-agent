from __future__ import annotations

import html
import json
import re
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
from .intent import Intent, IntentDecision, classify_intent, intent_prompt
from .llm import FinalResponseEvent, LLMClient, TextBlock, ToolUseBlock
from .permissions import PermissionContext, PermissionRule
from .tasks import TaskState
from .tool_core import Tool
from .tool_executor import ToolTurnExecutor
from .tool_registry import ToolRegistry


SYSTEM_PROMPT = """You are a Claude Code inspired learning agent.

Operating principles:
- Work in a tight observe-think-act loop.
- Inspect before editing.
- Prefer the smallest tool call that advances the task.
- Explain meaningful actions briefly before using tools.
- When a tool is needed, use the actual tool call interface. Do not print XML, JSON, or markdown pseudo tool calls as plain text.
- If the user explicitly asks you to use explore_agent, plan_agent, or verify_agent, call that tool when it is available.
- Match the user's intent and scope. For greetings or casual chat, reply briefly and do not describe the project architecture unless asked.
- For general learning requests like "I want to learn Python", do not inspect the workspace or describe this project unless the user explicitly asks to use the project as learning material. Give a concise learning path or ask about their current level.
- Only explain architecture, tools, permissions, or implementation details when the user asks for them or when they are necessary to complete the task.
- Keep file operations inside the workspace.
- For multi-step coding tasks, create or update a short todo list with task tools before doing substantial work.
- If a command or edit is risky, ask for confirmation through the permission system.
- When you finish, summarize what changed and how it was verified.
"""


@dataclass
class AgentState:
    messages: list[dict[str, Any]] = field(default_factory=list)
    events: list[RuntimeEvent] = field(default_factory=list)
    turn_count: int = 0
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
        self.permission_context = PermissionContext(mode=config.permission_mode, rules=permission_rules or [])
        self.event_handler = event_handler
        self.permission_handler = permission_handler

    def run_user_turn(self, user_input: str, intent_override: IntentDecision | None = None) -> str:
        self.state.current_intent = intent_override or classify_intent(user_input)
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
        self._emit("turn_transition", reason="final_answer", turn=self.state.turn_count)
        self._emit("final_answer", text=text)
        return text

    def _handle_tool_turn(self, tool_uses: list[Any]) -> None:
        self._emit(
            "turn_transition",
            reason="tool_use",
            turn=self.state.turn_count,
            tools=[tool_use.name for tool_use in tool_uses],
        )
        tool_results = self._execute_tool_uses(tool_uses)
        self.state.messages.append({"role": "user", "content": tool_results})
        self._disable_tools_after_project_question_use(tool_uses)
        self._emit("turn_transition", reason="next_turn", turn=self.state.turn_count)

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
        if streamed_text and not self._contains_pseudo_tool_call(self._content_text(final_response.content)):
            self._emit("text_delta", text=streamed_text)
        return final_response

    def _system_prompt(self) -> str:
        summary = f"\nConversation summary so far:\n{self.state.summary}\n" if self.state.summary else ""
        intent = f"\n{intent_prompt(self.state.current_intent)}\n" if self.state.current_intent else ""
        tasks = f"\n{self.task_state.prompt_summary()}\n"
        return f"{self.system_prompt}\nWorkspace root: {self.config.workspace}\n{intent}{tasks}{summary}"

    def _available_tool_specs(self) -> list[dict[str, Any]]:
        return self.tool_registry.api_specs_for_intent(self.state.current_intent)

    def _disable_tools_after_project_question_use(self, tool_uses: list[Any]) -> None:
        decision = self.state.current_intent
        if not decision or decision.intent != Intent.PROJECT_QUESTION:
            return
        if decision.requested_tool and not any(tool_use.name == decision.requested_tool for tool_use in tool_uses):
            return
        self.state.current_intent = IntentDecision(
            intent=decision.intent,
            reason=f"{decision.reason}; project question tools already ran",
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
        if any(getattr(block, "type", None) == "tool_use" for block in content_blocks):
            return content_blocks

        preserved_blocks = [block for block in content_blocks if getattr(block, "type", None) == "reasoning"]
        text = self._content_text(content_blocks).strip()
        xml_match = re.search(
            r"<invoke\s+name=[\"'](?P<name>[^\"']+)[\"']>\s*"
            r"<(?P<tag>query|prompt)>(?P<prompt>.*?)</(?P=tag)>\s*"
            r"</invoke>",
            text,
            flags=re.DOTALL,
        )
        if xml_match:
            name = xml_match.group("name")
            prompt = html.unescape(xml_match.group("prompt")).strip()
            return self._pseudo_tool_blocks_or_original(name, {"prompt": prompt}, content_blocks, preserved_blocks)

        function_match = re.search(
            r"<function=(?P<name>[^>\s]+)>\s*(?P<body>.*?)</function>",
            text,
            flags=re.DOTALL,
        )
        if function_match:
            name = function_match.group("name")
            tool_input = self._parameters_from_pseudo_function(function_match.group("body"))
            return self._pseudo_tool_blocks_or_original(name, tool_input, content_blocks, preserved_blocks)

        json_match = re.search(r"<tool_call>\s*(?P<body>\{.*?\})\s*</tool_call>", text, flags=re.DOTALL)
        if not json_match:
            return content_blocks
        try:
            payload = json.loads(json_match.group("body"))
        except json.JSONDecodeError:
            return content_blocks

        name = payload.get("name")
        arguments = payload.get("arguments") or {}
        if not isinstance(arguments, dict):
            return content_blocks
        return self._pseudo_tool_blocks_or_original(name, arguments, content_blocks, preserved_blocks)

    def _pseudo_tool_blocks_or_original(
        self,
        name: Any,
        tool_input: dict[str, Any],
        original: list[Any],
        preserved_blocks: list[Any],
    ) -> list[Any]:
        if not isinstance(name, str) or name not in self.tools:
            return original

        if "prompt" not in tool_input and "query" in tool_input:
            tool_input = {**tool_input, "prompt": tool_input["query"]}
        if "path" not in tool_input and "file_path" in tool_input:
            tool_input = {**tool_input, "path": tool_input["file_path"]}

        prompt = tool_input.get("prompt")
        if isinstance(prompt, str):
            tool_input = {**tool_input, "prompt": html.unescape(prompt).strip()}
            prompt = tool_input["prompt"]
        if name in {"explore_agent", "plan_agent", "verify_agent"} and not prompt:
            return original

        if name in {"explore_agent", "plan_agent", "verify_agent"}:
            tool_input = {"prompt": prompt}

        return preserved_blocks + [ToolUseBlock(id=f"pseudo_tool_{self.state.turn_count}", name=name, input=tool_input)]

    @staticmethod
    def _parameters_from_pseudo_function(body: str) -> dict[str, Any]:
        params: dict[str, Any] = {}
        for match in re.finditer(r"<parameter=(?P<name>[^>\s]+)>(?P<value>.*?)</parameter>", body, flags=re.DOTALL):
            params[match.group("name")] = html.unescape(match.group("value")).strip()
        return params

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
            "Preserve user goals, decisions, file paths, commands, and unresolved work.\n\n"
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
        executor = ToolTurnExecutor(
            tools=self.tools,
            permission_context=self.permission_context,
            emit=self._emit,
            permission_handler=self.permission_handler,
        )
        return executor.execute(tool_uses)

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
        return "<tool_call" in text or "<invoke" in text
