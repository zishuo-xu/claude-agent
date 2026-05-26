from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class RuntimeEvent:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[RuntimeEvent], None]
PermissionRequestHandler = Callable[[str, dict[str, Any], str], bool]
MAX_DISPLAY_TOOL_RESULT_CHARS = 1_200
SUMMARY_ONLY_TOOL_RESULTS = {"read_file", "search_text"}
TASK_TOOL_RESULTS = {"set_tasks", "update_task", "list_tasks"}


def print_runtime_event(event: RuntimeEvent) -> None:
    if event.type == "text_delta":
        print(event.payload.get("text", ""), end="", flush=True)
    elif event.type == "tool_start":
        print(_format_tool_start_for_display(event.payload))
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


def _format_tool_start_for_display(payload: dict[str, Any]) -> str:
    name = payload.get("name", "tool")
    tool_input = payload.get("input") or {}
    if name == "list_files":
        return f"\n\n[agent] Checking files: {_tool_target(tool_input, default='.')}"
    if name == "read_file":
        return f"\n\n[agent] Reading file: {_tool_target(tool_input)}"
    if name == "search_text":
        return f"\n\n[agent] Searching text: {_tool_target(tool_input)}"
    if name == "run_shell":
        return f"\n\n[agent] Running command: {_tool_target(tool_input)}"
    if name in {"write_file", "edit_file", "preview_edit", "apply_edit"}:
        return f"\n\n[agent] Editing file: {_tool_target(tool_input)}"
    if name in TASK_TOOL_RESULTS:
        return f"\n\n[agent] Updating task state: {name}"
    return f"\n\n[agent] Using tool: {name}"


def _tool_target(tool_input: dict[str, Any], *, default: str = "") -> str:
    if "path" in tool_input:
        return str(tool_input["path"])
    if "command" in tool_input:
        return str(tool_input["command"])
    if "pattern" in tool_input:
        return str(tool_input["pattern"])
    return default


def _format_tool_result_for_display(payload: dict[str, Any]) -> str:
    content = str(payload.get("content", ""))
    name = payload.get("name", "tool")
    if name == "run_shell":
        shell_result = _format_shell_result_for_display(content)
        if shell_result is not None:
            return shell_result
    if name == "list_files" and not payload.get("is_error"):
        return _format_list_files_result_for_display(content)
    if name in TASK_TOOL_RESULTS and not payload.get("is_error"):
        return _format_task_result_for_display(content)

    if payload.get("is_error"):
        return f"[tool_error] {name}: {content}"

    if name in SUMMARY_ONLY_TOOL_RESULTS:
        return _format_summary_only_tool_result(name, content)

    if len(content) <= MAX_DISPLAY_TOOL_RESULT_CHARS:
        return content

    return f"[result] {name} returned {len(content)} chars; hidden from display."


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
        return "[result] Found 0 entries."
    preview = ", ".join(entries[:5])
    suffix = "" if len(entries) <= 5 else f", ... +{len(entries) - 5} more"
    return f"[result] Found {len(entries)} entries: {preview}{suffix}"


def _format_summary_only_tool_result(name: str, content: str) -> str:
    if name == "search_text" and content == "(no matches)":
        return "[result] No text matches found."
    if name == "read_file":
        return f"[result] Read file ({len(content)} chars; content hidden from display)."
    if name == "search_text":
        return f"[result] Search returned {len(content)} chars; content hidden from display."
    return f"[result] {name} returned {len(content)} chars; hidden from display."


def _format_task_result_for_display(content: str) -> str:
    if content == "(no tasks)":
        return "[tasks] none"

    lines = []
    for raw_line in content.splitlines():
        match = re.match(r"^(t\d+) \[([a-z_]+)\] (.*)$", raw_line.strip())
        if not match:
            return content
        task_id, status, title = match.groups()
        lines.append(f"- {task_id} {status}: {title}")
    if not lines:
        return "[tasks] none"
    return "[tasks]\n" + "\n".join(lines)
