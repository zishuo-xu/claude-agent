from __future__ import annotations

import html
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any

from .config import AgentConfig
from .context import count_message_chars, micro_compact_messages
from .intent import IntentDecision, classify_intent, intent_prompt
from .llm import FinalResponseEvent, LLMClient, TextBlock, ToolUseBlock
from .permissions import PermissionBehavior, PermissionContext, PermissionRule, decide_permission
from .tasks import TaskState
from .tool_core import Tool
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
    ):
        self.client = client
        self.config = config
        self.system_prompt = system_prompt
        self.tool_registry = tools if isinstance(tools, ToolRegistry) else ToolRegistry(tools)
        self.tools = self.tool_registry.all()
        self.task_state = task_state or TaskState()
        self.state = AgentState()
        self.permission_context = PermissionContext(mode=config.permission_mode, rules=permission_rules or [])

    def run_user_turn(self, user_input: str, intent_override: IntentDecision | None = None) -> str:
        self.state.current_intent = intent_override or classify_intent(user_input)
        self.state.messages.append({"role": "user", "content": user_input})
        for _ in range(self.config.max_turns):
            self.state.turn_count += 1
            self._compact_if_needed()
            response = self._call_model(self.config.model)
            response.content = self._normalize_pseudo_tool_call(response.content)
            self.state.messages.append(
                {
                    "role": "assistant",
                    "content": [self._block_to_dict(block) for block in response.content],
                }
            )
            if not self._has_text(response.content):
                self._print_text(response.content)

            tool_uses = [block for block in response.content if getattr(block, "type", None) == "tool_use"]
            if not tool_uses:
                print()
                return self._content_text(response.content)

            tool_results = self._execute_tool_uses(tool_uses)
            self.state.messages.append({"role": "user", "content": tool_results})
            self._disable_requested_tool_after_use(tool_uses)

        print(f"\nStopped after {self.config.max_turns} turns.")
        return ""

    def _call_model(self, model: str) -> Any:
        tools = self._available_tool_specs()
        try:
            return self._stream_model_call(
                model=model,
                max_tokens=4096,
                system=self._system_prompt(),
                messages=self.state.messages,
                tools=tools,
            )
        except Exception:
            if not self.config.fallback_model or self.config.fallback_model == model:
                raise
            print(f"\n[model] {model} failed; retrying with {self.config.fallback_model}\n")
            return self._stream_model_call(
                model=self.config.fallback_model,
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
            print(streamed_text, end="", flush=True)
        return final_response

    def _system_prompt(self) -> str:
        summary = f"\nConversation summary so far:\n{self.state.summary}\n" if self.state.summary else ""
        intent = f"\n{intent_prompt(self.state.current_intent)}\n" if self.state.current_intent else ""
        tasks = f"\n{self.task_state.prompt_summary()}\n"
        return f"{self.system_prompt}\nWorkspace root: {self.config.workspace}\n{intent}{tasks}{summary}"

    def _available_tool_specs(self) -> list[dict[str, Any]]:
        return self.tool_registry.api_specs_for_intent(self.state.current_intent)

    def _disable_requested_tool_after_use(self, tool_uses: list[Any]) -> None:
        decision = self.state.current_intent
        if not decision or not decision.requested_tool:
            return
        if not any(tool_use.name == decision.requested_tool for tool_use in tool_uses):
            return
        self.state.current_intent = IntentDecision(
            intent=decision.intent,
            reason=f"{decision.reason}; requested tool already ran",
            allow_tools=False,
        )

    def _normalize_pseudo_tool_call(self, content_blocks: list[Any]) -> list[Any]:
        if any(getattr(block, "type", None) == "tool_use" for block in content_blocks):
            return content_blocks

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
            return self._pseudo_tool_block_or_original(name, {"prompt": prompt}, content_blocks)

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
        return self._pseudo_tool_block_or_original(name, arguments, content_blocks)

    def _pseudo_tool_block_or_original(self, name: Any, tool_input: dict[str, Any], original: list[Any]) -> list[Any]:
        if not isinstance(name, str) or name not in self.tools:
            return original

        if "prompt" not in tool_input and "query" in tool_input:
            tool_input = {**tool_input, "prompt": tool_input["query"]}

        prompt = tool_input.get("prompt")
        if isinstance(prompt, str):
            tool_input = {**tool_input, "prompt": html.unescape(prompt).strip()}
            prompt = tool_input["prompt"]
        if not prompt:
            return original

        return [ToolUseBlock(id=f"pseudo_tool_{self.state.turn_count}", name=name, input={"prompt": prompt})]

    def _compact_if_needed(self) -> None:
        total_chars = count_message_chars(self.state.messages)
        if total_chars <= self.config.context_char_budget:
            return

        micro_result = micro_compact_messages(self.state.messages)
        if micro_result.changed:
            self.state.messages = micro_result.messages
            print(f"\n[context] micro-compacted {micro_result.compacted_count} old tool result(s)\n")
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
        print("\n[context] compacted older conversation into summary\n")

    def _execute_tool_uses(self, tool_uses: list[Any]) -> list[dict[str, Any]]:
        if self._can_run_in_parallel(tool_uses):
            with ThreadPoolExecutor(max_workers=min(4, len(tool_uses))) as executor:
                return list(executor.map(self._execute_one_tool_use, tool_uses))
        return [self._execute_one_tool_use(tool_use) for tool_use in tool_uses]

    def _can_run_in_parallel(self, tool_uses: list[Any]) -> bool:
        if len(tool_uses) < 2:
            return False
        for tool_use in tool_uses:
            tool = self.tools.get(tool_use.name)
            if not tool or not tool.read_only(tool_use.input) or not tool.concurrency_safe(tool_use.input):
                return False
        return True

    def _execute_one_tool_use(self, tool_use: Any) -> dict[str, Any]:
        name = tool_use.name
        tool_input = tool_use.input
        tool = self.tools.get(name)
        if not tool:
            return self._tool_result(tool_use.id, f"Unknown tool: {name}", True)

        print(f"\n\n[tool] {name} {tool_input}")
        validation_error = tool.validate_input(tool_input)
        if validation_error:
            result = f"Invalid tool input: {validation_error}"
            print(result)
            return self._tool_result(tool_use.id, result, True)

        decision = decide_permission(
            context=self.permission_context,
            tool_name=name,
            tool_input=tool_input,
            read_only=tool.read_only(tool_input),
            destructive=tool.destructive(tool_input),
        )
        if decision.behavior == PermissionBehavior.DENY:
            result = f"Permission denied: {decision.reason}"
            print(result)
            return self._tool_result(tool_use.id, result, True)
        if decision.behavior == PermissionBehavior.ASK and not self._confirm_tool(name, tool_input, decision.reason):
            result = "Permission rejected by user"
            print(result)
            return self._tool_result(tool_use.id, result, True)

        try:
            result = tool.run(tool_input)
            print(result)
            return self._tool_result(tool_use.id, result, False)
        except Exception as exc:
            result = f"{type(exc).__name__}: {exc}"
            print(result)
            return self._tool_result(tool_use.id, result, True)

    def _confirm_tool(self, name: str, tool_input: dict[str, Any], reason: str) -> bool:
        print(f"[permission] {reason}")
        answer = input(f"Allow {name} {tool_input}? [y/N] ").strip().lower()
        return answer in {"y", "yes"}

    @staticmethod
    def _tool_result(tool_use_id: str, content: str, is_error: bool) -> dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": tool_use_id,
            "content": content,
            "is_error": is_error,
        }

    @staticmethod
    def _block_to_dict(block: Any) -> dict[str, Any]:
        if hasattr(block, "to_dict"):
            return block.to_dict()
        if isinstance(block, dict):
            return block
        raise TypeError(f"unsupported content block: {block!r}")

    @staticmethod
    def _print_text(content_blocks: list[Any]) -> None:
        for block in content_blocks:
            if getattr(block, "type", None) == "text":
                print(block.text, end="")

    @staticmethod
    def _has_text(content_blocks: list[Any]) -> bool:
        return any(getattr(block, "type", None) == "text" for block in content_blocks)

    @staticmethod
    def _content_text(content_blocks: list[Any]) -> str:
        return "\n".join(block.text for block in content_blocks if getattr(block, "type", None) == "text")

    @staticmethod
    def _contains_pseudo_tool_call(text: str) -> bool:
        return "<tool_call" in text or "<invoke" in text
