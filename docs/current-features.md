# Current Features

这份文档记录项目当前已经具备的功能。它应该在每次新增、删除、修改功能后同步更新。

当前版本：`0.6.2`

## 运行方式

```bash
cd /Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent
.venv/bin/python agent.py --permission-mode plan
```

退出：

```text
/exit
```

## LLM Provider

当前支持：

- `openai-compatible`
- `anthropic`

当前本地 `.env` 使用 OpenAI-compatible `/v1` 服务，模型名为 `mimo-v2-omni`。

相关文件：

- `mini_agent/llm.py`
- `docs/01-llm-provider-adapter.md`

## 对话循环

已支持：

- 多轮消息历史
- 意图识别和工具使用门控
- 普通寒暄和闲聊应短回答，不主动展开项目架构
- 泛学习咨询应短回答或询问水平，不主动读取工作区或介绍本项目
- 模型返回工具调用
- 主模型调用支持流式文本输出
- 本地执行工具
- 工具结果回传模型
- 当前任务状态注入 system prompt
- 最大轮次限制
- 上下文 micro-compact
- full compact 摘要压缩兜底
- Explore / Plan / Verification 只读子 Agent

相关文件：

- `mini_agent/runtime.py`
- `mini_agent/subagent.py`
- `mini_agent/context.py`
- `mini_agent/intent.py`
- `mini_agent/tasks.py`
- `mini_agent/tool_registry.py`
- `mini_agent/tool_policy.py`

## 上下文管理

已支持：

- 当消息历史超过 `context_char_budget` 时触发上下文管理
- 先执行 micro-compact，清理旧工具结果
- micro-compact 默认保留最近 6 个可压缩工具结果
- 更早的可压缩工具结果会替换为短占位文本
- 普通用户消息和 assistant 文本不会被 micro-compact 清理
- 如果 micro-compact 后仍超过预算，再执行 full compact
- full compact 会让模型总结旧消息，并只保留最近 4 条原始消息

当前可压缩工具结果：

- `list_files`
- `read_file`
- `write_file`
- `edit_file`
- `preview_edit`
- `apply_edit`
- `search_text`
- `run_shell`

当前不压缩 task/todo 工具结果，因为它们承载当前任务状态，信息密度较高。

相关文件：

- `mini_agent/context.py`
- `mini_agent/runtime.py`
- `tests/test_context.py`
- `tests/test_runtime_intent.py`

## Explore / Plan / Verification 子 Agent

已支持：

- `AgentDefinition`: 描述内置子 Agent 的类型
- `EXPLORE_AGENT`: 只读探索角色
- `PLAN_AGENT`: 只读规划角色
- `VERIFY_AGENT`: 只读验证角色
- `explore_agent`: 主 Agent 可调用的 AgentTool 风格工具
- `plan_agent`: 主 Agent 可调用的 AgentTool 风格工具
- `verify_agent`: 主 Agent 可调用的 AgentTool 风格工具
- 子 Agent 使用独立 `AgentRuntime`
- 子 Agent 使用独立 `AgentState`
- 子 Agent 使用独立 `TaskState`
- 子 Agent 只暴露只读工具
- 子 Agent 内部工具调用历史不会进入主 Agent messages
- 主 Agent 只接收子 Agent 最终总结
- Verification 子 Agent 专门检查问题、缺失测试、回归和证据不足
- Explore 子 Agent 输出 `Findings / Relevant files / Open questions`
- Plan 子 Agent 输出 `Goal / Steps / Critical files / Risks`
- Verification 子 Agent 输出 `Result / Checks / Evidence / Risks`

当前简化：

- 不支持自定义 Agent markdown
- 不支持插件 Agent
- 不支持后台并行
- 不支持子 Agent 独立模型配置
- 不支持 worktree / remote 隔离
- Verification 当前不允许写临时测试脚本

相关文件：

- `mini_agent/subagent.py`
- `mini_agent/runtime.py`
- `mini_agent/tool_registry.py`
- `tests/test_subagent.py`

## 流式输出

已支持：

- LLM 适配层统一流式事件接口
- OpenAI-compatible provider 使用 streaming chat completions
- Runtime 边接收 `text_delta` 边打印
- 流式结束后仍返回统一 `LLMResponse`
- 工具调用仍在流结束后统一执行
- 会跳过 provider 返回的空 `choices` chunk，避免 usage/结束事件导致崩溃

当前简化：

- 暂不做“流中提前执行工具”
- Anthropic provider 当前用非流式 fallback 包装成流式事件

相关文件：

- `mini_agent/llm.py`
- `mini_agent/runtime.py`
- `tests/test_llm_adapter.py`
- `tests/test_runtime_intent.py`

## Task/Todo 状态

已支持：

- `TaskState`: 保存当前任务列表
- `TaskItem`: 单个任务
- `TaskStatus`: `todo`、`in_progress`、`done`、`blocked`
- Runtime 和工具系统共享同一个任务状态
- system prompt 每轮包含当前任务摘要

相关工具：

- `set_tasks`: 替换当前 todo 列表
- `update_task`: 更新单个任务状态和备注
- `list_tasks`: 查看当前任务状态

相关文件：

- `mini_agent/tasks.py`
- `mini_agent/runtime.py`
- `mini_agent/tools.py`
- `tests/test_tasks.py`

## 意图识别 / 工具使用门控

已支持 intent：

- `casual_chat`: 短回答，不暴露工具
- `general_learning`: 简洁建议或询问水平，不暴露工具
- `project_question`: 可以暴露读/搜索等项目工具
- `coding_task`: 可以进入工具循环
- `dangerous_request`: 不暴露工具，提示安全风险

