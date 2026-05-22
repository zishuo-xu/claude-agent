from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_runtime_keeps_tool_execution_boundary_lightweight():
    source = (PROJECT_ROOT / "mini_agent" / "runtime.py").read_text(encoding="utf-8")

    assert "ToolTurnExecutor" in source
    assert "ThreadPoolExecutor" not in source
    assert "decide_permission" not in source
    assert "PermissionBehavior" not in source


def test_runtime_keeps_terminal_io_outside_main_loop():
    source = (PROJECT_ROOT / "mini_agent" / "runtime.py").read_text(encoding="utf-8")

    assert "print(" not in source
    assert "input(" not in source
