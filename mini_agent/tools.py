from __future__ import annotations

from pathlib import Path

from .builtin_tools import build_builtin_tools, is_read_only_shell_command, replace_text, unified_diff, validate_shell_input
from .tasks import TaskState
from .tool_core import Tool, build_tool


def default_tools(root: Path, task_state: TaskState | None = None) -> dict[str, Tool]:
    """Backward-compatible helper for tests and simple callers."""

    return build_builtin_tools(root, task_state)


__all__ = [
    "Tool",
    "build_tool",
    "default_tools",
    "is_read_only_shell_command",
    "replace_text",
    "validate_shell_input",
    "unified_diff",
]
