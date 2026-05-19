from pathlib import Path

import pytest

from mini_agent.workspace import Workspace


def test_workspace_resolves_relative_path(tmp_path: Path):
    workspace = Workspace(tmp_path)

    assert workspace.resolve("a/b.txt") == tmp_path / "a" / "b.txt"


def test_workspace_rejects_parent_escape(tmp_path: Path):
    workspace = Workspace(tmp_path)

    with pytest.raises(ValueError):
        workspace.resolve("../outside.txt")

