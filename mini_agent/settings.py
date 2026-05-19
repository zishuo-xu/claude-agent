from __future__ import annotations

import json
from pathlib import Path

from .permissions import PermissionBehavior, PermissionRule, parse_permission_rule


def load_permission_rules(path: Path) -> list[PermissionRule]:
    if not path.exists():
        return []

    data = json.loads(path.read_text(encoding="utf-8"))
    permissions = data.get("permissions", {})
    rules: list[PermissionRule] = []
    for behavior in PermissionBehavior:
        for raw_rule in permissions.get(behavior.value, []):
            rules.append(parse_permission_rule(raw_rule, behavior))
    return rules

