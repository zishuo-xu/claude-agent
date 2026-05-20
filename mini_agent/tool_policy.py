from __future__ import annotations

from .intent import IntentDecision
from .tool_core import Tool


def tools_for_intent(tools: dict[str, Tool], decision: IntentDecision | None) -> dict[str, Tool]:
    if decision and not decision.allow_tools:
        return {}
    return tools

