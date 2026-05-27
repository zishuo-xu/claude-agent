from pathlib import Path

import pytest

from mini_agent.tool_core import truncate_tool_result
from mini_agent.tools import (
    default_tools,
    is_denied_shell_command,
    is_read_only_shell_command,
    strip_thinking_markup,
    uses_bare_python_module_command,
    uses_bare_python_script_command,
    uses_shell_file_write,
    validate_shell_input,
)
from mini_agent.tasks import TaskState


def test_builtin_tool_set_shape_stays_focused(tmp_path: Path):
    tools = default_tools(tmp_path)

    assert set(tools) == {
        "list_files",
        "read_file",
        "write_file",
        "edit_file",
        "preview_edit",
        "apply_edit",
        "search_text",
        "run_shell",
        "set_tasks",
        "update_task",
        "list_tasks",
    }


def test_builtin_tool_schemas_stay_consistent(tmp_path: Path):
    tools = default_tools(tmp_path)

    for tool in tools.values():
        schema = tool.input_schema
        properties = schema.get("properties")
        required = schema.get("required", [])
        assert schema.get("type") == "object"
        assert isinstance(properties, dict)
        assert set(required) <= set(properties)

    assert "include_hidden" not in tools["list_files"].input_schema["properties"]


def test_shell_read_only_classifier_allows_simple_read_commands():
    assert is_read_only_shell_command("pwd")
    assert is_read_only_shell_command("ls -la")
    assert is_read_only_shell_command("git status --short")


def test_shell_read_only_classifier_rejects_combined_or_write_commands():
    assert not is_read_only_shell_command("pwd && rm file.txt")
    assert not is_read_only_shell_command("echo hi > out.txt")
    assert not is_read_only_shell_command("rm file.txt")


def test_run_shell_tool_marks_pwd_as_read_only(tmp_path: Path):
    run_shell = default_tools(tmp_path)["run_shell"]

    assert run_shell.read_only({"command": "pwd"})
    assert run_shell.concurrency_safe({"command": "pwd"})


def test_list_files_hides_common_noise_by_default(tmp_path: Path):
    (tmp_path / ".env").write_text("secret", encoding="utf-8")
    (tmp_path / ".venv").mkdir()
    (tmp_path / "__pycache__").mkdir()
    (tmp_path / "README.md").write_text("hello", encoding="utf-8")
    list_files = default_tools(tmp_path)["list_files"]

    result = list_files.run({"path": "."})

    assert "README.md" in result
    assert ".env" not in result
    assert ".venv" not in result
    assert "__pycache__" not in result


def test_list_files_can_include_hidden_noise_when_requested(tmp_path: Path):
    (tmp_path / ".env").write_text("secret", encoding="utf-8")
    list_files = default_tools(tmp_path)["list_files"]

    result = list_files.run({"path": ".", "include_hidden": True})

    assert ".env" in result


def test_run_shell_input_validator_rejects_empty_command():
    assert validate_shell_input({"command": ""}) == "command must be a non-empty string"
    assert validate_shell_input({"command": "   "}) == "command must be a non-empty string"
    assert validate_shell_input({"command": "pwd"}) is None


def test_run_shell_denies_system_python_package_install(tmp_path: Path):
    run_shell = default_tools(tmp_path)["run_shell"]

    assert is_denied_shell_command("pip3 install pytest")
    assert is_denied_shell_command("python3 -m pip install pytest")
    assert is_denied_shell_command("pip3 install pytest --break-system-packages")

    with pytest.raises(ValueError, match="refusing system Python package install"):
        run_shell.run({"command": "pip3 install pytest --break-system-packages"})


