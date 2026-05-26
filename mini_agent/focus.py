from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .intent import Intent, IntentDecision


class FocusKind(str, Enum):
    NONE = "none"
    PROJECT = "project"
    CONTENT = "content"
    CODING = "coding"
    GENERAL = "general"


DOCUMENT_OUTPUT_FOLLOWUPS = {
    "输出为文档",
    "整理成文档",
    "保存成文档",
    "写到文档",
    "生成文档",
}

CONTENT_MARKERS = {
    "小说",
    "故事",
    "大纲",
    "人物",
    "角色",
    "章节",
    "世界观",
    "男主",
    "女主",
    "故事简介",
}


@dataclass
class ConversationFocus:
    kind: FocusKind = FocusKind.NONE
    topic: str | None = None

    def resolve_followup(self, user_input: str, current: IntentDecision) -> IntentDecision | None:
        if current.intent == Intent.DANGEROUS_REQUEST or current.requested_tool:
            return None

        lowered = user_input.strip().lower()
        if any(marker in lowered for marker in DOCUMENT_OUTPUT_FOLLOWUPS) and self.kind == FocusKind.CONTENT:
            return IntentDecision(
                Intent.CODING_TASK,
                "document output follow-up from conversation focus",
                allow_tools=True,
                hidden_tools=frozenset({"list_files", "read_file", "search_text"}),
            )
        return None

    def update_after_final_answer(self, *, intent: IntentDecision | None, user_input: str, final_text: str) -> None:
        if not intent:
            return
        if intent.intent == Intent.PROJECT_QUESTION:
            self.kind = FocusKind.PROJECT
            self.topic = "project"
            return
        if intent.intent == Intent.CODING_TASK:
            self.kind = FocusKind.CODING
            self.topic = _topic_from_text(user_input, final_text)
            return
        if _looks_like_content_generation(user_input, final_text):
            self.kind = FocusKind.CONTENT
            self.topic = _topic_from_text(user_input, final_text)
            return
        if intent.intent == Intent.GENERAL_LEARNING:
            self.kind = FocusKind.GENERAL
            self.topic = None


def _looks_like_content_generation(user_input: str, final_text: str) -> bool:
    text = f"{user_input}\n{final_text}".lower()
    return len(final_text) >= 300 and any(marker in text for marker in CONTENT_MARKERS)


def _topic_from_text(user_input: str, final_text: str) -> str | None:
    text = f"{user_input}\n{final_text}"
    for marker in CONTENT_MARKERS:
        if marker in text:
            return marker
    return None
