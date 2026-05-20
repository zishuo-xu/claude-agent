# Changelog

本文件记录项目版本变化。

## 0.6.3 - 2026-05-21

当前学习阶段：工具输入验证层。

变更级别：小特性版本。

### Minor Features

- `Tool` 新增可选 `validate_input`
- Runtime 在权限判断前先执行工具输入校验
- `run_shell` 会拒绝空命令，并返回清晰错误

这是对 Claude `Tool.validateInput()` 思想的轻量实现。当前只补最小边界，不引入复杂 schema 校验框架。

### Fixes / Behavior Adjustments

- system prompt 明确要求使用真实 tool call，不要把 XML/JSON 伪工具调用当文本输出
- Runtime 可识别模型输出的 XML/JSON 简单伪工具调用，并转换为内部 `tool_use`
- 流式输出会抑制这类伪工具调用文本，避免直接展示给用户
- 当 provider 只在 stream delta 中返回文本、最终响应为空时，Runtime 会用累计文本补回最终响应
- 意图识别会把显式 `explore_agent` / `plan_agent` / `verify_agent` 请求归为可用工具的项目问题
- 显式子 Agent 请求只暴露被点名的子 Agent 工具，避免主 Agent 抢先使用文件工具
- 子 Agent 如果没有返回最终文本，会把捕获到的输出作为兜底结果返回给主 Agent
- 子 Agent prompt 明确最多 3 次工具调用后必须返回最终总结
- 子 Agent 默认 `max_turns` 调整为 4，对应 3 次工具调用加 1 次最终回答
- 子 Agent 到达轮次上限时，会追加一次无工具 finalization，把捕获 transcript 压成结构化最终答案
- 显式子 Agent 请求在目标工具执行一次后会关闭工具暴露，避免主 Agent 反复调用同一个子 Agent
- `list_files` 默认隐藏 `.env`、`.venv`、`__pycache__` 等常见噪音，可用 `include_hidden=true` 查看
- Verification 子 Agent prompt 明确避免 shell 管道、重定向、`cd` 和链式命令

### Tests

- 新增空 shell 命令校验测试
- 新增 runtime 在权限前拦截无效工具输入的测试
- 新增子 Agent stream-only 文本返回测试
- 新增伪工具调用识别和流式抑制测试
- 新增 stream delta 文本补回最终响应测试
- 新增显式子 Agent 请求的 intent 分类测试
- 新增显式子 Agent 请求只暴露目标工具的测试
- 新增子 Agent 工具调用预算和轮次限制测试
- 新增子 Agent 到达轮次上限后的 finalization 测试
- 新增显式子 Agent 工具只执行一次的 runtime 测试
- 新增 `list_files` 默认隐藏噪音和显式显示隐藏项测试
- 新增 system prompt 真实工具调用约束测试

### Verified

- `59 passed`

## 0.6.2 - 2026-05-20

当前学习阶段：子 Agent 输出结构化。

变更级别：小特性版本。

### Minor Features

- Explore 子 Agent 输出 `Findings / Relevant files / Open questions`
- Plan 子 Agent 输出 `Goal / Steps / Critical files / Risks`
- Verification 子 Agent 输出 `Result / Checks / Evidence / Risks`

这是一个很小的 prompt contract 迭代，不新增模块，不解析 JSON，不引入复杂结构，只让现有子 Agent 的最终汇报更稳定。

### Tests

- 扩展子 Agent prompt 测试，确保三个内置子 Agent 都包含结构化输出约束

### Verified

- `44 passed`

## 0.6.1 - 2026-05-20

当前学习阶段：Verification 只读验证子 Agent。

变更级别：小特性版本。

### Minor Features

- 新增 `VERIFY_AGENT`
- 新增 `verify_agent` AgentTool 风格工具
- Verification 子 Agent 复用独立 `AgentRuntime`
- Verification 子 Agent 只暴露只读工具
- Verification prompt 明确要求检查问题、缺失测试、回归和不充分证据
- Verification prompt 明确禁止创建、编辑、删除、移动、复制文件或安装依赖
- Verification 结果要求以 `passed`、`failed` 或 `inconclusive` 结论收尾

这些属于小特性，因为它复用 `0.6.0` 已建立的 AgentTool / 子 Agent 架构，只新增一个内置角色。

### Claude Alignment

- 对应 Claude Code 的 Verification Agent 设计思想
- 保持“验证者只检查，不修改项目”的角色隔离
- 简化点：当前不允许写临时测试脚本，也不做浏览器/UI 验证流程编排

### Tests

- 扩展子 Agent 测试：
  - `verify_agent` 注册为只读工具
  - Verification 子 Agent 使用专属 prompt
  - prompt 包含验证结论格式和禁止修改约束

### Verified

- `43 passed`

## 0.6.0 - 2026-05-20

当前学习阶段：Explore / Plan 只读子 Agent。

变更级别：大特性版本。

