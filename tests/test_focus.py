from mini_agent.focus import ConversationFocus, FocusKind
from mini_agent.intent import Intent, classify_intent, tool_choice_guidance


def test_focus_tracks_content_generation_from_final_answer():
    focus = ConversationFocus()

    focus.update_after_final_answer(
        intent=classify_intent("直接给我"),
        user_input="直接给我",
        final_text="# 心动频率\n\n故事简介\n\n男主和五位女主的人物大纲。" * 20,
    )

    assert focus.kind == FocusKind.CONTENT


def test_focus_resolves_document_output_followup_from_content():
    focus = ConversationFocus(kind=FocusKind.CONTENT, topic="小说")
    current = classify_intent("直接输出为文档")

    decision = focus.resolve_followup("直接输出为文档", current)

    assert decision is not None
    assert decision.intent == Intent.CODING_TASK
    assert decision.allow_tools
    assert decision.hidden_tools == frozenset({"list_files", "read_file", "search_text"})
    assert "conversation focus" in decision.reason
    assert "relevant content already present in the conversation" in tool_choice_guidance(decision)


def test_focus_does_not_rewrite_document_output_without_content_focus():
    focus = ConversationFocus(kind=FocusKind.PROJECT, topic="project")
    current = classify_intent("直接输出为文档")

    assert focus.resolve_followup("直接输出为文档", current) is None
