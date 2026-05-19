from __future__ import annotations

import fnmatch
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PermissionMode(str, Enum):
    DEFAULT = "default"
    PLAN = "plan"
    ACCEPT_EDITS = "acceptEdits"
    BYPASS = "bypassPermissions"
    DONT_ASK = "dontAsk"


class PermissionBehavior(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


@dataclass(frozen=True)
class PermissionRule:
    behavior: PermissionBehavior
    tool_name: str
    content_pattern: str | None = None


@dataclass
class PermissionDecision:
    behavior: PermissionBehavior
    reason: str


@dataclass
class PermissionContext:
    mode: PermissionMode
    rules: list[PermissionRule] = field(default_factory=list)


def parse_permission_rule(raw: str, behavior: PermissionBehavior) -> PermissionRule:
    match = re.fullmatch(r"([^()]+)(?:\((.*)\))?", raw.strip())
    if not match:
        raise ValueError(f"invalid permission rule: {raw}")
    tool_name = match.group(1).strip()
    content_pattern = match.group(2)
    if content_pattern in {"", "*"}:
        content_pattern = None
    return PermissionRule(behavior=behavior, tool_name=tool_name, content_pattern=content_pattern)


def command_for_permission(tool_name: str, tool_input: dict[str, Any]) -> str:
    if tool_name == "run_shell":
        return str(tool_input.get("command", ""))
    if "path" in tool_input:
        return str(tool_input["path"])
    if "pattern" in tool_input:
        return str(tool_input["pattern"])
    return ""


def matching_rule(
    rules: list[PermissionRule],
    tool_name: str,
    tool_input: dict[str, Any],
    behavior: PermissionBehavior | None = None,
) -> PermissionRule | None:
    content = command_for_permission(tool_name, tool_input)
    for rule in rules:
        if behavior is not None and rule.behavior != behavior:
            continue
        if rule.tool_name != tool_name and rule.tool_name != "*":
            continue
        if rule.content_pattern is None:
            return rule
        if fnmatch.fnmatch(content, rule.content_pattern):
            return rule
    return None


def decide_permission(
    *,
    context: PermissionContext,
    tool_name: str,
    tool_input: dict[str, Any],
    read_only: bool,
    destructive: bool,
) -> PermissionDecision:
    for behavior in [PermissionBehavior.DENY, PermissionBehavior.ALLOW, PermissionBehavior.ASK]:
        rule = matching_rule(context.rules, tool_name, tool_input, behavior)
        if rule:
            return PermissionDecision(rule.behavior, f"matched {behavior.value} rule for {tool_name}")

    if context.mode == PermissionMode.BYPASS:
        return PermissionDecision(PermissionBehavior.ALLOW, "bypassPermissions mode")

    if context.mode == PermissionMode.DONT_ASK:
        if read_only and not destructive:
            return PermissionDecision(PermissionBehavior.ALLOW, "read-only in dontAsk mode")
        return PermissionDecision(PermissionBehavior.DENY, "dontAsk mode refuses actions that need confirmation")

    if context.mode == PermissionMode.PLAN:
        if read_only and not destructive:
            return PermissionDecision(PermissionBehavior.ALLOW, "read-only in plan mode")
        return PermissionDecision(PermissionBehavior.ASK, "write/destructive action in plan mode")

    if context.mode == PermissionMode.ACCEPT_EDITS:
        if read_only and not destructive:
            return PermissionDecision(PermissionBehavior.ALLOW, "read-only")
        if tool_name in {"write_file", "edit_file"} and not destructive:
            return PermissionDecision(PermissionBehavior.ALLOW, "workspace edit in acceptEdits mode")
        return PermissionDecision(PermissionBehavior.ASK, "non-edit action in acceptEdits mode")

    if read_only and not destructive:
        return PermissionDecision(PermissionBehavior.ALLOW, "read-only")
    return PermissionDecision(PermissionBehavior.ASK, "default mode requires confirmation")
