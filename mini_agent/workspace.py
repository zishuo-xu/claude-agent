from __future__ import annotations

from pathlib import Path


class Workspace:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def resolve(self, path: str) -> Path:
        candidate = (self.root / path).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError(f"path escapes workspace: {path}")
        return candidate

