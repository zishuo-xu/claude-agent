from __future__ import annotations

from pathlib import Path

from .builtin_tools import (
    build_builtin_tools,
    is_denied_shell_command,
    is_read_only_shell_command,
    replace_text,
    strip_thinking_markup,
    unified_diff,
    uses_bare_python_module_command,
    uses_bare_python_script_command,
    uses_shell_file_write,
    validate_shell_input,
)
from .tasks import TaskState
from .tool_core import Tool, build_tool


def default_tools(root: Path, task_state: TaskState | None = None) -> dict[str, Tool]:
    """Backward-compatible helper for tests and simple callers."""

    return build_builtin_tools(root, task_state)


__all__ = [
    "Tool",
    "build_tool",
    "default_tools",
    "is_denied_shell_command",
    "is_read_only_shell_command",
    "uses_bare_python_module_command",
    "uses_bare_python_script_command",
    "uses_shell_file_write",
    "replace_text",
    "strip_thinking_markup",
    "validate_shell_input",
    "unified_diff",
]
