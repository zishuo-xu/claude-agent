from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_architecture_doc_states_eight_layers_explicitly():
    content = (ROOT / "docs" / "architecture.md").read_text(encoding="utf-8")

    assert "当前架构明确分为 8 层" in content
    assert "`Sub Agents` 是独立一层" in content
