from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class RuntimeEvent:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[RuntimeEvent], None]
PermissionRequestHandler = Callable[[str, dict[str, Any], str], bool]
MAX_DISPLAY_TOOL_RESULT_CHARS = 1_200


def print_runtime_event(event: RuntimeEvent) -> None:
    if event.type == "text_delta":
        print(event.payload.get("text", ""), end="", flush=True)
    elif event.type == "tool_start":
        print(f"\n\n[tool] {event.payload['name']} {event.payload['input']}")
    elif event.type == "tool_result":
        print(_format_tool_result_for_display(event.payload))
    elif event.type == "permission_request":
        return
    elif event.type == "context_notice":
        print(f"\n[context] {event.payload['message']}\n")
    elif event.type == "model_fallback":
        print(f"\n[model] {event.payload['from_model']} failed; retrying with {event.payload['to_model']}\n")
    elif event.type == "final_answer":
        print()
    elif event.type == "stopped":
        print(f"\nStopped after {event.payload['max_turns']} turns.")


def prompt_permission_request(name: str, tool_input: dict[str, Any], reason: str) -> bool:
    answer = input(_format_permission_prompt(name=name, tool_input=tool_input, reason=reason)).strip().lower()
    return answer in {"y", "yes"}


def _format_permission_prompt(*, name: str, tool_input: dict[str, Any], reason: str) -> str:
    lines = [
        "",
        "[permission request]",
        f"Tool: {name}",
        f"Reason: {reason}",
    ]
    target = _permission_target(name, tool_input)
    if target:
        lines.append(f"Target: {target}")
    lines.append("Allow this operation? Type y to allow, anything else to reject [y/N]: ")
    return "\n".join(lines)


def _permission_target(name: str, tool_input: dict[str, Any]) -> str:
    if name == "run_shell":
        return str(tool_input.get("command", ""))
    if "path" in tool_input:
        return str(tool_input["path"])
    if "pattern" in tool_input:
        return str(tool_input["pattern"])
    if not tool_input:
        return ""
    return json.dumps(tool_input, ensure_ascii=False)


def _format_tool_result_for_display(payload: dict[str, Any]) -> str:
    content = str(payload.get("content", ""))
    if payload.get("name") == "run_shell":
        shell_result = _format_shell_result_for_display(content)
        if shell_result is not None:
            return shell_result
    if payload.get("name") == "list_files" and not payload.get("is_error"):
        return _format_list_files_result_for_display(content)

    if payload.get("is_error"):
        return f"[tool_error] {payload.get('name', 'tool')}: {content}"

    if len(content) <= MAX_DISPLAY_TOOL_RESULT_CHARS:
        return content

    name = payload.get("name", "tool")
    return f"[tool_result] {name} returned {len(content)} chars; hidden from display."


def _format_shell_result_for_display(content: str) -> str | None:
    try:
        result = json.loads(content)
    except json.JSONDecodeError:
        return None
    if not isinstance(result, dict) or "command" not in result or "exit_code" not in result:
        return None

    lines = [f"[shell] exit {result['exit_code']}: {result['command']}"]
    stdout = str(result.get("stdout") or "").rstrip()
    stderr = str(result.get("stderr") or "").rstrip()
    if stdout:
        lines.extend(["stdout:", stdout])
    if stderr:
        lines.extend(["stderr:", stderr])
    if not stdout and not stderr:
        lines.append("[no output]")
    return "\n".join(lines)


def _format_list_files_result_for_display(content: str) -> str:
    entries = [line for line in content.splitlines() if line.strip()]
    if not entries:
        return "[tool_result] list_files returned 0 entries."
    preview = ", ".join(entries[:5])
    suffix = "" if len(entries) <= 5 else f", ... +{len(entries) - 5} more"
    return f"[tool_result] list_files returned {len(entries)} entries: {preview}{suffix}"
