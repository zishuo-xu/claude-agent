from mini_agent.events import RuntimeEvent, _format_permission_prompt, print_runtime_event


def test_print_runtime_event_hides_tool_batch_events_by_default(capsys):
    print_runtime_event(
        RuntimeEvent("tool_batch_start", {"parallel": True, "tools": ["read_file"], "tool_use_ids": ["call_1"]})
    )
    print_runtime_event(
        RuntimeEvent("tool_batch_end", {"parallel": True, "tools": ["read_file"], "tool_use_ids": ["call_1"]})
    )

    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_runtime_event_does_not_print_permission_request(capsys):
    print_runtime_event(
        RuntimeEvent(
            "permission_request",
            {"name": "run_shell", "input": {"command": "python3 hello.py"}, "reason": "write/destructive action in plan mode"},
        )
    )

    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_runtime_event_formats_read_file_start(capsys):
    print_runtime_event(RuntimeEvent("tool_start", {"name": "read_file", "input": {"path": "agent.py"}}))

    captured = capsys.readouterr()
    assert captured.out == "\n\n[agent] Reading file: agent.py\n"


def test_print_runtime_event_formats_list_files_start(capsys):
    print_runtime_event(RuntimeEvent("tool_start", {"name": "list_files", "input": {}}))

    captured = capsys.readouterr()
    assert captured.out == "\n\n[agent] Checking files: .\n"


def test_format_permission_prompt_for_shell_command():
    prompt = _format_permission_prompt(
        name="run_shell",
        tool_input={"command": "python3 hello.py"},
        reason="write/destructive action in plan mode",
    )

    assert "[permission request]" in prompt
    assert "Tool: run_shell" in prompt
    assert "Reason: write/destructive action in plan mode" in prompt
    assert "Target: python3 hello.py" in prompt
    assert "anything else to reject [y/N]:" in prompt


def test_format_permission_prompt_for_file_path():
    prompt = _format_permission_prompt(
        name="write_file",
        tool_input={"path": "tmp/hello.py", "content": "print('hello')"},
        reason="write/destructive action in plan mode",
    )

    assert "Tool: write_file" in prompt
    assert "Target: tmp/hello.py" in prompt
    assert "print('hello')" not in prompt


def test_print_runtime_event_hides_long_successful_tool_result(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "read_file", "content": "x" * 2_000, "is_error": False}))

    captured = capsys.readouterr()
    assert captured.out == "[result] Read file (2000 chars; content hidden from display).\n"


def test_print_runtime_event_hides_short_read_file_result(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "read_file", "content": "short result", "is_error": False}))

    captured = capsys.readouterr()
    assert captured.out == "[result] Read file (12 chars; content hidden from display).\n"


def test_print_runtime_event_keeps_short_write_file_result_visible(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "write_file", "content": "wrote tmp/a.py (10 bytes)", "is_error": False}))

    captured = capsys.readouterr()
    assert captured.out == "wrote tmp/a.py (10 bytes)\n"


def test_print_runtime_event_hides_search_text_matches(capsys):
    print_runtime_event(
        RuntimeEvent(
            "tool_result",
            {"name": "search_text", "content": "README.md:1:# Mini-Claude\n", "is_error": False},
        )
    )

    captured = capsys.readouterr()
    assert captured.out == "[result] Search returned 26 chars; content hidden from display.\n"


def test_print_runtime_event_summarizes_search_text_no_matches(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "search_text", "content": "(no matches)", "is_error": False}))

    captured = capsys.readouterr()
    assert captured.out == "[result] No text matches found.\n"


def test_print_runtime_event_formats_task_results(capsys):
    print_runtime_event(
        RuntimeEvent(
            "tool_result",
            {
                "name": "update_task",
                "content": "t1 [done] Inspect files - ok\nt2 [in_progress] Run tests",
                "is_error": False,
            },
        )
    )

    captured = capsys.readouterr()
    assert captured.out == "[tasks]\n- t1 done: Inspect files - ok\n- t2 in_progress: Run tests\n"


def test_print_runtime_event_formats_empty_task_result(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "list_tasks", "content": "(no tasks)", "is_error": False}))

    captured = capsys.readouterr()
    assert captured.out == "[tasks] none\n"


def test_print_runtime_event_keeps_error_tool_result_visible(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "read_file", "content": "error" * 400, "is_error": True}))

    captured = capsys.readouterr()
    assert "hidden from display" not in captured.out
    assert captured.out == "[tool_error] read_file: " + ("error" * 400) + "\n"


def test_print_runtime_event_formats_shell_success_result(capsys):
    print_runtime_event(
        RuntimeEvent(
            "tool_result",
            {
                "name": "run_shell",
                "content": '{"command": "python3 hello.py", "exit_code": 0, "stdout": "hello agent\\n", "stderr": ""}',
                "is_error": False,
            },
        )
    )

    captured = capsys.readouterr()
    assert captured.out == "[shell] exit 0: python3 hello.py\nstdout:\nhello agent\n"


def test_print_runtime_event_formats_shell_failure_result(capsys):
    print_runtime_event(
        RuntimeEvent(
            "tool_result",
            {
                "name": "run_shell",
                "content": (
                    '{"command": "python hello.py", "exit_code": 127, "stdout": "", '
                    '"stderr": "/bin/sh: python: command not found\\n"}'
                ),
                "is_error": False,
            },
        )
    )

    captured = capsys.readouterr()
    assert captured.out == "[shell] exit 127: python hello.py\nstderr:\n/bin/sh: python: command not found\n"


def test_print_runtime_event_summarizes_list_files_result(capsys):
    print_runtime_event(
        RuntimeEvent(
            "tool_result",
            {
                "name": "list_files",
                "content": "docs/\nmini_agent/\ntests/\nREADME.md\nVERSION\nCHANGELOG.md\n",
                "is_error": False,
            },
        )
    )

    captured = capsys.readouterr()
    assert captured.out == "[result] Found 6 entries: docs/, mini_agent/, tests/, README.md, VERSION, ... +1 more\n"
