from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from anthropic import Anthropic
from openai import OpenAI


@dataclass
class TextBlock:
    text: str
    type: str = "text"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "text": self.text}


@dataclass
class ToolUseBlock:
    id: str
    name: str
    input: dict[str, Any]
    type: str = "tool_use"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "id": self.id, "name": self.name, "input": self.input}


@dataclass
class ReasoningBlock:
    content: str
    type: str = "reasoning"

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "content": self.content}


@dataclass
class LLMResponse:
    content: list[TextBlock | ToolUseBlock | ReasoningBlock]


class LLMClient(Protocol):
    def complete(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        ...


class AnthropicLLM:
    def __init__(self) -> None:
        self.client = Anthropic()

    def complete(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        response = self.client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=messages,
            tools=tools or [],
        )
        return LLMResponse(content=list(response.content))


class OpenAICompatibleLLM:
    """Adapter for OpenAI-compatible /v1 chat completions APIs.

    The runtime stores messages in an Anthropic-like shape because that mirrors
    Claude Code's tool loop. This adapter translates that shape to OpenAI
    function calling on the boundary.
    """

    def __init__(self, *, api_key: str, base_url: str) -> None:
        self.client = OpenAI(api_key=api_key, base_url=base_url)

    def complete(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> LLMResponse:
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": self._to_openai_messages(system, messages),
        }
        if tools:
            request["tools"] = self._to_openai_tools(tools)
            request["tool_choice"] = "auto"
        response = self.client.chat.completions.create(**request)
        message = response.choices[0].message
        blocks: list[TextBlock | ToolUseBlock | ReasoningBlock] = []
        reasoning_content = self._get_reasoning_content(message)
        if reasoning_content:
            blocks.append(ReasoningBlock(content=reasoning_content))
        if message.content:
            blocks.append(TextBlock(text=message.content))
        for tool_call in message.tool_calls or []:
            arguments = tool_call.function.arguments or "{}"
            try:
                tool_input = json.loads(arguments)
            except json.JSONDecodeError:
                tool_input = {"raw_arguments": arguments}
            blocks.append(
                ToolUseBlock(
                    id=tool_call.id,
                    name=tool_call.function.name,
                    input=tool_input,
                )
            )
        return LLMResponse(content=blocks)

    @staticmethod
    def _get_reasoning_content(message: Any) -> str | None:
        reasoning_content = getattr(message, "reasoning_content", None)
        if reasoning_content:
            return reasoning_content
        model_extra = getattr(message, "model_extra", None) or {}
        return model_extra.get("reasoning_content")

    @staticmethod
    def _to_openai_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool.get("input_schema", {"type": "object", "properties": {}}),
                },
            }
            for tool in tools
        ]

    @staticmethod
    def _to_openai_messages(system: str, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        converted: list[dict[str, Any]] = [{"role": "system", "content": system}]
        for message in messages:
            role = message["role"]
            content = message.get("content", "")
            if isinstance(content, str):
                converted.append({"role": role, "content": content})
                continue

            if role == "assistant":
                text_parts: list[str] = []
                tool_calls: list[dict[str, Any]] = []
                reasoning_content: str | None = None
                for block in content:
                    if block.get("type") == "text":
                        text_parts.append(block.get("text", ""))
                    elif block.get("type") == "reasoning":
                        reasoning_content = block.get("content", "")
                    elif block.get("type") == "tool_use":
                        tool_calls.append(
                            {
                                "id": block["id"],
                                "type": "function",
                                "function": {
                                    "name": block["name"],
                                    "arguments": json.dumps(block.get("input", {}), ensure_ascii=False),
                                },
                            }
                        )
                openai_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": "\n".join(text_parts) if text_parts else None,
                }
                if tool_calls:
                    openai_message["tool_calls"] = tool_calls
                if reasoning_content:
                    openai_message["reasoning_content"] = reasoning_content
                converted.append(openai_message)
                continue

            for block in content:
                if block.get("type") == "tool_result":
                    converted.append(
                        {
                            "role": "tool",
                            "tool_call_id": block["tool_use_id"],
                            "content": block.get("content", ""),
                        }
                    )
        return converted