### Major Features

- 新增 `mini_agent.subagent`
- 新增 `AgentDefinition`，用于描述内置子 Agent
- 新增 `EXPLORE_AGENT` 和 `PLAN_AGENT`
- 新增 `explore_agent` / `plan_agent` 两个 AgentTool 风格工具
- 子 Agent 使用独立 `AgentRuntime` 和独立 `AgentState`
- 子 Agent 只暴露只读工具集
- 主 Agent 只接收子 Agent 最终总结，不接收子 Agent 内部工具历史

这些属于大特性，因为它们让项目从单 Agent 主循环进入“主 Agent + 角色化子 Agent”的 Claude Code 架构层，学习重点从工具调用扩展到上下文隔离和角色隔离。

### Claude Alignment

- 对应 Claude Code 的 `AgentTool`
- 对应内置 Agent 设计中的 Explore / Plan 角色
- 简化点：
  - 不支持自定义 markdown Agent
  - 不支持插件 Agent
  - 不支持后台并行
  - 不支持独立模型选择
  - 不支持 worktree / remote 隔离

### Tests

- 新增子 Agent 测试：
  - `explore_agent` / `plan_agent` 注册为只读工具
  - 子 Agent 只接收只读工具
  - 子 Agent 使用专属 system prompt

### Verified

- `42 passed`

## 0.5.0 - 2026-05-20

当前学习阶段：上下文 micro-compact。

变更级别：大特性版本。

### Major Features

- 新增 `mini_agent.context` 上下文管理模块
- 新增 `micro_compact_messages()`，用于清理旧的可压缩工具结果
- 新增 `count_message_chars()`，统一 runtime 的上下文字符预算统计
- `AgentRuntime._compact_if_needed()` 现在会先尝试 micro-compact
- 如果 micro-compact 后仍超过预算，继续使用原来的 full compact 总结兜底

这些属于大特性，因为它们改变了上下文压缩主路径，让项目从“只会等上下文过大后做总结”升级为“先轻量清理旧工具结果，再必要时总结旧历史”。

### Context Behavior

- 默认保留最近 6 个可压缩工具结果
- 更早的 `read_file`、`search_text`、`run_shell`、diff/编辑等工具结果会被替换成短占位文本
- 普通用户消息和 assistant 文本不会被 micro-compact 清理
- `set_tasks`、`update_task`、`list_tasks` 等任务状态工具结果暂不清理

### Tests

- 新增 micro-compact 单元测试：
  - 旧工具结果会被清理
  - 最近工具结果会保留
  - 普通用户文本和 assistant 文本不被误清理
  - 非压缩工具结果不被清理
- 新增 runtime 集成测试：
  - micro-compact 足够降到预算内时不会触发 full compact
  - micro-compact 不足时 full compact 仍会触发

### Verified

- `39 passed`

## 0.4.2 - 2026-05-20

当前学习阶段：工具系统架构整理。

变更级别：小特性 / 架构整理版本。

### Minor Features

- 新增 `mini_agent.tool_core`，集中保存 `Tool` 和 `build_tool()`
- 新增 `mini_agent.builtin_tools`，集中构造内置工具
- 新增 `mini_agent.tool_registry`，统一管理工具注册、查询和可暴露 schema
- 新增 `mini_agent.tool_policy`，承载按 intent 过滤工具的策略边界
- `AgentRuntime` 改为通过 `ToolRegistry` 获取当前可用工具 schema

这些属于小特性，因为它们主要整理现有工具系统边界，行为保持不变，但为后续 Git 专用工具、MCP 工具注册和多 agent 工具集打基础。

### Compatibility

- `mini_agent.tools.default_tools()` 继续保留，作为旧测试和简单调用方的兼容入口
- 现有内置工具名称、权限元信息和执行行为保持不变

### Tests

- 新增 `ToolRegistry` 测试：
  - 项目问题会暴露内置工具
  - 泛学习请求会隐藏工具

### Verified

- `34 passed`

## 0.4.1 - 2026-05-20

当前学习阶段：流式输出稳定性修复。

变更级别：bug fix 版本。

### Fixes

- 修复 OpenAI-compatible streaming 在收到空 `choices` chunk 时崩溃的问题
- 这类 chunk 常见于 usage、统计或流结束事件，应该跳过而不是访问 `choices[0]`

### Tests

- 新增回归测试，模拟 provider 先返回文本 chunk，再返回空 `choices` chunk

### Verified

- `32 passed`

## 0.4.0 - 2026-05-20

当前学习阶段：流式输出。

变更级别：大特性版本。

### Major Features

- 新增 LLM 流式事件接口
- Runtime 主模型调用改为流式消费文本增量
- OpenAI-compatible provider 支持 `/chat/completions` streaming
- 流式结束后仍返回统一 `LLMResponse`，继续兼容工具调用循环

