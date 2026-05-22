from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class RuntimeEvent:
    type: str
    payload: dict[str, Any] = field(default_factory=dict)


EventHandler = Callable[[RuntimeEvent], None]
PermissionRequestHandler = Callable[[str, dict[str, Any], str], bool]


def print_runtime_event(event: RuntimeEvent) -> None:
    if event.type == "text_delta":
        print(event.payload.get("text", ""), end="", flush=True)
    elif event.type == "tool_start":
        print(f"\n\n[tool] {event.payload['name']} {event.payload['input']}")
    elif event.type == "tool_result":
        print(event.payload.get("content", ""))
    elif event.type == "permission_request":
        print(f"[permission] {event.payload['reason']}")
    elif event.type == "context_notice":
        print(f"\n[context] {event.payload['message']}\n")
    elif event.type == "model_fallback":
        print(f"\n[model] {event.payload['from_model']} failed; retrying with {event.payload['to_model']}\n")
    elif event.type == "final_answer":
        print()
    elif event.type == "stopped":
        print(f"\nStopped after {event.payload['max_turns']} turns.")


def prompt_permission_request(name: str, tool_input: dict[str, Any], _reason: str) -> bool:
    answer = input(f"Allow {name} {tool_input}? [y/N] ").strip().lower()
    return answer in {"y", "yes"}
