from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from .context import count_message_chars, micro_compact_messages


DEFAULT_FULL_COMPACT_KEEP_RECENT_MESSAGES = 4


@dataclass
class ContextPreflightResult:
    messages: list[dict[str, Any]]
    summary: str | None = None
    input_chars: int = 0
    output_chars: int = 0
    micro_compacted_count: int = 0
    full_compacted: bool = False
    blocked_reason: str | None = None
    notices: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return self.micro_compacted_count > 0 or self.full_compacted

    @property
    def blocked(self) -> bool:
        return self.blocked_reason is not None


SummaryFn = Callable[[list[dict[str, Any]]], str]


def run_context_preflight(
    messages: list[dict[str, Any]],
    *,
    char_budget: int,
    summarize: SummaryFn | None = None,
    keep_recent_messages: int = DEFAULT_FULL_COMPACT_KEEP_RECENT_MESSAGES,
) -> ContextPreflightResult:
    input_chars = count_message_chars(messages)
    if input_chars <= char_budget:
        return ContextPreflightResult(messages=messages, input_chars=input_chars, output_chars=input_chars)

    current_messages = messages
    notices: list[str] = []
    micro_compacted_count = 0

    micro_result = micro_compact_messages(current_messages)
    if micro_result.changed:
        current_messages = micro_result.messages
        micro_compacted_count = micro_result.compacted_count
        notices.append(f"micro-compacted {micro_result.compacted_count} old tool result(s)")
        current_chars = count_message_chars(current_messages)
        if current_chars <= char_budget:
            return ContextPreflightResult(
                messages=current_messages,
                input_chars=input_chars,
                output_chars=current_chars,
                micro_compacted_count=micro_compacted_count,
                notices=notices,
            )

    if summarize is None or len(current_messages) < keep_recent_messages * 2:
        current_chars = count_message_chars(current_messages)
        return ContextPreflightResult(
            messages=current_messages,
            input_chars=input_chars,
            output_chars=current_chars,
            micro_compacted_count=micro_compacted_count,
            blocked_reason=_blocked_reason(current_chars, char_budget) if current_chars > char_budget else None,
            notices=notices,
        )

    old_messages = current_messages[:-keep_recent_messages]
    recent_messages = current_messages[-keep_recent_messages:]
    summary = summarize(old_messages)
    notices.append("compacted older conversation into summary")

    output_chars = count_message_chars(recent_messages)
    return ContextPreflightResult(
        messages=recent_messages,
        summary=summary,
        input_chars=input_chars,
        output_chars=output_chars,
        micro_compacted_count=micro_compacted_count,
        full_compacted=True,
        blocked_reason=_blocked_reason(output_chars, char_budget) if output_chars > char_budget else None,
        notices=notices,
    )


def _blocked_reason(output_chars: int, char_budget: int) -> str:
    return (
        "Context preflight stopped before the model call: "
        f"compacted context is still {output_chars} chars, over the {char_budget} char budget."
    )


def build_full_compact_summary_prompt(old_messages: list[dict[str, Any]]) -> str:
    return (
        "Summarize this conversation for continuing a coding task. "
        "Preserve user goals, decisions, file paths, commands, and unresolved work. "
        "Do not copy long tool outputs, casual chatter, or repeated details.\n\n"
        f"{old_messages}"
    )
