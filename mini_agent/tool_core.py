from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


ToolHandler = Callable[[dict[str, Any]], str]
ToolValidator = Callable[[dict[str, Any]], str | None]


@dataclass
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    call: ToolHandler
    max_result_chars: int = 20_000
    read_only: Callable[[dict[str, Any]], bool] = lambda _input: False
    concurrency_safe: Callable[[dict[str, Any]], bool] = lambda _input: False
    destructive: Callable[[dict[str, Any]], bool] = lambda _input: False
    validate_input: ToolValidator = lambda _input: None

    def api_spec(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }

    def run(self, tool_input: dict[str, Any]) -> str:
        result = self.call(tool_input)
        if len(result) > self.max_result_chars:
            return result[: self.max_result_chars] + "\n...[truncated]"
        return result


def build_tool(**kwargs: Any) -> Tool:
    return Tool(**kwargs)
