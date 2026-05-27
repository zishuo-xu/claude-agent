from agent import _join_input_lines, format_cli_error


def test_join_input_lines_preserves_pasted_multiline_input():
    text = _join_input_lines(
        "按案例执行：",
        [
            "",
            "1. 创建 calc.py\n",
            "2. 运行验证\n",
        ],
    )

    assert text == "按案例执行：\n\n1. 创建 calc.py\n2. 运行验证"


def test_join_input_lines_strips_outer_whitespace():
    text = _join_input_lines("  /exit  ", [])

    assert text == "/exit"


def test_format_cli_error_is_single_line():
    assert format_cli_error(RuntimeError("model down")) == "[error] RuntimeError: model down"
