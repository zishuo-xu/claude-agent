#!/usr/bin/env python3
"""CLI entry point for the learning agent."""

from __future__ import annotations

import argparse
import os
import select
import sys
from pathlib import Path

from mini_agent.config import AgentConfig, load_dotenv
from mini_agent.events import print_runtime_event
from mini_agent.llm import AnthropicLLM, LLMClient, OpenAICompatibleLLM
from mini_agent.permissions import PermissionMode
from mini_agent.runtime import AgentRuntime
from mini_agent.settings import load_permission_rules
from mini_agent.subagent import build_subagent_tools
from mini_agent.tasks import TaskState
from mini_agent.tool_registry import ToolRegistry


ROOT = Path.cwd().resolve()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Claude Code inspired learning agent.")
    parser.add_argument("--provider", choices=["anthropic", "openai-compatible"], default=os.environ.get("LLM_PROVIDER"))
    parser.add_argument("--base-url", default=os.environ.get("LLM_BASE_URL"))
    parser.add_argument("--model", default=os.environ.get("LLM_MODEL_NAME") or os.environ.get("ANTHROPIC_MODEL"))
    parser.add_argument("--fallback-model", default=os.environ.get("LLM_FALLBACK_MODEL") or os.environ.get("ANTHROPIC_FALLBACK_MODEL"))
    parser.add_argument("--max-turns", type=int, default=12)
    parser.add_argument(
        "--permission-mode",
        choices=[mode.value for mode in PermissionMode],
        default=os.environ.get("AGENT_PERMISSION_MODE", PermissionMode.DEFAULT.value),
    )
    parser.add_argument("--context-char-budget", type=int, default=80_000)
    return parser.parse_args()


def make_llm_client(provider: str, base_url: str | None) -> LLMClient:
    if provider == "openai-compatible":
        api_key = os.environ.get("LLM_API_KEY")
        if not api_key:
            raise RuntimeError("Missing LLM_API_KEY for openai-compatible provider.")
        if not base_url:
            raise RuntimeError("Missing LLM_BASE_URL for openai-compatible provider.")
        return OpenAICompatibleLLM(api_key=api_key, base_url=base_url)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise RuntimeError("Missing ANTHROPIC_API_KEY for anthropic provider.")
    return AnthropicLLM()


def read_user_input(prompt: str = "\n你 > ") -> str:
    first_line = input(prompt)
    return _join_input_lines(first_line, _drain_pending_stdin())


def _join_input_lines(first_line: str, extra_lines: list[str]) -> str:
    lines = [first_line, *extra_lines]
    return "\n".join(line.rstrip("\n") for line in lines).strip()


def _drain_pending_stdin() -> list[str]:
    if not sys.stdin.isatty():
        return []
    lines: list[str] = []
    while True:
        try:
            ready, _, _ = select.select([sys.stdin], [], [], 0.02)
        except (OSError, ValueError):
            return lines
        if not ready:
            return lines
        line = sys.stdin.readline()
        if not line:
            return lines
        lines.append(line)


def format_cli_error(exc: Exception) -> str:
    return f"[error] {type(exc).__name__}: {exc}"


def main() -> int:
    load_dotenv(ROOT / ".env")
    args = parse_args()

    provider = args.provider or ("openai-compatible" if os.environ.get("LLM_BASE_URL") else "anthropic")
    model = args.model or ("claude-sonnet-4-20250514" if provider == "anthropic" else None)
    if not model:
        print("Missing model. Set LLM_MODEL_NAME or pass --model.", file=sys.stderr)
        return 2
    try:
        client = make_llm_client(provider, args.base_url)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2

    config = AgentConfig(
        workspace=ROOT,
        provider=provider,
        model=model,
        fallback_model=args.fallback_model,
        base_url=args.base_url,
        max_turns=args.max_turns,
        permission_mode=PermissionMode(args.permission_mode),
        context_char_budget=args.context_char_budget,
    )
    task_state = TaskState()
    tool_registry = ToolRegistry.with_builtin_tools(ROOT, task_state)
    subagent_base_registry = ToolRegistry(dict(tool_registry.all()))
    for tool in build_subagent_tools(client=client, config=config, tool_registry=subagent_base_registry).values():
        tool_registry.register(tool)
    runtime = AgentRuntime(
        client=client,
        config=config,
        tools=tool_registry,
        task_state=task_state,
        permission_rules=load_permission_rules(ROOT / "agent_settings.json"),
        event_handler=print_runtime_event,
    )

    print(f"Claude-style learning agent ({provider}, {model}). Type /exit to quit, /mode to see permission mode.")
    while True:
        try:
            user_input = read_user_input()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0

        if user_input in {"/exit", "/quit"}:
            return 0
        if user_input == "/mode":
            print(f"permission mode: {runtime.config.permission_mode.value}")
            continue
        if not user_input:
            continue

        print("\nagent > ", end="", flush=True)
        try:
            runtime.run_user_turn(user_input)
        except Exception as exc:
            print(f"\n{format_cli_error(exc)}")


if __name__ == "__main__":
    raise SystemExit(main())
