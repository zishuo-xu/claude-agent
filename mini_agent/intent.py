from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum


class Intent(str, Enum):
    CASUAL_CHAT = "casual_chat"
    GENERAL_LEARNING = "general_learning"
    PROJECT_QUESTION = "project_question"
    CODING_TASK = "coding_task"
    DANGEROUS_REQUEST = "dangerous_request"


@dataclass(frozen=True)
class IntentDecision:
    intent: Intent
    reason: str
    allow_tools: bool
    requested_tool: str | None = None
    hidden_tools: frozenset[str] = field(default_factory=frozenset)


CASUAL_PHRASES = {
    "hi",
    "hello",
    "hey",
    "你好",
    "在吗",
    "早上好",
    "晚上好",
}

LEARNING_KEYWORDS = {
    "学习",
    "学一下",
    "入门",
    "教程",
    "learn",
    "study",
}

PROJECT_KEYWORDS = {
    "这个项目",
    "当前项目",
    "本项目",
    "架构",
    "文档",
    "readme",
    "architecture",
    "current features",
    "roadmap",
}

AGENT_TOOL_NAMES = {
    "explore_agent",
    "plan_agent",
    "verify_agent",
}

BUILTIN_TOOL_NAMES = {
    "run_shell",
}

CODING_KEYWORDS = {
    "实现",
    "修改",
    "修复",
    "新增",
    "添加",
    "测试",
    "运行",
    "重构",
    "报错",
    "debug",
    "fix",
    "implement",
    "add",
    "test",
    "refactor",
}

DANGEROUS_KEYWORDS = {
    "删除所有",
    "清空",
    "rm -rf",
    "format",
    "wipe",
}


def classify_intent(user_input: str) -> IntentDecision:
    text = user_input.strip()
    lowered = text.lower()

    if not text:
        return IntentDecision(Intent.CASUAL_CHAT, "empty input", allow_tools=False)

    if lowered in CASUAL_PHRASES:
        return IntentDecision(Intent.CASUAL_CHAT, "greeting or casual chat", allow_tools=False)

    if any(keyword in lowered for keyword in DANGEROUS_KEYWORDS):
        return IntentDecision(Intent.DANGEROUS_REQUEST, "potentially destructive request", allow_tools=False)

    for tool_name in AGENT_TOOL_NAMES:
        if tool_name in lowered:
            return IntentDecision(
                Intent.PROJECT_QUESTION,
                "explicit subagent tool requested",
                allow_tools=True,
                requested_tool=tool_name,
            )

    for tool_name in BUILTIN_TOOL_NAMES:
        if tool_name in lowered:
            return IntentDecision(
                Intent.CODING_TASK,
                "explicit builtin tool requested",
                allow_tools=True,
                requested_tool=tool_name,
            )

    mentions_project = any(keyword in lowered for keyword in PROJECT_KEYWORDS)
    asks_to_use_project = any(phrase in lowered for phrase in ["用这个项目", "结合当前代码", "结合这个项目", "use this project"])

    if mentions_project:
        return IntentDecision(Intent.PROJECT_QUESTION, "project-specific question", allow_tools=True)

    if any(keyword in lowered for keyword in CODING_KEYWORDS):
        if _looks_like_direct_file_task(lowered):
            return IntentDecision(
                Intent.CODING_TASK,
                "direct file task with explicit path and content",
                allow_tools=True,
                hidden_tools=frozenset({"list_files"}),
            )
        return IntentDecision(Intent.CODING_TASK, "coding or project task", allow_tools=True)

    if any(keyword in lowered for keyword in LEARNING_KEYWORDS):
        if asks_to_use_project:
            return IntentDecision(Intent.PROJECT_QUESTION, "learning request tied to project", allow_tools=True)
        return IntentDecision(Intent.GENERAL_LEARNING, "general learning request", allow_tools=False)

    return IntentDecision(Intent.CASUAL_CHAT, "no project or coding action requested", allow_tools=False)


def _looks_like_direct_file_task(text: str) -> bool:
    has_path = bool(re.search(r"[\w./-]+\.[a-z0-9_]+", text))
    has_content = any(keyword in text for keyword in ["内容", "content"])
    has_create_or_edit = any(keyword in text for keyword in ["创建", "新增", "写入", "生成", "create", "write", "add"])
    return has_path and has_content and has_create_or_edit


def intent_prompt(decision: IntentDecision) -> str:
    guidance = {
        Intent.CASUAL_CHAT: "Reply briefly. Do not use tools. Do not describe project architecture unless asked.",
        Intent.GENERAL_LEARNING: "Give concise learning advice or ask about the user's level. Do not use tools or inspect the workspace.",
        Intent.PROJECT_QUESTION: (
            "Use the smallest useful read path. Prefer README.md, docs/context-map.md, docs/architecture.md, "
            "docs/current-features.md, and docs/roadmap.md before reading code. Use list_files only when the "
            "target file is unclear, and stop using tools once enough context is available. Answer the user's "
            "specific question directly and concisely. Do not restate whole documents, long histories, or broad "
            "feature lists unless the user explicitly asks for detail."
        ),
        Intent.CODING_TASK: (
            "You may use tools to inspect, edit, run tests, and verify changes. If the user gives an explicit "
            "file path and exact content, create or edit that file directly; do not call list_files first unless "
            "the target path is ambiguous or you need to discover existing files."
        ),
        Intent.DANGEROUS_REQUEST: "Do not use tools. Explain the safety concern and ask for a safer, more specific goal.",
    }[decision.intent]
    return f"Current user intent: {decision.intent.value}. Reason: {decision.reason}. Tool guidance: {guidance}"
