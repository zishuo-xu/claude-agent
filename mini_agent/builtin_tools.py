from __future__ import annotations

import difflib
import json
import shlex
import subprocess
from pathlib import Path

from .tasks import TaskState
from .tool_core import Tool, build_tool
from .workspace import Workspace


DENIED_SHELL_FRAGMENTS = [
    "rm -rf /",
    "rm -rf .",
    "git reset --hard",
    "git clean -fd",
    "mkfs",
    ":(){",
]


READ_ONLY_SHELL_COMMANDS = {
    "pwd",
    "ls",
    "find",
    "cat",
    "head",
    "tail",
    "wc",
    "rg",
    "grep",
    "git status",
    "git diff",
    "git log",
    "git show",
    "git branch",
}

SHELL_CONTROL_TOKENS = {";", "&&", "||", "|", ">", ">>", "<", "`", "$("}


def is_read_only_shell_command(command: str) -> bool:
    if any(token in command for token in SHELL_CONTROL_TOKENS):
        return False

    try:
        parts = shlex.split(command)
    except ValueError:
        return False
    if not parts:
        return False

    first = parts[0]
    if first in READ_ONLY_SHELL_COMMANDS:
        return True
    if len(parts) >= 2 and f"{parts[0]} {parts[1]}" in READ_ONLY_SHELL_COMMANDS:
        return True
    return False


def unified_diff(path: str, before: str, after: str) -> str:
    diff = difflib.unified_diff(
        before.splitlines(keepends=True),
        after.splitlines(keepends=True),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
    )
    return "".join(diff) or "(no changes)"


def replace_text(content: str, old: str, new: str, replace_all: bool = False) -> tuple[str, int]:
    occurrences = content.count(old)
    if occurrences == 0:
        raise ValueError("old text not found")
    if occurrences > 1 and not replace_all:
        raise ValueError(f"old text occurs {occurrences} times; set replace_all=true or use a more specific old text")
    updated = content.replace(old, new) if replace_all else content.replace(old, new, 1)
    return updated, occurrences


