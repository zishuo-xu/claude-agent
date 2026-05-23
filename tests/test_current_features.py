from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_current_features_states_tool_count_breakdown():
    content = (ROOT / "docs" / "current-features.md").read_text(encoding="utf-8")

    assert "共有 14 个模型可用工具：11 个基础工具 + 3 个只读子 Agent 工具" in content