def test_run_shell_prefers_workspace_venv_for_python_module_commands(tmp_path: Path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    run_shell = default_tools(tmp_path)["run_shell"]

    assert uses_bare_python_module_command("python3 -m pytest tests/test_core.py")
    assert uses_bare_python_module_command("cd tmp && python3 -m pytest tests/test_core.py")
    assert not uses_bare_python_module_command("python3 script.py")
    assert not uses_bare_python_module_command(".venv/bin/python -m pytest")
    assert not uses_bare_python_module_command("/tmp/work/.venv/bin/python -m pytest")

    with pytest.raises(ValueError, match="workspace has .venv"):
        run_shell.run({"command": "python3 -m pytest tests/test_core.py"})


def test_run_shell_prefers_workspace_venv_for_python_script_commands(tmp_path: Path):
    (tmp_path / ".venv" / "bin").mkdir(parents=True)
    (tmp_path / ".venv" / "bin" / "python").write_text("", encoding="utf-8")
    run_shell = default_tools(tmp_path)["run_shell"]

    assert uses_bare_python_script_command("python script.py")
    assert uses_bare_python_script_command("python3 tmp/app.py")
    assert uses_bare_python_script_command("cd tmp && python3 app.py")
    assert not uses_bare_python_script_command(".venv/bin/python script.py")
    assert not uses_bare_python_script_command("/tmp/work/.venv/bin/python script.py")
    assert not uses_bare_python_script_command("python3 -m pytest tests/test_core.py")

    with pytest.raises(ValueError, match="use .venv/bin/python script.py"):
        run_shell.run({"command": "python tmp_context_acceptance/mini_notes.py"})


def test_file_tools_strip_thinking_markup(tmp_path: Path):
    tools = default_tools(tmp_path)

    tools["write_file"].run({"path": "story.md", "content": "开头</think>## 第二章\n正文"})
    content = (tmp_path / "story.md").read_text(encoding="utf-8")

    assert "</think>" not in content
    assert "开头\n\n## 第二章" in content
    assert strip_thinking_markup("<think>internal</think>正文") == "正文"


def test_run_shell_rejects_shell_file_writes(tmp_path: Path):
    run_shell = default_tools(tmp_path)["run_shell"]

    assert uses_shell_file_write("cat >> story.md << 'EOF'\nbody\nEOF")
    assert uses_shell_file_write("echo hi > story.md")

    with pytest.raises(ValueError, match="use write_file or edit_file"):
        run_shell.run({"command": "cat >> story.md << 'EOF'\nbody\nEOF"})


def test_tool_result_budget_keeps_head_tail_and_marker():
    result = truncate_tool_result("A" * 80 + "MIDDLE" + "Z" * 80, 100)

    assert len(result) <= 100
    assert result.startswith("A")
    assert "showing head and tail" in result
    assert result.endswith("Z")
    assert "MIDDLE" not in result


def test_read_file_tool_uses_smaller_result_budget(tmp_path: Path):
    path = tmp_path / "large.txt"
    path.write_text("start\n" + ("x" * 9000) + "\nend", encoding="utf-8")
    read_file = default_tools(tmp_path)["read_file"]

    result = read_file.run({"path": "large.txt"})

    assert len(result) <= read_file.max_result_chars
    assert result.startswith("start")
    assert "truncated tool result" in result
    assert result.endswith("end")


def test_preview_edit_returns_diff_without_modifying_file(tmp_path: Path):
    path = tmp_path / "hello.py"
    path.write_text("print('hello')\n", encoding="utf-8")
    preview_edit = default_tools(tmp_path)["preview_edit"]

    result = preview_edit.run({"path": "hello.py", "old": "hello", "new": "agent"})

    assert "--- a/hello.py" in result
    assert "+++ b/hello.py" in result
    assert "-print('hello')" in result
    assert "+print('agent')" in result
    assert path.read_text(encoding="utf-8") == "print('hello')\n"


def test_apply_edit_returns_diff_and_modifies_file(tmp_path: Path):
    path = tmp_path / "hello.py"
    path.write_text("print('hello')\n", encoding="utf-8")
    apply_edit = default_tools(tmp_path)["apply_edit"]

    result = apply_edit.run({"path": "hello.py", "old": "hello", "new": "agent"})

    assert "applied hello.py" in result
    assert "-print('hello')" in result
    assert "+print('agent')" in result
    assert path.read_text(encoding="utf-8") == "print('agent')\n"


def test_preview_edit_is_read_only_and_apply_edit_is_not(tmp_path: Path):
    tools = default_tools(tmp_path)

    assert tools["preview_edit"].read_only({"path": "x", "old": "a", "new": "b"})
    assert not tools["apply_edit"].read_only({"path": "x", "old": "a", "new": "b"})


def test_task_tools_share_task_state(tmp_path: Path):
    task_state = TaskState()
    tools = default_tools(tmp_path, task_state)

    set_result = tools["set_tasks"].run({"tasks": ["Inspect files", "Run tests"]})
    update_result = tools["update_task"].run({"id": "t1", "status": "done", "note": "ok"})
    list_result = tools["list_tasks"].run({})

    assert "t1 [todo] Inspect files" in set_result
    assert "t1 [done] Inspect files - ok" in update_result
    assert list_result == task_state.render()
    assert tools["list_tasks"].read_only({})
