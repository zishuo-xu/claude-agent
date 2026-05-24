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

    def validation_error(self, tool_input: dict[str, Any]) -> str | None:
        schema = self.input_schema or {}
        properties = schema.get("properties")
        if isinstance(properties, dict):
            unknown_fields = sorted(set(tool_input) - set(properties))
            if unknown_fields:
                return f"unknown input field(s): {', '.join(unknown_fields)}"

        required = schema.get("required")
        if isinstance(required, list):
            missing_fields = [field for field in required if field not in tool_input]
            if missing_fields:
                return f"missing required input field(s): {', '.join(missing_fields)}"

        if isinstance(properties, dict):
            for field, value in tool_input.items():
                field_schema = properties.get(field)
                if not isinstance(field_schema, dict):
                    continue
                enum_values = field_schema.get("enum")
                if isinstance(enum_values, list) and value not in enum_values:
                    return f"invalid value for {field}: expected one of {', '.join(map(str, enum_values))}"
                expected_type = field_schema.get("type")
                if isinstance(expected_type, str) and not _matches_json_type(value, expected_type, field_schema):
                    return f"invalid type for {field}: expected {expected_type}"

        return self.validate_input(tool_input)

    def run(self, tool_input: dict[str, Any]) -> str:
        result = self.call(tool_input)
        return truncate_tool_result(result, self.max_result_chars)


def build_tool(**kwargs: Any) -> Tool:
    return Tool(**kwargs)


def _matches_json_type(value: Any, expected_type: str, schema: dict[str, Any]) -> bool:
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "boolean":
        return isinstance(value, bool)
    if expected_type == "array":
        if not isinstance(value, list):
            return False
        item_schema = schema.get("items")
        item_type = item_schema.get("type") if isinstance(item_schema, dict) else None
        if not isinstance(item_type, str):
            return True
        return all(_matches_json_type(item, item_type, item_schema) for item in value)
    if expected_type == "object":
        return isinstance(value, dict)
    return True


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
