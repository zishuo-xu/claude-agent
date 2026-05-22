from __future__ import annotations

from .intent import IntentDecision
from .intent import Intent
from .tool_core import Tool


PROJECT_QUESTION_TOOLS = {
    "list_files",
    "read_file",
    "search_text",
}


def tools_for_intent(tools: dict[str, Tool], decision: IntentDecision | None) -> dict[str, Tool]:
    if decision and not decision.allow_tools:
        return {}
    if decision and decision.requested_tool:
        tool = tools.get(decision.requested_tool)
        return {decision.requested_tool: tool} if tool else {}
    if decision and decision.intent == Intent.PROJECT_QUESTION:
        return {name: tool for name, tool in tools.items() if name in PROJECT_QUESTION_TOOLS}
    if decision and decision.hidden_tools:
        return {name: tool for name, tool in tools.items() if name not in decision.hidden_tools}
    return tools
