from __future__ import annotations

from dataclasses import dataclass
from typing import Any


MICRO_COMPACT_PLACEHOLDER = "[old tool result cleared by micro-compact"

COMPACTABLE_TOOL_NAMES = {
    "list_files",
    "read_file",
    "write_file",
    "edit_file",
    "preview_edit",
    "apply_edit",
    "search_text",
    "run_shell",
}


@dataclass
class MicroCompactResult:
    messages: list[dict[str, Any]]
    compacted_count: int

    @property
    def changed(self) -> bool:
        return self.compacted_count > 0


@dataclass
class _ToolResultRef:
    message_index: int
    block_index: int
    tool_use_id: str
    tool_name: str | None


def count_message_chars(messages: list[dict[str, Any]]) -> int:
    return sum(len(str(message.get("content", ""))) for message in messages)


def micro_compact_messages(
    messages: list[dict[str, Any]],
    *,
    keep_recent_tool_results: int = 6,
    compactable_tool_names: set[str] | None = None,
) -> MicroCompactResult:
    tool_names = compactable_tool_names or COMPACTABLE_TOOL_NAMES
    tool_use_names = _collect_tool_use_names(messages)
    compactable_refs = _collect_compactable_tool_results(messages, tool_use_names, tool_names)
    if len(compactable_refs) <= keep_recent_tool_results:
        return MicroCompactResult(messages=messages, compacted_count=0)

    refs_to_clear = compactable_refs[: len(compactable_refs) - keep_recent_tool_results]
    updated = _copy_messages_for_compaction(messages)
    compacted_count = 0

    for ref in refs_to_clear:
        block = updated[ref.message_index]["content"][ref.block_index]
        if not isinstance(block, dict):
            continue
        content = block.get("content")
        if isinstance(content, str) and content.startswith(MICRO_COMPACT_PLACEHOLDER):
            continue
        block["content"] = _placeholder(ref)
        compacted_count += 1

    return MicroCompactResult(messages=updated, compacted_count=compacted_count)


def _collect_tool_use_names(messages: list[dict[str, Any]]) -> dict[str, str]:
    names: dict[str, str] = {}
    for message in messages:
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            tool_use_id = block.get("id")
            name = block.get("name")
            if isinstance(tool_use_id, str) and isinstance(name, str):
                names[tool_use_id] = name
    return names


def _collect_compactable_tool_results(
    messages: list[dict[str, Any]],
    tool_use_names: dict[str, str],
    compactable_tool_names: set[str],
) -> list[_ToolResultRef]:
    refs: list[_ToolResultRef] = []
    for message_index, message in enumerate(messages):
        content = message.get("content")
        if not isinstance(content, list):
            continue
        for block_index, block in enumerate(content):
            if not isinstance(block, dict) or block.get("type") != "tool_result":
                continue
            if block.get("is_error") is True:
                continue
            tool_use_id = block.get("tool_use_id")
            if not isinstance(tool_use_id, str):
                continue
            tool_name = tool_use_names.get(tool_use_id)
            if tool_name in compactable_tool_names:
                refs.append(
                    _ToolResultRef(
                        message_index=message_index,
                        block_index=block_index,
                        tool_use_id=tool_use_id,
                        tool_name=tool_name,
                    )
                )
    return refs


def _copy_messages_for_compaction(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    copied: list[dict[str, Any]] = []
    for message in messages:
        content = message.get("content")
        if isinstance(content, list):
            copied.append(
                {
                    **message,
                    "content": [block.copy() if isinstance(block, dict) else block for block in content],
                }
            )
        else:
            copied.append(message.copy())
    return copied


def _placeholder(ref: _ToolResultRef) -> str:
    if ref.tool_name:
        return f"{MICRO_COMPACT_PLACEHOLDER}: {ref.tool_name} {ref.tool_use_id}]"
    return f"{MICRO_COMPACT_PLACEHOLDER}: {ref.tool_use_id}]"
