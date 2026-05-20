from pathlib import Path

from mini_agent.tools import default_tools, is_read_only_shell_command, validate_shell_input
from mini_agent.tasks import TaskState


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
