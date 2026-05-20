from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Iterator, Protocol

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


@dataclass
class TextDeltaEvent:
    text: str
    type: str = "text_delta"


@dataclass
class FinalResponseEvent:
    response: LLMResponse
    type: str = "final_response"


LLMStreamEvent = TextDeltaEvent | FinalResponseEvent


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

    def stream_complete(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[LLMStreamEvent]:
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

    def stream_complete(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[LLMStreamEvent]:
        response = self.complete(model=model, max_tokens=max_tokens, system=system, messages=messages, tools=tools)
        for block in response.content:
            if getattr(block, "type", None) == "text":
                yield TextDeltaEvent(text=block.text)
        yield FinalResponseEvent(response=response)


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
        return LLMResponse(content=self._blocks_from_message(message))

    def stream_complete(
        self,
        *,
        model: str,
        max_tokens: int,
        system: str,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> Iterator[LLMStreamEvent]:
        request: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": self._to_openai_messages(system, messages),
            "stream": True,
        }
        if tools:
            request["tools"] = self._to_openai_tools(tools)
            request["tool_choice"] = "auto"

        accumulator = OpenAIStreamAccumulator()
        for chunk in self.client.chat.completions.create(**request):
            if not getattr(chunk, "choices", None):
                continue
            delta = chunk.choices[0].delta
            text = getattr(delta, "content", None)
            if text:
                accumulator.add_text(text)
                yield TextDeltaEvent(text=text)

            reasoning_content = self._get_reasoning_content(delta)
            if reasoning_content:
                accumulator.add_reasoning(reasoning_content)

            for tool_call_delta in getattr(delta, "tool_calls", None) or []:
                accumulator.add_tool_call_delta(tool_call_delta)

        yield FinalResponseEvent(response=accumulator.to_response())

    @staticmethod
    def _blocks_from_message(message: Any) -> list[TextBlock | ToolUseBlock | ReasoningBlock]:
        blocks: list[TextBlock | ToolUseBlock | ReasoningBlock] = []
        reasoning_content = OpenAICompatibleLLM._get_reasoning_content(message)
        if reasoning_content:
            blocks.append(ReasoningBlock(content=reasoning_content))
        if message.content:
            blocks.append(TextBlock(text=message.content))
        for tool_call in message.tool_calls or []:
            blocks.append(OpenAIStreamAccumulator.tool_call_to_block(tool_call.id, tool_call.function.name, tool_call.function.arguments or "{}"))
        return blocks

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


class OpenAIStreamAccumulator:
    def __init__(self) -> None:
        self.text_parts: list[str] = []
        self.reasoning_parts: list[str] = []
        self.tool_calls: dict[int, dict[str, str]] = {}

    def add_text(self, text: str) -> None:
        self.text_parts.append(text)

    def add_reasoning(self, text: str) -> None:
        self.reasoning_parts.append(text)

    def add_tool_call_delta(self, delta: Any) -> None:
        index = getattr(delta, "index", 0)
        current = self.tool_calls.setdefault(index, {"id": "", "name": "", "arguments": ""})
        if getattr(delta, "id", None):
            current["id"] = delta.id
        function = getattr(delta, "function", None)
        if function:
            if getattr(function, "name", None):
                current["name"] += function.name
            if getattr(function, "arguments", None):
                current["arguments"] += function.arguments

    def to_response(self) -> LLMResponse:
        blocks: list[TextBlock | ToolUseBlock | ReasoningBlock] = []
        reasoning = "".join(self.reasoning_parts)
        if reasoning:
            blocks.append(ReasoningBlock(content=reasoning))
        text = "".join(self.text_parts)
        if text:
            blocks.append(TextBlock(text=text))
        for _, tool_call in sorted(self.tool_calls.items()):
            blocks.append(self.tool_call_to_block(tool_call["id"], tool_call["name"], tool_call["arguments"]))
        return LLMResponse(content=blocks)

    @staticmethod
    def tool_call_to_block(tool_call_id: str, name: str, arguments: str) -> ToolUseBlock:
        try:
            tool_input = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            tool_input = {"raw_arguments": arguments}
        return ToolUseBlock(id=tool_call_id, name=name, input=tool_input)
