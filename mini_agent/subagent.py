from __future__ import annotations

import contextlib
import io
from dataclasses import dataclass
from typing import Any

from .config import AgentConfig
from .intent import Intent, IntentDecision
from .llm import LLMClient
from .permissions import PermissionMode
from .runtime import AgentRuntime
from .tasks import TaskState
from .tool_core import Tool, build_tool
from .tool_registry import ToolRegistry


EXPLORE_PROMPT = """You are an Explore subagent for a Claude Code inspired learning agent.

Role:
- Search and read the workspace to answer the assigned question.
- Stay strictly read-only.
- Do not create, edit, delete, move, copy, or run commands that change state.
- Return your final answer using this structure:
  Findings:
  Relevant files:
  Open questions:
"""

PLAN_PROMPT = """You are a Plan subagent for a Claude Code inspired learning agent.

Role:
- Explore the workspace in read-only mode.
- Design an implementation plan, not the implementation itself.
- Do not create, edit, delete, move, copy, or run commands that change state.
- Return your final answer using this structure:
  Goal:
  Steps:
  Critical files:
  Risks:
"""

VERIFY_PROMPT = """You are a Verification subagent for a Claude Code inspired learning agent.

Role:
- Check whether an implementation, explanation, or plan is actually supported by the workspace.
- Try to find problems, missing tests, regressions, or unsupported assumptions.
- Stay strictly read-only.
- Do not create, edit, delete, move, copy, install packages, or run commands that change state.
- Prefer existing tests, read-only commands, file inspection, and evidence-based conclusions.
- Return your final answer using this structure:
  Result: passed | failed | inconclusive
  Checks:
  Evidence:
  Risks:
"""


@dataclass(frozen=True)
class AgentDefinition:
    agent_type: str
    description: str
    system_prompt: str
    max_turns: int = 6


EXPLORE_AGENT = AgentDefinition(
    agent_type="explore",
    description="Read-only workspace exploration subagent. Use it to inspect files, search code, and summarize findings without modifying anything.",
    system_prompt=EXPLORE_PROMPT,
)

PLAN_AGENT = AgentDefinition(
    agent_type="plan",
    description="Read-only planning subagent. Use it to inspect the project and produce an implementation plan before code changes.",
    system_prompt=PLAN_PROMPT,
)

VERIFY_AGENT = AgentDefinition(
    agent_type="verify",
    description="Read-only verification subagent. Use it to check whether work is correct, tested, and supported by evidence without modifying files.",
    system_prompt=VERIFY_PROMPT,
)


def build_subagent_tools(
    *,
    client: LLMClient,
    config: AgentConfig,
    tool_registry: ToolRegistry,
) -> dict[str, Tool]:
    return {
        "explore_agent": _build_subagent_tool(
            name="explore_agent",
            definition=EXPLORE_AGENT,
            client=client,
            config=config,
            tool_registry=tool_registry,
        ),
        "plan_agent": _build_subagent_tool(
            name="plan_agent",
            definition=PLAN_AGENT,
            client=client,
            config=config,
            tool_registry=tool_registry,
        ),
        "verify_agent": _build_subagent_tool(
            name="verify_agent",
            definition=VERIFY_AGENT,
            client=client,
            config=config,
            tool_registry=tool_registry,
        ),
    }


def run_subagent(
    *,
    definition: AgentDefinition,
    prompt: str,
    client: LLMClient,
    config: AgentConfig,
    tool_registry: ToolRegistry,
) -> str:
    sub_config = AgentConfig(
        workspace=config.workspace,
        provider=config.provider,
        model=config.model,
        fallback_model=config.fallback_model,
        base_url=config.base_url,
        max_turns=definition.max_turns,
        permission_mode=PermissionMode.PLAN,
        context_char_budget=config.context_char_budget,
    )
    runtime = AgentRuntime(
        client=client,
        config=sub_config,
        tools=tool_registry.read_only(),
        task_state=TaskState(),
        system_prompt=definition.system_prompt,
    )
    intent = IntentDecision(
        Intent.PROJECT_QUESTION,
        f"{definition.agent_type} subagent always uses its read-only tool set",
        allow_tools=True,
    )
    with contextlib.redirect_stdout(io.StringIO()):
        result = runtime.run_user_turn(prompt, intent_override=intent)
    return result or "(subagent completed without a final text response)"


def _build_subagent_tool(
    *,
    name: str,
    definition: AgentDefinition,
    client: LLMClient,
    config: AgentConfig,
    tool_registry: ToolRegistry,
) -> Tool:
    def call(args: dict[str, Any]) -> str:
        prompt = args["prompt"]
        return run_subagent(
            definition=definition,
            prompt=prompt,
            client=client,
            config=config,
            tool_registry=tool_registry,
        )

    return build_tool(
        name=name,
        description=definition.description,
        input_schema={
            "type": "object",
            "properties": {
                "prompt": {
                    "type": "string",
                    "description": "Focused task for the read-only subagent.",
                }
            },
            "required": ["prompt"],
        },
        call=call,
        read_only=lambda _input: True,
        concurrency_safe=lambda _input: False,
    )
