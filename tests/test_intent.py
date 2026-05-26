from mini_agent.intent import Intent, classify_intent, intent_prompt, tool_choice_guidance


def test_classifies_greeting_as_casual_without_tools():
    decision = classify_intent("你好")

    assert decision.intent == Intent.CASUAL_CHAT
    assert not decision.allow_tools


def test_classifies_general_learning_without_tools():
    decision = classify_intent("我想学习 Python")

    assert decision.intent == Intent.GENERAL_LEARNING
    assert not decision.allow_tools


def test_classifies_project_question_with_tools():
    decision = classify_intent("解释这个项目架构")

    assert decision.intent == Intent.PROJECT_QUESTION
    assert decision.allow_tools
    assert decision.requested_tool is None
    assert decision.hidden_tools == frozenset({"list_files", "search_text"})


def test_project_question_without_clear_doc_entrypoint_can_list_files():
    decision = classify_intent("看看这个项目")

    assert decision.intent == Intent.PROJECT_QUESTION
    assert decision.allow_tools
    assert decision.hidden_tools == frozenset()


def test_documented_project_question_without_project_word_uses_docs():
    decision = classify_intent("下一步应该做什么？")

    assert decision.intent == Intent.PROJECT_QUESTION
    assert decision.allow_tools
    assert decision.hidden_tools == frozenset({"list_files", "search_text"})


def test_startup_question_without_project_word_uses_current_features():
    decision = classify_intent("怎么启动？")

    assert decision.intent == Intent.PROJECT_QUESTION
    assert decision.allow_tools
    assert decision.hidden_tools == frozenset({"list_files", "search_text"})
    assert "docs/current-features.md" in tool_choice_guidance(decision)


def test_agent_loop_question_uses_project_docs():
    decision = classify_intent("现在的 Agent Loop 是怎么做的？")

    assert decision.intent == Intent.PROJECT_QUESTION
    assert decision.allow_tools
    assert decision.hidden_tools == frozenset({"list_files", "search_text"})


def test_classifies_explicit_subagent_request_with_tools():
    decision = classify_intent("用 explore_agent 找出 runtime 的职责")

    assert decision.intent == Intent.PROJECT_QUESTION
    assert decision.allow_tools
    assert decision.requested_tool == "explore_agent"


def test_classifies_explicit_builtin_tool_request_with_tools():
    decision = classify_intent("请调用 run_shell，command 为空字符串")

    assert decision.intent == Intent.CODING_TASK
    assert decision.allow_tools
    assert decision.requested_tool == "run_shell"


def test_classifies_coding_task_with_tools():
    decision = classify_intent("帮我修改代码并运行测试")

    assert decision.intent == Intent.CODING_TASK
    assert decision.allow_tools


def test_intent_prompt_includes_tool_guidance():
    decision = classify_intent("我想学习 Python")

    prompt = intent_prompt(decision)

    assert "general_learning" in prompt
    assert "Tool choice strategy" in prompt
    assert "Do not use tools" in prompt
    assert "3-5 short lines" in prompt
    assert "Do not use emoji" in prompt
    assert "unless the user asks for resources" in prompt


def test_project_question_tool_choice_guidance_names_doc_entrypoints():
    decision = classify_intent("当前架构上分为几层？")

    guidance = tool_choice_guidance(decision)

    assert "docs/architecture.md" in guidance
    assert "docs/current-features.md" in guidance
    assert "docs/roadmap.md" in guidance
    assert "Use list_files only when the target file is unclear" in guidance


def test_coding_task_prompt_avoids_listing_when_path_and_content_are_explicit():
    decision = classify_intent("创建 tmp_manual_test/hello.py，内容是打印 hello agent，然后运行它")

    prompt = intent_prompt(decision)

    assert decision.intent == Intent.CODING_TASK
    assert decision.hidden_tools == frozenset({"list_files"})
    assert "explicit file path and exact content" in prompt
    assert "do not call list_files first" in prompt


def test_classifies_create_file_with_content_as_coding_task():
    decision = classify_intent("创建 x.txt，内容是 x")

    assert decision.intent == Intent.CODING_TASK
    assert decision.allow_tools
    assert decision.hidden_tools == frozenset({"list_files"})


def test_classifies_save_as_file_request_as_coding_task():
    decision = classify_intent("可以，并且保持为文件，要求至少5个女主角")

    assert decision.intent == Intent.CODING_TASK
    assert not decision.allow_tools
    assert "needs clarification" in decision.reason


def test_classifies_save_as_file_request_with_path_as_tool_task():
    decision = classify_intent("保存为文件，文件名 novel.md，先写一小段")

    assert decision.intent == Intent.CODING_TASK
    assert decision.allow_tools


def test_classifies_document_output_followup_as_coding_task():
    decision = classify_intent("直接输出为文档")

    assert decision.intent == Intent.CODING_TASK
    assert decision.allow_tools
    assert decision.hidden_tools == frozenset({"list_files", "read_file", "search_text"})


def test_coding_task_prompt_guides_long_content_batches():
    decision = classify_intent("保存为文件，目标50w字，先写5w字")

    guidance = tool_choice_guidance(decision)

    assert "very long generated content" in guidance
    assert "in batches" in guidance


def test_coding_task_prompt_guides_document_output_from_conversation():
    decision = classify_intent("直接输出为文档")

    guidance = tool_choice_guidance(decision)

    assert "relevant content already present in the conversation" in guidance
    assert "do not inspect project files" in guidance


def test_create_keyword_without_file_path_does_not_hide_list_files():
    decision = classify_intent("创建一个简单的 Python 示例")

    assert decision.intent == Intent.CODING_TASK
    assert decision.allow_tools
    assert decision.hidden_tools == frozenset()
