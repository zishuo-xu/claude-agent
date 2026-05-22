from mini_agent.events import RuntimeEvent, print_runtime_event


def test_print_runtime_event_hides_tool_batch_events_by_default(capsys):
    print_runtime_event(
        RuntimeEvent("tool_batch_start", {"parallel": True, "tools": ["read_file"], "tool_use_ids": ["call_1"]})
    )
    print_runtime_event(
        RuntimeEvent("tool_batch_end", {"parallel": True, "tools": ["read_file"], "tool_use_ids": ["call_1"]})
    )

    captured = capsys.readouterr()
    assert captured.out == ""


def test_print_runtime_event_hides_long_successful_tool_result(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "read_file", "content": "x" * 2_000, "is_error": False}))

    captured = capsys.readouterr()
    assert captured.out == "[tool_result] read_file returned 2000 chars; hidden from display.\n"


def test_print_runtime_event_keeps_short_tool_result_visible(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "read_file", "content": "short result", "is_error": False}))

    captured = capsys.readouterr()
    assert captured.out == "short result\n"


def test_print_runtime_event_keeps_error_tool_result_visible(capsys):
    print_runtime_event(RuntimeEvent("tool_result", {"name": "read_file", "content": "error" * 400, "is_error": True}))

    captured = capsys.readouterr()
    assert "hidden from display" not in captured.out
    assert captured.out == ("error" * 400) + "\n"


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
    assert captured.out == "[tool_result] list_files returned 6 entries: docs/, mini_agent/, tests/, README.md, VERSION, ... +1 more\n"
