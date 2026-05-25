from __future__ import annotations

from dataclasses import dataclass

from .intent import Intent, IntentDecision, classify_intent


CLARIFICATION_MARKERS = {
    "请确认",
    "确认",
    "告诉我",
    "你希望",
    "你想",
    "需要",
    "文件名",
    "路径",
    "风格",
    "长度",
    "设定",
    "偏好",
    "which",
    "what",
    "where",
    "please provide",
}

CANCEL_MARKERS = {
    "算了",
    "不用了",
    "取消",
    "先不",
    "不要了",
    "cancel",
    "never mind",
}


@dataclass
class WorkingState:
    pending_intent: IntentDecision | None = None
    pending_goal: str | None = None
    waiting_for_user: bool = False

    def resolve_intent(self, user_input: str) -> IntentDecision:
        current = classify_intent(user_input)
        if not self.waiting_for_user or not self.pending_intent:
            return current
        if _is_cancel(user_input):
            self.clear()
            return current
        if _is_supplemental_response(user_input, current):
            pending = self.pending_intent
            return IntentDecision(
                intent=pending.intent,
                reason=f"{pending.reason}; continued from pending task",
                allow_tools=pending.allow_tools,
                requested_tool=pending.requested_tool,
                hidden_tools=pending.hidden_tools,
            )
        return current

    def mark_waiting(self, *, intent: IntentDecision, goal: str) -> None:
        if intent.intent != Intent.CODING_TASK:
            self.clear()
            return
        self.pending_intent = intent
        self.pending_goal = goal
        self.waiting_for_user = True

    def clear(self) -> None:
        self.pending_intent = None
        self.pending_goal = None
        self.waiting_for_user = False


def should_wait_for_user(intent: IntentDecision | None, final_text: str, used_tools: bool) -> bool:
    if used_tools or not intent or intent.intent != Intent.CODING_TASK:
        return False
    lowered = final_text.lower()
    has_question = "?" in final_text or "？" in final_text
    return has_question and any(marker in lowered for marker in CLARIFICATION_MARKERS)


def _is_cancel(user_input: str) -> bool:
    lowered = user_input.strip().lower()
    return any(marker in lowered for marker in CANCEL_MARKERS)


def _is_supplemental_response(user_input: str, current: IntentDecision) -> bool:
    if current.intent != Intent.CASUAL_CHAT or current.reason != "no project or coding action requested":
        return False
    text = user_input.strip()
    if not text:
        return False
    lowered = text.lower()
    if lowered in {"你好", "hi", "hello", "hey", "在吗"}:
        return False
    return True
