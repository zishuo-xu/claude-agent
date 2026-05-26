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
    "创建",
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

FILE_GENERATION_KEYWORDS = {
    "保存为文件",
    "保持为文件",
    "写成文件",
    "生成文件",
    "输出到文件",
    "写入文件",
    "存成文件",
    "save to file",
    "write to file",
}

DOCUMENT_OUTPUT_KEYWORDS = {
    "输出为文档",
    "整理成文档",
    "保存成文档",
    "写到文档",
    "生成文档",
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

    if any(keyword in lowered for keyword in DOCUMENT_OUTPUT_KEYWORDS):
        return IntentDecision(
            Intent.CODING_TASK,
            "document output follow-up",
            allow_tools=True,
            hidden_tools=frozenset({"list_files", "read_file", "search_text"}),
        )

    if _looks_like_documented_project_question(lowered):
        return IntentDecision(
            Intent.PROJECT_QUESTION,
            "project question with clear documentation entrypoint",
            allow_tools=True,
            hidden_tools=frozenset({"list_files", "search_text"}),
        )

    if mentions_project:
        return IntentDecision(Intent.PROJECT_QUESTION, "project-specific question", allow_tools=True)

    if any(keyword in lowered for keyword in FILE_GENERATION_KEYWORDS):
        if not _has_file_path(lowered):
            return IntentDecision(Intent.CODING_TASK, "file generation task needs clarification", allow_tools=False)
        return IntentDecision(Intent.CODING_TASK, "file generation task", allow_tools=True)

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
    has_path = _has_file_path(text)
    has_content = any(keyword in text for keyword in ["内容", "content"])
    has_create_or_edit = any(keyword in text for keyword in ["创建", "新增", "写入", "生成", "create", "write", "add"])
    return has_path and has_content and has_create_or_edit


def _has_file_path(text: str) -> bool:
    return bool(re.search(r"[\w./-]+\.[a-z0-9_]+", text))


def _looks_like_documented_project_question(text: str) -> bool:
    return any(
        keyword in text
        for keyword in [
            "项目结构",
            "项目架构",
            "当前架构",
            "当前功能",
            "当前版本",
            "怎么启动",
            "如何启动",
            "启动方式",
            "下一步",
            "agent loop",
            "主循环",
            "对话循环",
            "roadmap",
            "architecture",
            "current features",
        ]
    )


def tool_choice_guidance(decision: IntentDecision) -> str:
    if decision.requested_tool:
        return f"Only use the explicitly requested tool: {decision.requested_tool}."

    guidance = {
        Intent.CASUAL_CHAT: "Reply briefly. Do not use tools. Do not describe project architecture unless asked.",
        Intent.GENERAL_LEARNING: (
            "Give a brief answer, then ask at most one clarifying question when useful. "
            "Keep the final answer to 3-5 short lines by default. Do not use tools or inspect the workspace. "
            "Do not use emoji, tables, or extra links unless the user asks for resources."
        ),
        Intent.PROJECT_QUESTION: (
            "Use the smallest useful read path. Choose the most relevant documentation entry first: "
            "architecture questions use docs/architecture.md; feature or version questions use "
            "docs/current-features.md; startup or usage questions use docs/current-features.md; "
            "next-step or roadmap questions use docs/roadmap.md; broad project overview questions use "
            "README.md or docs/context-map.md. Use list_files only when the "
            "target file is unclear, and stop using tools once enough context is available. Answer the user's "
            "specific question directly and concisely. Do not restate whole documents, long histories, or broad "
            "feature lists unless the user explicitly asks for detail. When the document states an explicit "
            "count or ordered list, preserve that count and list exactly; do not estimate counts. "
            "Keep the final answer to 3-6 short bullets "
            "or a short paragraph by default. Do not use emoji, tables, directory trees, or extra learning links "
            "unless the user asks for them. Always provide a visible final answer."
        ),
        Intent.CODING_TASK: (
            "You may use tools to inspect, edit, run tests, and verify changes. If tools are not available for "
            "a file generation request, ask for the missing file path, scope, or content constraints; do not "
            "invent a default file path or write the file yet. If this is a document output follow-up, use the "
            "relevant content already present in the conversation and write it as a Markdown document; if no path "
            "is provided, choose a concise safe filename from the topic or use output.md, and do not inspect "
            "project files. If the user gives an explicit "
            "file path and exact content, create or edit that file directly; do not call list_files first unless "
            "the target path is ambiguous or you need to discover existing files. If the user asks for very long "
            "generated content, create or update a file in batches instead of trying to produce everything in one "
            "response. Start with outline, metadata, or the first useful chunk, then explain how to continue."
        ),
        Intent.DANGEROUS_REQUEST: "Do not use tools. Explain the safety concern and ask for a safer, more specific goal.",
    }[decision.intent]
    return guidance


def intent_prompt(decision: IntentDecision) -> str:
    return (
        f"Current user intent: {decision.intent.value}. Reason: {decision.reason}. "
        f"Tool choice strategy: {tool_choice_guidance(decision)}"
    )
