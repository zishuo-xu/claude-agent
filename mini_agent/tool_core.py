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
        return truncate_tool_result(result, self.max_result_chars)


def build_tool(**kwargs: Any) -> Tool:
    return Tool(**kwargs)


def truncate_tool_result(result: str, max_chars: int) -> str:
    if len(result) <= max_chars:
        return result

    marker = f"\n...[truncated tool result from {len(result)} to {max_chars} chars; showing head and tail]...\n"
    remaining = max_chars - len(marker)
    if remaining <= 0:
        return result[:max_chars]

    head_chars = max(1, remaining * 3 // 4)
    tail_chars = max(1, remaining - head_chars)
    return result[:head_chars] + marker + result[-tail_chars:]