当前实现是规则分类器，适合学习和测试。后续可以升级为更细的策略层。

相关文件：

- `mini_agent/intent.py`
- `mini_agent/runtime.py`
- `tests/test_intent.py`
- `tests/test_runtime_intent.py`

## 工具系统

已支持工具：

- `list_files`: 列出工作区内文件
- `read_file`: 读取 UTF-8 文本文件
- `write_file`: 写入文件
- `edit_file`: 替换已有文件中的文本，并返回 unified diff
- `preview_edit`: 预览文本替换 diff，不修改文件
- `apply_edit`: 应用文本替换，并返回实际 diff
- `search_text`: 使用 ripgrep 搜索文本
- `run_shell`: 在工作区运行 shell 命令
- `set_tasks`: 设置当前任务列表
- `update_task`: 更新任务状态
- `list_tasks`: 查看任务状态

已支持工具元信息：

- JSON schema
- 是否只读
- 是否可并发
- 是否危险
- 最大结果长度截断

`run_shell` 对常见只读命令有保守分类，例如 `pwd`、`ls`、`git status`。包含 `&&`、`;`、管道、重定向等组合操作的 shell 命令不会被自动视为只读。

`preview_edit` 是只读工具，适合在修改前查看 diff；`apply_edit` 会写文件，适合在确认修改后应用。

当前工具系统分层：

- `mini_agent/tool_core.py`: `Tool` 类型和 `build_tool()`
- `mini_agent/builtin_tools.py`: 内置工具实现和构造
- `mini_agent/tool_registry.py`: 工具注册、按名称查询、生成可暴露 schema
- `mini_agent/tool_policy.py`: 根据 intent 决定当前模型能看到哪些工具
- `mini_agent/tools.py`: 兼容旧入口，保留 `default_tools()`

这次分层不会改变工具行为，主要让后续新增 Git 工具、MCP 工具或多 agent 工具集时不用继续膨胀 runtime。

相关文件：

- `mini_agent/tools.py`
- `mini_agent/tool_core.py`
- `mini_agent/builtin_tools.py`
- `mini_agent/tool_registry.py`
- `mini_agent/tool_policy.py`

## 权限系统

已支持权限模式：

- `default`: 非只读操作需要确认
- `plan`: 只读操作自动允许，写操作确认
- `acceptEdits`: 文件编辑自动允许，其他风险操作确认
- `bypassPermissions`: 跳过大部分权限检查，但 deny 规则仍优先
- `dontAsk`: 需要确认的操作直接拒绝

已支持权限规则：

- `allow`
- `deny`
- `ask`
- 工具级规则，例如 `read_file`
- 内容匹配规则，例如 `run_shell(git status*)`
- `preview_edit` 默认可作为只读预览；`apply_edit` 默认进入确认流程

相关文件：

- `mini_agent/permissions.py`
- `mini_agent/settings.py`
- `agent_settings.example.json`

## 工作区安全

已支持：

- 文件路径限制在当前 workspace
- 阻止 `../` 逃逸
- shell 命令基础危险片段拦截

相关文件：

- `mini_agent/workspace.py`
- `mini_agent/tools.py`

## Reasoning 续传

OpenAI-compatible provider 如果返回 `reasoning_content`，项目会保存为内部 `ReasoningBlock`，并在下一轮请求中传回 provider。

这个功能用于支持 thinking/reasoning 模式的工具调用。

相关文件：

- `mini_agent/llm.py`
- `tests/test_llm_adapter.py`
- `docs/01-llm-provider-adapter.md`

## 测试

当前测试覆盖：

- 权限规则和权限模式
- intent 分类和 runtime 工具过滤
- shell 只读命令分类
- diff/patch 工具行为
- tool registry 和 tool policy 边界
- 上下文 micro-compact
- full compact 兜底
- Explore / Plan / Verification 只读子 Agent
- 子 Agent 输出结构化 prompt contract
- task/todo 状态和工具共享状态
- streaming text delta 和最终响应重建
- system prompt 的泛学习请求约束
- 工作区路径边界
- LLM provider 适配层转换
- `reasoning_content` 续传

运行：

```bash
.venv/bin/python -m pytest
```

当前测试数量：

```text
44 tests
```

相关文件：

- `tests/test_permissions.py`
- `tests/test_workspace.py`
- `tests/test_llm_adapter.py`
- `tests/test_tool_registry.py`
- `tests/test_context.py`
- `tests/test_subagent.py`

## 文档体系

当前长期文档：

- `README.md`: 项目入口、运行、测试、学习路线
- `PROJECT_PRINCIPLES.md`: 项目原则和工作流
- `docs/architecture.md`: 当前架构
- `docs/current-features.md`: 当前功能
- `docs/roadmap.md`: 下一步工作和优先级
- `docs/versioning.md`: 版本规则和学习阶段
- `docs/learning-qa.md`: 技术疑问和解答沉淀
- `docs/01-llm-provider-adapter.md`: LLM provider 适配专题
- `CHANGELOG.md`: 版本变化记录

## 版本归档

当前版本 `0.6.2` 已按特性级别归档：

- 小特性：子 Agent 输出结构化
- 架构：不新增模块，只补 prompt contract
- 文档与测试：changelog、当前功能、44 个测试

详细记录见 `CHANGELOG.md`。

## 推荐下一步

当前建议保持简洁，暂停继续堆功能。后续候选方向见 `docs/roadmap.md`。
