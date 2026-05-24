from __future__ import annotations

import html
import json
import re
from typing import Any

from .llm import ToolUseBlock


AGENT_TOOL_NAMES = {"explore_agent", "plan_agent", "verify_agent"}


def normalize_pseudo_tool_call(
    content_blocks: list[Any],
    *,
    available_tool_names: set[str],
    tool_use_id: str,
) -> list[Any]:
    if any(getattr(block, "type", None) == "tool_use" for block in content_blocks):
        return content_blocks

    preserved_blocks = [block for block in content_blocks if getattr(block, "type", None) == "reasoning"]
    text = _content_text(content_blocks).strip()
    parsed = _parse_pseudo_tool_call(text)
    if not parsed:
        return content_blocks

    name, tool_input = parsed
    return _pseudo_tool_blocks_or_original(
        name,
        tool_input,
        original=content_blocks,
        preserved_blocks=preserved_blocks,
        available_tool_names=available_tool_names,
        tool_use_id=tool_use_id,
    )


def contains_pseudo_tool_call(text: str) -> bool:
    return "<tool_call" in text or "<invoke" in text


def _parse_pseudo_tool_call(text: str) -> tuple[Any, dict[str, Any]] | None:
    xml_match = re.search(
        r"<invoke\s+name=[\"'](?P<name>[^\"']+)[\"']>\s*"
        r"<(?P<tag>query|prompt)>(?P<prompt>.*?)</(?P=tag)>\s*"
        r"</invoke>",
        text,
        flags=re.DOTALL,
    )
    if xml_match:
        return xml_match.group("name"), {"prompt": html.unescape(xml_match.group("prompt")).strip()}

    function_match = re.search(
        r"<function=(?P<name>[^>\s]+)>\s*(?P<body>.*?)</function>",
        text,
        flags=re.DOTALL,
    )
    if function_match:
        return function_match.group("name"), _parameters_from_pseudo_function(function_match.group("body"))

    json_match = re.search(r"<tool_call>\s*(?P<body>\{.*?\})\s*</tool_call>", text, flags=re.DOTALL)
    if not json_match:
        return None
    try:
        payload = json.loads(json_match.group("body"))
    except json.JSONDecodeError:
        return None

    name = payload.get("name")
    arguments = payload.get("arguments") or {}
    if not isinstance(arguments, dict):
        return None
    return name, arguments


def _pseudo_tool_blocks_or_original(
    name: Any,
    tool_input: dict[str, Any],
    *,
    original: list[Any],
    preserved_blocks: list[Any],
    available_tool_names: set[str],
    tool_use_id: str,
) -> list[Any]:
    if not isinstance(name, str) or name not in available_tool_names:
        return original

    if "prompt" not in tool_input and "query" in tool_input:
        tool_input = {**tool_input, "prompt": tool_input["query"]}
    if "path" not in tool_input and "file_path" in tool_input:
        tool_input = {**tool_input, "path": tool_input["file_path"]}
        tool_input.pop("file_path", None)

    prompt = tool_input.get("prompt")
    if isinstance(prompt, str):
        tool_input = {**tool_input, "prompt": html.unescape(prompt).strip()}
        prompt = tool_input["prompt"]
    if name in AGENT_TOOL_NAMES and not prompt:
        return original

    if name in AGENT_TOOL_NAMES:
        tool_input = {"prompt": prompt}

    return preserved_blocks + [ToolUseBlock(id=tool_use_id, name=name, input=tool_input)]


def _parameters_from_pseudo_function(body: str) -> dict[str, Any]:
    params: dict[str, Any] = {}
    for match in re.finditer(r"<parameter=(?P<name>[^>\s]+)>(?P<value>.*?)</parameter>", body, flags=re.DOTALL):
        params[match.group("name")] = html.unescape(match.group("value")).strip()
    return params


def _content_text(content_blocks: list[Any]) -> str:
    return "\n".join(block.text for block in content_blocks if getattr(block, "type", None) == "text")
