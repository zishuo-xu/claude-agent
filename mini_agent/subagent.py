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
- Do not delegate to other agents.
- Do not create, edit, delete, move, copy, or run commands that change state.
- Use at most 3 focused tool calls.
- After the third tool call, or earlier if you have enough evidence, stop using tools and return a final answer.
- If evidence is incomplete, state that in Open questions instead of continuing to search.
- Return your final answer using this structure:
  Findings:
  Relevant files:
  Open questions:
"""

PLAN_PROMPT = """You are a Plan subagent for a Claude Code inspired learning agent.

Role:
- Explore the workspace in read-only mode.
- Design an implementation plan, not the implementation itself.
- Do not delegate to other agents.
- Do not create, edit, delete, move, copy, or run commands that change state.
- Use at most 3 focused tool calls.
- After the third tool call, or earlier if you have enough evidence, stop using tools and return a final answer.
- If evidence is incomplete, state that in Risks instead of continuing to search.
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
- Do not delegate to other agents.
- Do not create, edit, delete, move, copy, install packages, or run commands that change state.
- Prefer existing tests, simple read-only commands, file inspection, and evidence-based conclusions.
- Do not use shell pipelines, redirection, cd, or chained shell commands.
- Use at most 3 focused tool calls.
- After the third tool call, or earlier if you have enough evidence, stop using tools and return a final answer.
- If evidence is incomplete, return Result: inconclusive instead of continuing to search.
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
    max_turns: int = 4


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

SUBAGENT_TOOL_NAMES = {"explore_agent", "plan_agent", "verify_agent"}
SUBAGENT_TASK_CHAR_BUDGET = 4_000
SUBAGENT_TRANSCRIPT_CHAR_BUDGET = 4_000
SUBAGENT_RESULT_CHAR_BUDGET = 4_000

SUBAGENT_CONTEXT_POLICY = """Subagent context policy:
- Treat the assigned task as the only task.
- Keep internal investigation local to this subagent.
- Return only the final structured summary to the main agent.
- Do not include raw long tool output unless it is essential evidence.
"""


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
    task_prompt = _trim_for_subagent(prompt, SUBAGENT_TASK_CHAR_BUDGET, label="assigned task")
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
        tools=_read_only_workspace_tools(tool_registry),
        task_state=TaskState(),
        system_prompt=_subagent_system_prompt(definition),
    )
    intent = IntentDecision(
        Intent.PROJECT_QUESTION,
        f"{definition.agent_type} subagent always uses its read-only tool set",
        allow_tools=True,
    )
    stdout = io.StringIO()
    with contextlib.redirect_stdout(stdout):
        result = runtime.run_user_turn(task_prompt, intent_override=intent)
    output = stdout.getvalue()
    return result or _finalize_subagent_result(
        definition=definition,
        prompt=task_prompt,
        output=output,
        client=client,
        config=sub_config,
    )


def _finalize_subagent_result(
    *,
    definition: AgentDefinition,
    prompt: str,
    output: str,
    client: LLMClient,
    config: AgentConfig,
) -> str:
    captured_output = _trim_for_subagent(
        output,
        SUBAGENT_TRANSCRIPT_CHAR_BUDGET,
        label="captured transcript",
        keep_tail=True,
    )
    fallback = _fallback_subagent_result(captured_output)
    try:
        response = client.complete(
            model=config.model,
            max_tokens=1024,
            system=(
                f"{definition.system_prompt}\n"
                "You are finalizing after the subagent reached its turn limit. "
                "Do not use tools. Produce the required final answer from the captured transcript. "
                "If evidence is incomplete, say so in the required structure."
            ),
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Original task:\n{prompt}\n\n"
                        f"Captured transcript:\n{captured_output}\n\n"
                        "Return the final structured answer now."
                    ),
                }
            ],
        )
    except Exception:
        return fallback

    text = "\n".join(block.text for block in response.content if getattr(block, "type", None) == "text").strip()
    return text or fallback


def _fallback_subagent_result(output: str) -> str:
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if not lines:
        evidence = "No captured output."
    else:
        evidence = "\n".join(lines[-8:])
        if len(evidence) > 800:
            evidence = evidence[-800:]
    return (
        "Result: inconclusive\n"
        "Reason: subagent reached its turn limit before a final answer.\n"
        f"Recent evidence:\n{evidence}"
    )


def _subagent_system_prompt(definition: AgentDefinition) -> str:
    return f"{definition.system_prompt}\n{SUBAGENT_CONTEXT_POLICY}"


def _trim_for_subagent(text: str, max_chars: int, *, label: str, keep_tail: bool = False) -> str:
    if len(text) <= max_chars:
        return text
    marker = f"\n...[truncated {label} from {len(text)} to {max_chars} chars]...\n"
    remaining = max_chars - len(marker)
    if remaining <= 0:
        return text[-max_chars:] if keep_tail else text[:max_chars]
    if keep_tail:
        return marker + text[-remaining:]
    return text[:remaining] + marker


def _read_only_workspace_tools(tool_registry: ToolRegistry) -> ToolRegistry:
    return ToolRegistry(
        {
            name: tool
            for name, tool in tool_registry.read_only().all().items()
            if name not in SUBAGENT_TOOL_NAMES
        }
    )


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
        max_result_chars=SUBAGENT_RESULT_CHAR_BUDGET,
        read_only=lambda _input: True,
        concurrency_safe=lambda _input: False,
    )