这些属于大特性，因为它们改变了模型调用主路径，让 agent 从“等待完整响应”升级为“边接收边输出”的交互模式。

### Provider Behavior

- OpenAI-compatible streaming 会累积：
  - text delta
  - reasoning content
  - tool call delta
- Anthropic provider 当前使用非流式 fallback 包装成流式事件，保持接口一致。

### Tests

- 新增 stream accumulator 测试
- 新增 runtime streaming 调用测试

### Verified

- `31 passed`

## 0.3.0 - 2026-05-20

当前学习阶段：Task/Todo 状态管理。

变更级别：大特性版本。

### Major Features

- 新增 `mini_agent.tasks` 核心状态模块
- 新增 `TaskState`，用于保存当前任务列表
- 新增 `TaskItem` 和 `TaskStatus`
- Runtime 持有共享 `TaskState`
- System prompt 每轮注入当前任务状态
- 工具系统和 runtime 共享同一个任务状态

这些属于大特性，因为它们引入了新的核心状态模块，让 agent 从“单轮工具执行”升级到“能跟踪多步骤任务进度”。

### Tools

- 新增 `set_tasks`：替换当前 todo 列表
- 新增 `update_task`：更新单个任务状态和备注
- 新增 `list_tasks`：读取当前任务状态

### Tests

- 新增任务状态测试：
  - 设置任务列表
  - 更新任务状态和备注
  - 拒绝未知任务 id
  - prompt summary
  - 工具共享同一个 `TaskState`
  - runtime prompt 注入任务状态

### Verified

- `29 passed`

## 0.2.1 - 2026-05-20

当前学习阶段：安全可学习的 Claude-style agent 骨架。

变更级别：小特性版本。

### Minor Features

- 新增 `preview_edit` 工具，只生成 unified diff，不修改文件
- 新增 `apply_edit` 工具，应用文本替换并返回实际 diff
- `edit_file` 现在会返回修改 diff，减少黑盒文件修改
- 新增 `unified_diff()` 辅助函数
- 新增 `replace_text()` 辅助函数，统一文本替换校验
- 权限示例中允许 `preview_edit`，并让 `apply_edit` 进入确认流程

这些属于小特性，因为它们增强现有工具系统的编辑体验，但没有引入新的核心模块，也没有改变 agent 的主循环学习阶段。

### Tests

- 新增 diff/patch 工具测试：
  - `preview_edit` 返回 diff 且不修改文件
  - `apply_edit` 返回 diff 且修改文件
  - `preview_edit` 是只读工具，`apply_edit` 不是只读工具

### Verified

- `23 passed`

## 0.2.0 - 2026-05-20

当前学习阶段：安全可学习的 Claude-style agent 骨架。

变更级别：大特性版本。

### Major Features

- LLM provider 适配层，支持 Anthropic 和 OpenAI-compatible `/v1`
- 工具系统：`Tool`、`build_tool()`、工具 schema、结果截断
- 权限系统：`default`、`plan`、`acceptEdits`、`bypassPermissions`、`dontAsk`
- 工作区路径边界，阻止文件工具逃逸 workspace
- 意图识别 / 工具使用门控

这些属于大特性，因为它们引入或改变了 agent 的核心模块和主流程。

### Minor Features

- OpenAI-compatible `reasoning_content` 续传
- 内置工具：`list_files`、`read_file`、`write_file`、`edit_file`、`search_text`、`run_shell`
- 权限规则：`allow`、`deny`、`ask`
- shell 只读命令保守分类
- 简单上下文摘要压缩
- fallback model 配置

这些属于小特性，因为它们增强现有模块能力，但不单独构成新的学习阶段。

### Fixes / Behavior Adjustments

- 普通寒暄默认短回答，不主动输出项目架构
- 泛学习请求默认不读取工作区，不主动介绍本项目
- `run_shell("pwd")` 等只读命令在 `plan` 模式不再错误触发写操作确认
- Q&A 文档仅记录技术疑问和解答

### Documentation

- 长期文档体系：
  - `PROJECT_PRINCIPLES.md`
  - `docs/architecture.md`
  - `docs/current-features.md`
  - `docs/roadmap.md`
  - `docs/learning-qa.md`
  - `docs/01-llm-provider-adapter.md`
  - `docs/versioning.md`
- 版本管理文件：
  - `VERSION`
  - `CHANGELOG.md`

### Tests

- 测试套件覆盖：
  - intent 分类和 runtime 工具过滤
  - LLM provider 适配层转换
  - `reasoning_content` 续传
  - 权限规则和权限模式
  - shell 只读命令分类
  - 工作区路径边界

### Verified

- `20 passed`

## 0.1.0 - 2026-05-20

当前学习阶段：最小 Claude-style agent 闭环。

变更级别：大特性版本。

### Added

- 最小对话循环
- Anthropic Messages API 工具调用
- 基础工具：列目录、读文件、写文件、运行 shell
- 初始 README
