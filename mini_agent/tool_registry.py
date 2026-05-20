from __future__ import annotations

from pathlib import Path

from .builtin_tools import build_builtin_tools
from .intent import IntentDecision
from .tasks import TaskState
from .tool_core import Tool
from .tool_policy import tools_for_intent


class ToolRegistry:
    def __init__(self, tools: dict[str, Tool]):
        self._tools = tools

    @classmethod
    def with_builtin_tools(cls, root: Path, task_state: TaskState | None = None) -> "ToolRegistry":
        return cls(build_builtin_tools(root, task_state))

    def all(self) -> dict[str, Tool]:
        return self._tools

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def read_only(self) -> "ToolRegistry":
        return ToolRegistry(
            {
                name: tool
                for name, tool in self._tools.items()
                if tool.read_only({})
            }
        )

    def available_for_intent(self, decision: IntentDecision | None) -> dict[str, Tool]:
        return tools_for_intent(self._tools, decision)

    def api_specs_for_intent(self, decision: IntentDecision | None) -> list[dict]:
        return [tool.api_spec() for tool in self.available_for_intent(decision).values()]