def build_builtin_tools(root: Path, task_state: TaskState | None = None) -> dict[str, Tool]:
    workspace = Workspace(root)
    tasks = task_state or TaskState()

    def list_files(args: dict) -> str:
        path = workspace.resolve(args.get("path", "."))
        if not path.exists():
            raise FileNotFoundError(str(path))
        if not path.is_dir():
            raise NotADirectoryError(str(path))
        rows = []
        for item in sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            suffix = "/" if item.is_dir() else ""
            rows.append(f"{item.relative_to(workspace.root)}{suffix}")
        return "\n".join(rows) or "(empty)"

    def read_file(args: dict) -> str:
        path = workspace.resolve(args["path"])
        if not path.is_file():
            raise FileNotFoundError(str(path))
        return path.read_text(encoding="utf-8")

    def write_file(args: dict) -> str:
        path = workspace.resolve(args["path"])
        content = args["content"]
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return f"wrote {path.relative_to(workspace.root)} ({len(content)} bytes)"

    def edit_file(args: dict) -> str:
        path = workspace.resolve(args["path"])
        content = path.read_text(encoding="utf-8")
        updated, occurrences = replace_text(content, args["old"], args["new"], args.get("replace_all", False))
        path.write_text(updated, encoding="utf-8")
        diff = unified_diff(str(path.relative_to(workspace.root)), content, updated)
        return f"edited {path.relative_to(workspace.root)} ({occurrences} match{'es' if occurrences != 1 else ''})\n\n{diff}"

    def preview_edit(args: dict) -> str:
        path = workspace.resolve(args["path"])
        content = path.read_text(encoding="utf-8")
        updated, occurrences = replace_text(content, args["old"], args["new"], args.get("replace_all", False))
        diff = unified_diff(str(path.relative_to(workspace.root)), content, updated)
        return f"preview {path.relative_to(workspace.root)} ({occurrences} match{'es' if occurrences != 1 else ''})\n\n{diff}"

    def apply_edit(args: dict) -> str:
        path = workspace.resolve(args["path"])
        content = path.read_text(encoding="utf-8")
        updated, occurrences = replace_text(content, args["old"], args["new"], args.get("replace_all", False))
        diff = unified_diff(str(path.relative_to(workspace.root)), content, updated)
        path.write_text(updated, encoding="utf-8")
        return f"applied {path.relative_to(workspace.root)} ({occurrences} match{'es' if occurrences != 1 else ''})\n\n{diff}"

    def search_text(args: dict) -> str:
        pattern = args["pattern"]
        path = workspace.resolve(args.get("path", "."))
        command = ["rg", "--line-number", "--no-heading", pattern, str(path)]
        completed = subprocess.run(
            command,
            cwd=workspace.root,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=int(args.get("timeout_seconds", 20)),
        )
        if completed.returncode not in {0, 1}:
            raise RuntimeError(completed.stderr.strip())
        return completed.stdout or "(no matches)"

    def run_shell(args: dict) -> str:
        command = args["command"]
        if any(fragment in command for fragment in DENIED_SHELL_FRAGMENTS):
            raise ValueError(f"refusing dangerous command: {command}")
        completed = subprocess.run(
            command,
            cwd=workspace.root,
            shell=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=int(args.get("timeout_seconds", 20)),
        )
        return json.dumps(
            {
                "command": command,
                "exit_code": completed.returncode,
                "stdout": completed.stdout[-8000:],
                "stderr": completed.stderr[-8000:],
            },
            ensure_ascii=False,
            indent=2,
        )

    def set_tasks(args: dict) -> str:
        return tasks.set_tasks(args["tasks"])

    def update_task(args: dict) -> str:
        return tasks.update_task(args["id"], args["status"], args.get("note", ""))

    def list_tasks(_args: dict) -> str:
        return tasks.render()

    return {
        "list_files": build_tool(
            name="list_files",
            description="List files and directories inside the workspace.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Directory path relative to the workspace.", "default": "."}
                },
            },
            call=list_files,
            read_only=lambda _input: True,
            concurrency_safe=lambda _input: True,
        ),
        "read_file": build_tool(
            name="read_file",
            description="Read a UTF-8 text file inside the workspace.",
            input_schema={
                "type": "object",
                "properties": {"path": {"type": "string", "description": "File path relative to the workspace."}},
                "required": ["path"],
            },
            call=read_file,
            read_only=lambda _input: True,
            concurrency_safe=lambda _input: True,
        ),
        "write_file": build_tool(
            name="write_file",
            description="Write a UTF-8 text file inside the workspace, creating parent directories if needed.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "File path relative to the workspace."},
                    "content": {"type": "string", "description": "Complete file content to write."},
                },
                "required": ["path", "content"],
            },
            call=write_file,
        ),
        "edit_file": build_tool(
            name="edit_file",
            description="Replace text in an existing UTF-8 file inside the workspace and return a unified diff. Prefer preview_edit before applying risky changes.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string", "description": "Exact text to replace."},
                    "new": {"type": "string", "description": "Replacement text."},
                    "replace_all": {"type": "boolean", "default": False},
                },
                "required": ["path", "old", "new"],
            },
            call=edit_file,
        ),
        "preview_edit": build_tool(
            name="preview_edit",
            description="Preview a text replacement as a unified diff without modifying the file.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string", "description": "Exact text to replace."},
                    "new": {"type": "string", "description": "Replacement text."},
                    "replace_all": {"type": "boolean", "default": False},
                },
                "required": ["path", "old", "new"],
            },
            call=preview_edit,
            read_only=lambda _input: True,
            concurrency_safe=lambda _input: True,
        ),
        "apply_edit": build_tool(
            name="apply_edit",
            description="Apply a text replacement to an existing UTF-8 file and return the unified diff that was applied.",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "old": {"type": "string", "description": "Exact text to replace."},
                    "new": {"type": "string", "description": "Replacement text."},
                    "replace_all": {"type": "boolean", "default": False},
                },
                "required": ["path", "old", "new"],
            },
            call=apply_edit,
        ),
        "search_text": build_tool(
            name="search_text",
            description="Search workspace text using ripgrep.",
            input_schema={
                "type": "object",
                "properties": {
                    "pattern": {"type": "string"},
                    "path": {"type": "string", "default": "."},
                    "timeout_seconds": {"type": "integer", "default": 20, "minimum": 1, "maximum": 120},
                },
                "required": ["pattern"],
            },
            call=search_text,
            read_only=lambda _input: True,
            concurrency_safe=lambda _input: True,
        ),
        "run_shell": build_tool(
            name="run_shell",
            description="Run a shell command in the workspace and return stdout/stderr.",
            input_schema={
                "type": "object",
                "properties": {
                    "command": {"type": "string"},
                    "timeout_seconds": {"type": "integer", "default": 20, "minimum": 1, "maximum": 120},
                },
                "required": ["command"],
            },
            call=run_shell,
            read_only=lambda args: is_read_only_shell_command(args.get("command", "")),
            concurrency_safe=lambda args: is_read_only_shell_command(args.get("command", "")),
            destructive=lambda args: any(word in args.get("command", "") for word in ["rm ", "mv ", "chmod ", "chown "]),
        ),
        "set_tasks": build_tool(
            name="set_tasks",
            description="Replace the current task list with ordered todo items for a multi-step task.",
            input_schema={
                "type": "object",
                "properties": {
                    "tasks": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Ordered task titles.",
                    }
                },
                "required": ["tasks"],
            },
            call=set_tasks,
        ),
        "update_task": build_tool(
            name="update_task",
            description="Update one task status and optional note. Valid statuses: todo, in_progress, done, blocked.",
            input_schema={
                "type": "object",
                "properties": {
                    "id": {"type": "string", "description": "Task id such as t1."},
                    "status": {
                        "type": "string",
                        "enum": ["todo", "in_progress", "done", "blocked"],
                    },
                    "note": {"type": "string", "default": ""},
                },
                "required": ["id", "status"],
            },
            call=update_task,
        ),
        "list_tasks": build_tool(
            name="list_tasks",
            description="List the current task state.",
            input_schema={"type": "object", "properties": {}},
            call=list_tasks,
            read_only=lambda _input: True,
            concurrency_safe=lambda _input: True,
        ),
    }
