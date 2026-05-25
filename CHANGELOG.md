# Changelog

本文件记录项目版本变化。

## Unreleased

### Documentation

- 统一项目定位为 `mini-claude`
- 明确目标是轻量级工程化 Claude-style agent，不是玩具 demo，也不是完整 Claude Code 复刻
- 将 `docs/learning-qa.md` 定位为独立学习沉淀文档，默认不参与日常上下文加载

## 0.24.0 - 2026-05-25

当前学习阶段：Working State For Pending Task / 短期任务意图延续。

变更级别：小特性。

### Added

- 新增 `mini_agent/working_state.py`，保存当前 runtime 内的单个 pending task
- Runtime 使用 `WorkingState.resolve_intent()`，让澄清问题后的用户补充可以继承上一轮 coding task
- 新增创作型文件任务识别：“保存为文件 / 保持为文件 / 写成文件 / 输出到文件”等表达进入 coding task
- coding task guidance 增加超长内容分批写入文件策略

### Changed

- 工具执行时会清空 pending task，避免任务完成后错误继承
- 用户取消时会清空 pending task

### Review

- 这是 Claude-style agent loop 的轻量工作状态边界，不是长期记忆系统
- 不做 session resume、多任务队列、planner 或专用小说生成器

### Verified

- pending task 针对性测试 passed
- `155 passed`
- 文档测试 passed

### Next

- 下一步建议 `0.24.1 Pending Task Acceptance / 短期任务延续验收`

## 0.23.0 - 2026-05-25

当前学习阶段：Subagent Context Policy / 子 Agent 上下文策略。

变更级别：小特性。

### Changed

- 新增子 Agent 上下文策略提示，明确内部探索留在子 Agent，只把最终结构化摘要返回主 Agent
- 新增 `SUBAGENT_TASK_CHAR_BUDGET`，对子任务输入做轻量截断，避免主 Agent 把过长上下文直接塞给子 Agent
- 新增 `SUBAGENT_TRANSCRIPT_CHAR_BUDGET`，对子 Agent 超限后的 captured transcript 做截断，再交给 finalizer 总结
- 新增 `SUBAGENT_RESULT_CHAR_BUDGET`，对子 Agent 工具返回做较小预算，避免最终摘要污染主上下文
- 新增测试覆盖 oversized assigned task、trimmed finalizer transcript 和 compact subagent tool result budget

### Review

- 保持固定 `explore_agent`、`plan_agent`、`verify_agent` 三个只读角色
- 不新增自定义 agent、后台并行、独立模型、worktree 隔离或子 Agent 间通信

### Verified

- `tests/test_subagent.py` passed
- `151 passed`
- 文档测试 passed

### Next

- 下一步建议 `0.23.1 Subagent Context Acceptance / 子 Agent 上下文验收`

## 0.22.1 - 2026-05-25

当前学习阶段：Context Budget Acceptance / 上下文预算验收。

变更级别：复查版本。

### Review

- 复查上下文相关测试，确认旧工具结果清理、最近工具结果保留、错误结果保留、task 工具结果保留和孤立 tool_result 保留
- 复查 runtime 压缩测试，确认 micro-compact 先于 full compact、summary 注入、summary 和 TaskState 分离、真实长任务关键上下文保留
- 确认上下文预算主线当前够用，暂不新增 token 精确预算、长期记忆、向量库或 session resume

### Verified

- `tests/test_context.py tests/test_runtime_intent.py -k 'compact or summary or context'` passed
- `148 passed`

### Next

- 下一条主线转向 `0.23.0 Subagent Context Policy / 子 Agent 上下文策略`

## 0.22.0 - 2026-05-25

当前学习阶段：Context Budget Policy / 上下文预算策略。

变更级别：小特性。

### Changed

- 新增 `DEFAULT_KEEP_RECENT_TOOL_RESULTS`，明确 micro-compact 默认保留最近 6 个可压缩工具结果
- 为 `COMPACTABLE_TOOL_NAMES` 增加策略说明，强调只压缩高噪音成功工具输出
- 新增测试固定 task/todo 工具不在默认可压缩集合中
- 同步文档，明确上下文预算顺序：tool result budget -> micro-compact -> full compact -> summary / TaskState 注入

### Review

- 保持现有 compact 流程，不引入 token 精确预算、向量库、长期记忆或 session resume
- 继续保持 summary 和 TaskState 分离：summary 保存历史上下文，TaskState 保存当前任务进度

### Verified

- `tests/test_context.py tests/test_runtime_intent.py -k 'compact or summary or context'` passed
- `148 passed`

## 0.21.1 - 2026-05-25

当前学习阶段：LLM Adapter Acceptance / 模型适配验收。

变更级别：复查版本。

### Review

- 复查现有 `tests/test_llm_adapter.py` 覆盖消息转换、工具调用、工具结果、reasoning 续传、streaming 空 `choices` 和无效工具参数降级
- 手动模拟 OpenAI-compatible streaming 同时包含 text、reasoning、tool_call 和空 `choices`
- 确认最终内部 blocks 能重建为 `ReasoningBlock`、`TextBlock` 和 `ToolUseBlock`
- 确认 LLM Adapter 主线当前够用，暂不新增 provider 框架、多模型路由或复杂 retry/backoff

### Verified

- `tests/test_llm_adapter.py` passed
- streaming 模拟验收通过

### Next

- 下一条主线转向 `0.22.0 Context Budget Policy / 上下文预算策略`

## 0.21.0 - 2026-05-25

当前学习阶段：LLM Adapter Protocol Review / 模型适配协议复查。

变更级别：小特性。

### Changed

- 补充 OpenAI-compatible `model_extra.reasoning_content` 转内部 `ReasoningBlock` 的协议测试
- 补充无效 JSON 工具参数降级为 `raw_arguments` 的协议测试
- 更新 LLM Adapter 文档，明确当前已支持 `stream_complete()`、streaming event、`ReasoningBlock` 和空 `choices` chunk 跳过
- 修正 LLM Adapter 文档中过期的“未实现 streaming”描述

### Review

- 当前 `llm.py` 职责仍清楚，暂不拆文件
- 暂不新增 provider、provider 能力探测、多模型路由或复杂 retry/backoff

### Verified

- `tests/test_llm_adapter.py` passed
- `147 passed`

## 0.20.1 - 2026-05-25

当前学习阶段：Tool Choice Acceptance / 工具选择验收。

变更级别：复查版本。

### Review

- 真实 CLI 验收泛学习请求：未调用工具
- 真实 CLI 验收“怎么启动”：直接读取 `docs/current-features.md`
- 真实 CLI 验收“当前架构上分为几层”：直接读取 `docs/architecture.md`
- 真实 CLI 验收“当前功能有哪些”：直接读取 `docs/current-features.md`
- 真实 CLI 验收明确文件创建并运行：直接使用 `write_file` 和 `run_shell`，未先 `list_files`
- 确认工具选择主线当前够用，暂不新增 planner

### Verified

- `tests/test_docs.py tests/test_current_features.py` passed
- 真实 CLI 验收通过

### Next

- 下一条主线转向 `0.21.0 LLM Adapter Protocol Review / 模型适配协议复查`

## 0.20.0 - 2026-05-25

当前学习阶段：Tool Choice Strategy / 工具选择策略。

变更级别：小特性。

### Changed

- 新增 `tool_choice_guidance()`，把工具选择策略从 `intent_prompt()` 中拆出为明确边界
- `intent_prompt()` 改为注入 `Tool choice strategy`，让模型按当前 intent 选择工具
- “怎么启动 / 如何启动 / 启动方式”归类为项目文档入口问题，隐藏 `list_files` / `search_text`
- 启动和用法问题的工具选择策略优先指向 `docs/current-features.md`
- 显式请求某个工具时，策略提示只使用该工具

### Tests

- 新增启动问题归类和文档入口策略测试
- 新增项目问答工具选择策略入口文档测试

### Verified

- `tests/test_intent.py tests/test_tool_registry.py tests/test_runtime_intent.py tests/test_runtime_prompt.py` passed
- `145 passed`

## 0.19.0 - 2026-05-25

当前学习阶段：Task Plan UX / 任务计划体验。

变更级别：小特性。

### Design

- 参考 Claude-Code-Source-Study 的任务系统资料和 CoreCoder Agent Loop 解读，确认本项目只吸收“任务状态辅助长任务推进”的核心思想
- 不复刻 Claude 的后台任务、任务通知、并发任务引擎、UI 面板或任务持久化
- 继续复用已有 `TaskState`、task 工具和 runtime prompt 注入边界

### Changed

- system prompt 明确多步骤 coding task 应创建 3-6 项短 todo，并在阶段开始或完成时更新
- system prompt 明确寒暄、泛学习和简单单步请求不使用 task 工具
- task 工具成功结果在 CLI 中显示为 `[tasks]` 区块，提升计划进度可见性
- 模型上下文中的 task 工具结果不变，仍保留原始任务状态文本

### Tests

- 新增 task 工具结果 CLI 格式化测试
- 新增空 task 状态 CLI 格式化测试

### Verified

- `tests/test_events.py tests/test_runtime_prompt.py tests/test_tasks.py tests/test_tools.py` passed
- `143 passed`
- 事件打印模拟通过：task 工具结果显示为 `[tasks]` 区块

## 0.18.0 - 2026-05-25

当前学习阶段：CLI Output Protocol Review / CLI 输出协议复查。

变更级别：小特性。

### Changed

- `read_file` 成功结果在 CLI 中统一显示摘要，不再因为内容较短就直接打印文件内容
- `search_text` 成功匹配结果在 CLI 中统一显示摘要，`(no matches)` 显示为明确的无匹配提示
- 写入、编辑、任务类短结果继续直接展示，保持动作结果可见
- 模型上下文中的工具结果不变，只调整终端展示协议

### Tests

- 新增 `read_file` 短结果摘要展示测试
- 新增 `search_text` 匹配结果摘要展示测试
- 新增 `search_text` 无匹配提示测试
- 保留写入类短结果直接展示测试

### Verified

- `tests/test_events.py` passed
- `141 passed`
- 事件打印模拟通过：`read_file` / `search_text` 摘要展示，`write_file` 短结果直接展示

## 0.17.2 - 2026-05-25

当前学习阶段：Permission Line Review / 权限体验主线收尾复查。

变更级别：复查版本。

### Review

- 复查 0.17.x 权限体验主线：确认提示、权限模式验收、拒绝后防绕路行为
- 确认当前轻量 Permission Pipeline 已足够支撑 mini-claude，不继续扩展复杂权限规则
- 暂不新增自动白名单、复杂规则合并、权限配置 UI 或 TUI
- 下一条主线转向 CLI 输出协议复查

### Verified

- `tests/test_docs.py tests/test_current_features.py` passed

## 0.17.1 - 2026-05-25

当前学习阶段：Permission Mode Acceptance Review / 权限模式验收复查。

变更级别：小特性。

### Changed

- 权限拒绝结果明确提示模型不要换工具重试同一操作
- runtime 在权限拒绝或用户拒绝后关闭本轮工具暴露，让模型解释权限边界

### Review

- 真实 CLI 验收 `plan` 模式：写文件和运行命令都会询问
- 真实 CLI 验收 `acceptEdits` 模式：文件写入自动允许，shell 仍确认
- 真实 CLI 验收 `dontAsk` 模式：写入直接拒绝，拒绝后不再绕路重试

### Tests

- 新增权限拒绝结果提示测试
- 新增权限拒绝后 runtime 关闭工具暴露测试

### Verified

- `tests/test_tool_executor.py tests/test_runtime_intent.py tests/test_events.py tests/test_permissions.py` passed
- 真实 CLI 验收 `plan`、`acceptEdits`、`dontAsk` 通过

## 0.17.0 - 2026-05-25

当前学习阶段：Permission UX Review / 权限体验复查。

变更级别：大特性。

### Changed

- 权限确认提示改为集中展示工具名、原因、目标和默认拒绝说明
- `permission_request` 事件不再单独打印粗糙原因，避免和确认输入重复
- 文件路径类操作只展示目标路径，不把完整写入内容塞进确认提示

### Tests

- 新增权限提示格式测试
- 新增 permission request 事件不打印测试

### Verified

- `tests/test_events.py tests/test_permissions.py tests/test_tool_executor.py tests/test_runtime_intent.py` passed
- `136 passed`
- 真实 CLI 验收写文件和运行命令通过

## 0.16.2 - 2026-05-24

当前学习阶段：Prompt / Context Line Review / 提示词与上下文主线收尾复查。

变更级别：复查版本。

### Review

- 复查 0.16.x prompt/context 主线：拼接顺序、summary / TaskState 边界、真实 CLI 验收结果
- 确认当前边界足够清楚，暂不继续增加 prompt 规则
- 暂不引入 prompt builder、模板系统、prompt DSL 或复杂 token budget
- 下一条主线转向权限体验复查

### Verified

- `tests/test_docs.py tests/test_current_features.py` passed

## 0.16.1 - 2026-05-24

当前学习阶段：Prompt / Context Acceptance Review / 提示词与上下文验收复查。

变更级别：复查版本。

### Review

- 真实 CLI 验收 Agent Loop 项目问答：仍读取 `docs/architecture.md`，回答基于项目实现
- 真实 CLI 验收泛学习请求：未调用工具，回答保持收敛
- 真实 CLI 验收明确文件任务：未先 `list_files`，写入、权限确认、`python3` 运行和最终总结正常
- 未发现需要改代码的问题

### Verified

- `tests/test_runtime_prompt.py tests/test_runtime_intent.py tests/test_context.py tests/test_tasks.py tests/test_docs.py tests/test_current_features.py` passed

## 0.16.0 - 2026-05-24

当前学习阶段：Prompt / Context Boundary Review / 提示词与上下文边界复查。

变更级别：大特性。

### Changed

- `_system_prompt()` 改为显式分段拼接
- 固定模型输入拼接顺序：base system -> workspace -> intent -> historical summary -> live task state
- historical summary 继续标记为历史上下文，不是当前任务列表
- TaskState 继续标记为 live task state，不合并进 summary

### Tests

- 更新 summary / TaskState 边界测试，固定 summary 先于 live task state 注入
- 新增 prompt/context 动态拼接顺序测试

### Verified

- `tests/test_runtime_prompt.py tests/test_runtime_intent.py tests/test_context.py tests/test_tasks.py` passed
- `133 passed`

## 0.15.2 - 2026-05-24

当前学习阶段：Acceptance Summary / 验收阶段总结。

变更级别：复查版本。

### Review

- 总结 0.15.x 真实 CLI 验收结果
- 确认项目功能问答、Agent Loop 项目问答、明确文件任务、错误命令反馈、泛学习短回答已通过
- 确认已修复 Agent Loop 问答误走泛化回答、泛学习偏长、CLI 项目交付流程误写为启动/重启
- 暂缓偶尔使用表格这类轻微风格问题，不为此增加复杂约束
- 下一步转向下一架构主线决策，而不是继续堆小版本

### Verified

- `tests/test_docs.py tests/test_current_features.py` passed

## 0.15.1 - 2026-05-24

当前学习阶段：Acceptance Follow-up Review / 验收跟进复查。

变更级别：复查版本。

### Review

- 跟进验收 Agent Loop 后续问答：能沿用上下文回答，未重复读取文档
- 跟进验收错误命令场景：能清楚展示 exit 127 和 command not found
- 跟进验收泛学习 agent 场景：保持短回答，未调用工具
- 本轮未发现必须改代码的高收益问题

### Documentation

- `PROJECT_PRINCIPLES.md` 明确本项目是 CLI，不需要重启
- 代码改动后的交付流程改为测试和必要 CLI 烟测

### Verified

- `132 passed`

## 0.15.0 - 2026-05-24

当前学习阶段：Real Usage Acceptance Review / 真实使用验收复查。

变更级别：大特性。

### Review

- 真实 CLI 验收项目功能问答：只读取 `docs/current-features.md`，输出收敛
- 真实 CLI 验收明确文件任务：直接写入目标文件并使用 `python3` 运行，未先 `list_files`
- 真实 CLI 验收 Agent Loop 问答：发现误走泛化回答
- 真实 CLI 验收泛学习请求：确认不调用工具，但回答偏长

### Changed

- `Agent Loop`、`主循环`、`对话循环` 归为明确文档入口的项目问题
- 泛学习提示词收紧为默认 3-5 行，不主动使用 emoji、表格或额外链接

### Tests

- 新增 Agent Loop 项目问答意图识别测试
- 扩展泛学习 prompt 测试，固定短输出和资源链接边界

### Verified

- `132 passed`

## 0.14.3 - 2026-05-24

当前学习阶段：Subagent Line Review / 子 Agent 主线收尾复查。

变更级别：复查版本。

### Review

- 复查 0.14.x 子 Agent 主线：运行隔离、prompt 边界、兜底总结
- 确认当前子 Agent 已保持只读、固定角色、不递归和短总结边界
- 暂停继续扩展自定义 Agent、后台并行、独立模型、worktree 隔离或 JSON 输出解析
- 下一条主线转向真实使用验收复查

### Verified

- `131 passed`

## 0.14.2 - 2026-05-24

当前学习阶段：Subagent Finalization Review / 子 Agent 兜底总结复查。

变更级别：小特性。

### Changed

- 子 Agent finalizer 可用时仍优先生成结构化最终答案
- 子 Agent finalizer 失败时返回短 `Result: inconclusive` 摘要
- 兜底结果只附少量最近证据，不再直接返回长 `Captured output`

### Tests

- 新增测试覆盖 finalizer 失败时的短兜底结果

### Verified

- `131 passed`

## 0.14.1 - 2026-05-24

当前学习阶段：Subagent Prompt Boundary Review / 子 Agent 提示词边界复查。

变更级别：小特性。

### Changed

- Explore / Plan / Verification 三个子 Agent prompt 明确不委托其他 Agent
- 保持短文本结构化输出，不改成 JSON 解析
- 不引入 prompt builder，避免为了消除少量重复而增加概念

### Tests

- 新增测试固定子 Agent prompt 的不委托边界
- 新增测试确认当前子 Agent prompt 不使用 JSON contract

### Verified

- `130 passed`

## 0.14.0 - 2026-05-24

当前学习阶段：Subagent Boundary Line Review / 子 Agent 边界主线复查。

变更级别：大特性。

### Changed

- 子 Agent 内部工具集继续只使用只读 workspace 工具
- 子 Agent 内部过滤 `explore_agent`、`plan_agent`、`verify_agent` 工具自身，避免递归 AgentTool 调用
- 保持当前三种固定内置子 Agent，不新增自定义 agent、后台并行、独立模型或 worktree 隔离

### Tests

- 新增测试确认子 Agent 即使收到包含子 Agent 工具的 registry，也不会向内部 runtime 暴露嵌套子 Agent 工具

### Verified

- `129 passed`

## 0.13.4 - 2026-05-24

当前学习阶段：Tool Line Review / 工具系统主线收尾复查。

变更级别：复查版本。

### Review

- 复查 0.13.x 工具系统主线：工具边界、内置工具形态、输入 schema、错误表现
- 确认工具系统当前边界清楚，暂不继续新增 Git 工具、MCP、复杂权限或插件系统
- 下一条主线转向子 Agent 边界复查

### Verified

- `128 passed`

## 0.13.3 - 2026-05-24

当前学习阶段：Tool Error Surface Review / 工具错误表现复查。

变更级别：小特性。

### Changed

- CLI 展示错误工具结果时增加 `[tool_error] tool_name:` 前缀
- 模型上下文中的错误 `tool_result` 内容保持不变
- 保持轻量实现，不引入复杂错误类型系统

### Tests

- 更新事件展示测试，固定错误工具结果的 CLI 前缀

### Verified

- `128 passed`

## 0.13.2 - 2026-05-24

当前学习阶段：Tool Input Schema Review / 工具输入 Schema 复查。

变更级别：小特性。

### Changed

- `Tool.validation_error()` 增加基础 JSON schema 类型校验：string、integer、boolean、array、object
- `Tool.validation_error()` 增加 enum 校验
- 保持轻量实现，不引入完整 JSON Schema 框架

### Tests

- 新增工具输入类型不匹配测试
- 新增工具输入 enum 不匹配测试
- 新增内置工具 schema 形态测试

### Verified

- `128 passed`

## 0.13.1 - 2026-05-24

当前学习阶段：Builtin Tools Shape Review / 内置工具形态复查。

变更级别：小特性。

### Review

- 复查 `builtin_tools.py`，确认它当前只是较长，职责仍集中在内置工具构造和少量直接相关 helper
- 暂不拆分 `builtin_tools.py`，避免过早制造文件碎片

### Tests

- 新增内置工具集合形态测试，固定当前 11 个基础工具

### Verified

- `125 passed`

## 0.13.0 - 2026-05-24

当前学习阶段：Tool Boundary Line Review / 工具系统边界主线复查。

变更级别：大特性。

### Review

- 复查工具链路：`Tool`、`ToolRegistry`、`tool_policy`、`ToolTurnExecutor`、`builtin_tools`
- 确认工具定义、工具集合、工具可见性、权限执行和结果包装仍然分层清楚
- 暂不新增 Git 工具、MCP、复杂权限或插件系统

### Tests

- 新增只读工具集过滤测试，确认子 Agent 不会获得依赖输入才可能只读的 `run_shell`

### Verified

- `124 passed`

## 0.12.3 - 2026-05-24

当前学习阶段：Runtime Line Review / Runtime 主线收尾复查。

变更级别：复查版本。

### Review

- 复查 0.12.x runtime 减重主线：伪工具调用兼容、system prompt 边界、AgentState 状态边界
- 确认 `runtime.py` 仍保持 queryLoop 风格协调器角色，暂不继续拆分
- 下一条主线转向工具系统边界复查

### Verified

- `123 passed`

## 0.12.2 - 2026-05-24

当前学习阶段：Runtime State Boundary Review / Runtime 状态边界复查。

变更级别：小特性。

### Changed

- 将 `AgentState.project_question_tool_rounds` 重命名为 `current_turn_tool_rounds`
- 明确该字段是当前用户请求内的工具轮次计数，不是跨对话长期状态
- 保持 `AgentState` 在 runtime 内，不新增 state 模块

### Tests

- 新增 runtime state 边界测试，确认当前请求内工具轮次计数会在新用户请求开始时重置

### Verified

- `123 passed`

## 0.12.1 - 2026-05-24

当前学习阶段：Runtime Prompt Boundary Review / Runtime 提示词边界复查。

变更级别：小特性。

### Changed

- 收敛 `SYSTEM_PROMPT`，移除已由 intent 边界覆盖的寒暄和泛学习细则
- system prompt 增加高层原则：遵循当前 intent guidance
- 保持具体场景规则在 `intent_prompt()` 中注入，不新增 prompt builder

### Tests

- 更新 runtime prompt 测试，固定系统提示只保留高层运行原则
- 新增测试确认系统提示不重复 intent-specific 规则

### Verified

- `122 passed`

## 0.12.0 - 2026-05-24

当前学习阶段：Runtime Boundary Slim Review / Runtime 边界减重复查。

变更级别：大特性。

### Changed

- 新增 `mini_agent/pseudo_tools.py`，承接伪工具调用标记解析、参数别名归一和 reasoning block 保留
- `AgentRuntime` 不再直接维护 XML/JSON/function 风格伪工具调用解析细节，只保留主循环委托
- 保持 runtime 对可见工具集合的约束，隐藏工具不会因为伪工具调用兼容而被执行

### Tests

- 新增独立伪工具调用兼容测试
- 保留 runtime 侧兼容测试，确认对外行为不变

### Verified

- `121 passed`

## 0.11.4 - 2026-05-24

当前学习阶段：Context Line Review / 上下文主线收尾复查。

变更级别：复查版本。

### Review

- 复查 0.11.x 上下文管理主线：tool result budget、micro-compact、full compact、summary 注入、错误结果保留、TaskState 边界
- 确认当前实现仍保持轻量，不引入向量库、长期记忆、复杂 token 预算器或新模块
- 下一条主线转向 Runtime 边界减重复查

### Verified

- `116 passed`

## 0.11.3 - 2026-05-23

当前学习阶段：Context / TaskState Relationship Review / 上下文与任务状态关系复查。

变更级别：小特性。

### Changed

- system prompt 明确标记 `TaskState` 为 live task state
- system prompt 明确标记 full compact summary 为 historical context，不是当前任务列表

### Tests

- 新增 TaskState 和 summary 同时存在且独立注入 system prompt 的测试
- 更新 TaskState prompt summary 测试

### Verified

- `116 passed`

## 0.11.2 - 2026-05-23

当前学习阶段：Tool Result Compact Policy Review / 工具结果压缩策略复查。

变更级别：小特性。

### Changed

- micro-compact 不再清理错误工具结果，便于继续排查失败原因
- 当前策略明确为：高噪音成功工具结果可压缩，task/todo 和错误工具结果保留

### Tests

- 新增错误工具结果不被 micro-compact 清理的测试
- 新增默认保留最近 6 个可压缩工具结果的测试

### Verified

- `115 passed`

## 0.11.1 - 2026-05-23

当前学习阶段：Summary Boundary Review / 摘要边界复查。

变更级别：小特性。

### Changed

- full compact prompt 明确保留用户目标、决策、文件路径、命令和未完成事项
- full compact prompt 明确不要复制长工具输出、闲聊或重复细节

### Tests

- 扩展 full compact summary prompt 边界测试

### Verified

- `113 passed`

## 0.11.0 - 2026-05-23

当前学习阶段：Context Compact Real-World Review / 上下文压缩真实复查。

变更级别：大特性。

### Review

- 对照 Claude-style 上下文管理主线，复查现有 tool result budget、micro-compact、full compact 和 summary 注入
- 保持轻量实现，不引入向量库、长期记忆、复杂 token 预算器或新模块

### Tests

- 新增真实长任务 compact 测试
- 覆盖用户目标、关键文件路径、测试命令、未完成事项、micro-compact placeholder 和最近消息保留

### Verified

- `113 passed`

## 0.10.5 - 2026-05-23

当前学习阶段：0.10 Line Review / 0.10 主线复查。

变更级别：小特性。

### Review

- 手动验收项目结构、架构层数、当前功能、下一步、模糊项目查看和创建文件路径
- 明确项目问题能按文档入口读取，模糊项目问题允许 `list_files`
- 文件创建任务能直接请求 `write_file` 权限

### Changed

- `docs/current-features.md` 明确当前 CLI 启动后共有 14 个模型可用工具：11 个基础工具 + 3 个只读子 Agent 工具
- 项目问答 prompt 增加要求：不要估算数量

### Tests

- 新增当前功能文档的工具数量拆分测试

### Verified

- `112 passed`

## 0.10.4 - 2026-05-23

当前学习阶段：Architecture Answer Accuracy Review / 架构问答准确性复查。

变更级别：小特性。

### Changed

- `docs/architecture.md` 明确写出当前架构分为 8 层
- 明确 `Sub Agents` 是独立一层，不应合并到其他层
- 项目问答 prompt 增加要求：保留文档中的明确数字和有序列表

### Tests

- 新增架构文档明确 8 层的文档测试
- 扩展项目问答 prompt 测试，固定保留明确数字和列表的约束

### Verified

- `111 passed`

## 0.10.3 - 2026-05-23

当前学习阶段：Output Style Review / 输出风格复查。

变更级别：小特性。

### Changed

- 收紧项目问答默认输出风格：短段落或 3-6 条短要点
- 默认不使用 emoji、表格、目录树或额外学习链接
- 项目问答 prompt 明确要求始终给出可见最终回答
- 隐藏但存在的工具被模型调用时，runtime 返回内部引导结果，不再按普通未知工具错误展示
- streaming provider 只在 final response 返回文本、没有 text delta 时，CLI 也会打印最终文本
- `下一步`、`当前版本` 等明确文档入口问题即使没有显式项目词，也会按项目问答处理
- 项目问答 prompt 改为按问题选择最相关入口文档，不再默认先读 README

### Tests

- 扩展项目问答 system prompt 边界测试
- 更新隐藏工具执行兜底测试，区分 unavailable tool 和 unknown tool
- 新增 final response 无 text delta 时仍打印文本的测试
- 新增无显式项目词的文档入口问题意图测试

### Verified

- `110 passed`

## 0.10.2 - 2026-05-23

当前学习阶段：Create Intent Recognition / 创建意图识别补强。

变更级别：小特性。

### Changed

- 将中文 `创建` 纳入 coding task 关键词
- `创建 x.txt，内容是 x` 会识别为明确文件任务，并隐藏 `list_files`
- 不带明确文件路径的创建请求仍保留普通 coding task 工具可见性

### Tests

- 新增中文创建文件请求的意图识别测试
- 新增创建类非明确文件任务不隐藏 `list_files` 的测试

### Verified

- `108 passed`

## 0.10.1 - 2026-05-23

当前学习阶段：Visible Tool Enforcement / 可见工具执行校验。

变更级别：小特性。

### Changed

- runtime 执行工具时只传入当前 intent 可见的工具集合
- 伪工具调用归一化也遵守当前可见工具集合
- 明确文档入口的项目问答中，隐藏的 `list_files` 即使被模型输出也不会被执行

### Tests

- 新增隐藏工具不能被执行的 runtime 测试
- 新增隐藏伪工具调用不被归一化的测试
- 调整旧测试，让权限和输入校验用明确工具意图触发

### Verified

- `106 passed`

## 0.10.0 - 2026-05-23

当前学习阶段：Project Read Strategy Hardening / 项目读取策略硬化。

变更级别：大特性。

### Changed

- 明确文档入口的项目问答会隐藏 `list_files`
- 项目结构、项目架构、当前功能、当前版本、下一步等问题直接走 read/search 路径
- 模糊项目问题仍保留 `list_files`
- 复用 `hidden_tools`，不新增 planner，不改变工具执行层

### Tests

- 新增项目问答隐藏 `list_files` 的 intent 测试
- 新增项目问答隐藏 `list_files` 的 tool registry 测试
- 更新 runtime 工具可见性测试

### Verified

- `104 passed`

## 0.9.9 - 2026-05-23

当前学习阶段：Direct File Tool Gating / 明确文件任务工具门控。

变更级别：小特性。

### Changed

- `IntentDecision` 增加轻量 `hidden_tools`，用于隐藏本轮不应暴露的工具
- 明确给出文件路径和内容的 coding task 会隐藏 `list_files`
- 工具注册表会按 `hidden_tools` 过滤模型可见工具

### Tests

- 扩展明确文件任务意图测试，确认隐藏 `list_files`
- 新增工具注册表测试，确认明确文件任务不暴露 `list_files`

### Verified

- `101 passed`

## 0.9.8 - 2026-05-23

当前学习阶段：Direct File Task UX / 明确文件任务体验收敛。

变更级别：小特性。

### Changed

- coding task guidance 明确：用户给出文件路径和精确内容时，直接创建或编辑文件，不先 `list_files`
- `list_files` 的 CLI 展示改为条目数和少量预览，避免目录列表刷屏
- 不改变工具执行和权限管线

### Tests

- 新增明确文件任务不应先 `list_files` 的提示测试
- 新增 `list_files` 展示摘要测试

### Verified

- `100 passed`

## 0.9.7 - 2026-05-23

当前学习阶段：Shell Execution UX / Shell 执行体验收敛。

变更级别：小特性。

### Changed

- `run_shell` 的 CLI 展示改为 exit/stdout/stderr 格式，不再原样输出 JSON
- 系统提示建议运行 Python 脚本时优先使用 `python3`
- shell 工具结果进入模型上下文的结构不变

### Tests

- 新增 shell 成功结果展示测试
- 新增 shell 失败结果展示测试

### Verified

- `98 passed`

## 0.9.6 - 2026-05-23

当前学习阶段：Tool Result Display Compact / 工具结果展示收敛。

变更级别：小特性。

### Changed

- CLI 打印层会隐藏过长的成功工具结果，只显示一行摘要
- 工具结果仍完整写入 agent 消息历史，模型上下文不受影响
- 短工具结果和错误工具结果仍完整展示

### Tests

- 新增长成功工具结果隐藏测试
- 新增短工具结果完整展示测试
- 新增长错误工具结果完整展示测试

### Verified

- `96 passed`

## 0.9.5 - 2026-05-23

当前学习阶段：Manual Usage Review / 手动使用复查。

变更级别：文档验收记录。

### Review

- 寒暄和泛学习请求不误用工具
- 写文件和运行脚本权限路径正常
- 项目架构问题仍会先 `list_files`
- CLI 直接打印长工具结果，用户感知偏吵，因此进入 0.9.6

## 0.9.4 - 2026-05-23

当前学习阶段：Project Answer Compression / 项目问答输出收敛。

变更级别：小特性。

### Changed

- 项目问答 guidance 增加输出收敛要求：直接、简洁回答用户的具体问题
- 默认不复述整份文档、长历史或宽泛功能清单
- 用户明确要求详细时再展开

### Tests

- 扩展项目问答 system prompt 边界测试，固定输出收敛约束

### Verified

- `93 passed`

## 0.9.3 - 2026-05-22

当前学习阶段：Project Question Read Strategy / 项目问答读取策略。

变更级别：小特性。

### Changed

- 项目问答 guidance 改为优先读取文档入口：`README.md`、`docs/context-map.md`、`docs/architecture.md`、`docs/current-features.md`、`docs/roadmap.md`
- 明确 `list_files` 只在目标文件不清楚时使用
- 保持现有工具策略和主循环不变，不新增 planner 或子 Agent

### Tests

- 新增项目问答 system prompt 边界测试

### Verified

- `93 passed`

## 0.9.2 - 2026-05-22

当前学习阶段：Strict Tool Input Validation / 严格工具输入校验。

变更级别：小特性。

### Changed

- `Tool` 增加统一 schema 输入校验：未知字段会被拒绝，缺少 required 字段会被拒绝
- `ToolTurnExecutor` 改为使用统一校验入口，避免各工具重复处理基础输入契约
- 伪工具调用中的 `file_path` 会归一成 `path`，并移除旧别名，避免严格校验误判

### Tests

- 新增未知字段拒绝测试
- 新增 required 字段缺失测试
- 收紧伪工具调用别名归一化测试

### Verified

- `92 passed`

## 0.9.1 - 2026-05-22

当前学习阶段：Context Boundary Tests / 上下文边界测试。

变更级别：测试增强版本。

### Tests

- 新增 micro-compact 不压缩孤立 `tool_result` 的测试
- 新增接近用户长任务的 full compact 测试，确认旧目标进入摘要 prompt，最近 4 条原始消息保留

### Verified

- `90 passed`

## 0.9.0 - 2026-05-22

当前学习阶段：Context Strategy Review / 上下文策略复查。

变更级别：架构复查版本。

### Decision

- 当前上下文策略保持四段式：tool result budget -> micro-compact -> full compact -> summary 注入 system prompt
- 暂不引入复杂 token 预算器、长期记忆系统、向量库或多层缓存
- 下一步只补必要上下文边界测试

### Tests

- 新增 full compact 摘要注入 system prompt 的测试

### Verified

- `88 passed`

## 0.8.4 - 2026-05-22

当前学习阶段：Tool Executor Boundary Review / 工具执行边界复查。

变更级别：小特性版本。

### Minor Features

- 复查 `ToolTurnExecutor` 边界，确认工具执行层仍保持轻量
- 新增测试固定 `tool_batch_start` / `tool_batch_end` 默认不打印到 CLI
- 下一步从工具执行主题转向上下文策略复查

这是一次架构健康检查。它不新增用户能力，只防止内部批次事件意外变成用户终端噪音。

### Tests

- 新增 `print_runtime_event()` 不打印工具批次事件的测试

### Verified

- `87 passed`

## 0.8.3 - 2026-05-22

当前学习阶段：Project Question Follow-up Fix / 项目问答跟进修复。

变更级别：修复版本。

### Fixes

- 项目问题第一轮如果只用了 `list_files`，允许第二轮继续读取必要文件
- 使用 `read_file` / `search_text` 后仍会关闭项目问答工具，避免无休止扫描项目
- `list_files` 的模型可见 schema 不再暴露 `include_hidden`，减少普通项目问答列出隐藏文件的概率

这是针对真实验收问题的轻量修复：项目架构问题不能只列目录就结束，但也不能重新放开无限读文件。

### Tests

- 新增项目问题先列目录、再读文档、最后总结的 runtime 测试

### Verified

- `86 passed`

## 0.8.2 - 2026-05-22

当前学习阶段：Tool Batch Events / 工具批次事件。

变更级别：小特性版本。

### Minor Features

- 新增 `tool_batch_start` 事件
- 新增 `tool_batch_end` 事件
- 批次事件包含 `parallel`、`tools`、`tool_use_ids`
- 默认 CLI 不打印批次事件，避免增加用户噪音

这是对工具批次分区的事件化补充：执行结构存在，事件结构也能表达。它不引入完整事件总线，也不实现 StreamingToolExecutor。

### Tests

- 新增工具批次事件测试
- 调整未知工具和权限拒绝测试以适配批次事件顺序

### Verified

- `85 passed`

## 0.8.1 - 2026-05-22

当前学习阶段：Tool Batch Partition / 工具批次分区。

变更级别：小特性版本。

### Minor Features

- 新增轻量 `ToolBatch`
- `ToolTurnExecutor` 按连续并发安全工具分批执行
- 写入、未知或不安全工具单独串行执行
- 保持 tool result 格式、权限逻辑和输入校验顺序不变

这是对 Claude `partitionToolCalls()` 思想的轻量实现。它吸收工具编排的核心价值，但不引入 StreamingToolExecutor 的流中调度、取消和丢弃机制。

### Tests

- 新增工具批次分区测试
- 新增跨批次结果顺序测试

### Verified

- `84 passed`

## 0.8.0 - 2026-05-22

当前学习阶段：Streaming Tool Execution Decision / 流式工具执行取舍。

变更级别：架构决策版本。

### Decision

- 暂不实现完整 StreamingToolExecutor
- 保留当前 batch tool execution 路径
- 下一步优先做 `Tool Batch Partition`

理由：Claude 的流式工具执行包含流中启动、挂起结果丢弃、fallback 取消和合成错误结果。它是重要思想，但当前直接实现会让 mini-claude 过早复杂化。更合适的下一步是吸收 Claude 的工具批次分区思想。

### Verified

- 文档决策版本，无代码行为变化

## 0.7.5 - 2026-05-22

当前学习阶段：Runtime Boundary Review / 主循环边界验收。

变更级别：小特性版本。

### Minor Features

- 新增 Runtime 边界守护测试
- 验证工具并发执行、权限决策、终端输入输出没有回流到 `runtime.py`
- 修正 roadmap 中关于 tool result budget 的过期判断

这是一次架构刹车检查：确认 0.7.x 的拆分让边界更清楚，而不是继续制造不必要的抽象。

### Tests

- 新增 Runtime 不直接持有工具执行细节的测试
- 新增 Runtime 不直接做终端输入输出的测试

### Verified

- `82 passed`

## 0.7.4 - 2026-05-22

当前学习阶段：Tool Turn Executor / 工具轮次执行器。

变更级别：小特性版本。

### Minor Features

- 新增 `mini_agent.tool_executor.ToolTurnExecutor`
- 将工具并发判断、输入校验、权限确认、执行和错误 tool_result 组装从 runtime 移到工具轮次执行器
- `AgentRuntime` 只负责调度工具轮次，不再直接持有工具执行细节

这是对 Claude 工具执行服务 / StreamingToolExecutor 边界的轻量对齐。当前不实现流中工具执行，不改变 tool result 格式。

### Tests

- 新增未知工具的 executor 测试
- 新增权限拒绝的 executor 测试

### Verified

- `80 passed`

## 0.7.3 - 2026-05-21

当前学习阶段：Runtime Error Recovery / 轻量错误恢复。

变更级别：小特性版本。

### Minor Features

- 工具错误会发出 `tool_error` 事件，并继续作为 `tool_result` 回传模型
- 模型调用失败会发出 `model_error` 事件
- fallback 模型路径继续发出 `model_fallback`
- 轮次耗尽会发出 `turn_limit_reached` 和 `stopped`

这是对 Claude `queryLoop` 错误恢复思想的轻量实现。当前不做 429/413/529 全套重试，也不做输出 token 截断多轮恢复。

### Tests

- 新增无效工具输入错误事件测试
- 新增未知工具错误事件测试
- 新增轮次耗尽事件测试
- 新增主模型失败 fallback 事件测试
- 新增无 fallback 模型失败事件测试

### Verified

- `78 passed`

## 0.7.2 - 2026-05-21

当前学习阶段：Runtime Loop Shape / 主循环形态整理。

变更级别：小特性版本。

### Minor Features

- `run_user_turn()` 拆成更清晰的阶段方法：
  - `_begin_turn()`
  - `_record_assistant_response()`
  - `_handle_final_answer()`
  - `_handle_tool_turn()`

这是对 Claude `queryLoop` 阶段感的轻量对齐。它不引入完整状态机，不改变工具执行模型，只让主循环更清楚、更容易放置后续错误恢复和调度逻辑。

### Tests

- 新增 runtime loop 阶段方法存在性测试

### Verified

- `73 passed`

## 0.7.1 - 2026-05-21

当前学习阶段：Runtime Print Cleanup / 输出边界收敛。

变更级别：小特性版本。

### Minor Features

- Runtime 移除残留直接文本打印路径
- 权限确认改为 `permission_request` 事件加可注入 permission handler
- 终端输入输出进一步集中到 `mini_agent.events` 和 CLI 边界

这是对 `0.7.0` 轻量运行时事件的收敛补充。它继续对齐 Claude 中 runtime 产出事件、外层消费事件的思路，但不引入完整 UI event bus。

### Tests

- 新增权限确认 handler 测试

### Verified

- `72 passed`

## 0.7.0 - 2026-05-21

当前学习阶段：Lightweight Runtime Events / 轻量运行时事件。

变更级别：大特性版本。

### Major Features

- 新增 `mini_agent/events.py`
- 新增 `RuntimeEvent` 和 `EventHandler`
- Runtime 会记录并发出 `turn_start`、`model_start`、`text_delta`、`assistant_message`、`tool_start`、`tool_result`、`turn_transition`、`final_answer` 等轻量事件
- CLI 显式使用 `print_runtime_event()` 展示事件
- Runtime 支持关闭事件打印，便于测试和后续外层消费

这是对 Claude `queryLoop` / AsyncGenerator 事件化思想的轻量实现。当前只拆清 runtime 和 CLI 输出边界，不实现完整事件总线，也不实现 StreamingToolExecutor。

### Tests

- 新增最终回答事件序列测试
- 新增工具调用和 `next_turn` 转换事件测试
- 新增关闭事件打印后的静默 runtime 测试

### Verified

- `71 passed`

## 0.6.5 - 2026-05-21

当前学习阶段：Context Map / 文档导航索引。

变更级别：文档小特性版本。

### Documentation

- 新增 `docs/context-map.md`
- 在 README 文档入口中加入 Context Map
- 同步当前版本和文档体系说明

这个版本不改变代码行为。它的目标是降低学习者和 AI 工具进入项目时的文档读取成本。

## 0.6.4 - 2026-05-21

当前学习阶段：Tool Result Budget / 输出收敛。

变更级别：小特性版本。

### Minor Features

- `Tool.run()` 统一通过工具结果预算截断超长输出
- 超长结果保留开头和结尾，并插入截断说明
- `read_file`、`search_text`、`run_shell`、diff 类工具设置更小结果预算

这是对 Claude 工具结果预算思想的轻量实现。它在工具结果进入上下文前先减噪，不引入复杂预算器，也不拆分 runtime。

### Tests

- 新增通用工具结果截断测试
- 新增 `read_file` 大文件结果预算测试

### Verified

- `68 passed`

### Documentation

- 压缩 `docs/architecture.md`、`docs/current-features.md`、`docs/versioning.md`、`docs/learning-qa.md`
- 明确文档职责边界，减少重复内容对上下文的占用
- 在 `PROJECT_PRINCIPLES.md` 增加文档克制和文档减重要求

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
- Runtime 可识别 `<function=...><parameter=...>` 伪工具调用，并映射常见参数名
- Runtime 规范化伪工具调用时会保留 `ReasoningBlock`，避免 thinking provider 下一轮丢失 `reasoning_content`
- 流式输出会抑制这类伪工具调用文本，避免直接展示给用户
- 当 provider 只在 stream delta 中返回文本、最终响应为空时，Runtime 会用累计文本补回最终响应
- 当模型最终响应没有用户可见文本、只有空白文本或没有工具调用时，Runtime 会返回简短兜底回复，避免空回复
- 意图识别会把显式 `explore_agent` / `plan_agent` / `verify_agent` 请求归为可用工具的项目问题
- 意图识别会把显式 `run_shell` 请求归为可用工具的编码任务，并只暴露 `run_shell`
- 显式子 Agent 请求只暴露被点名的子 Agent 工具，避免主 Agent 抢先使用文件工具
- 普通项目问题只暴露 `list_files`、`read_file`、`search_text`，不默认暴露子 Agent，并在一轮工具调用后关闭工具暴露，避免解释类问题读太多文件
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
- 新增 `<function=...><parameter=...>` 伪工具调用识别测试
- 新增伪工具调用规范化时保留 reasoning 的测试
- 新增 stream delta 文本补回最终响应测试
- 新增空最终响应的兜底回复测试
- 新增空白最终文本的兜底回复测试
- 新增显式子 Agent 请求的 intent 分类测试
- 新增显式 `run_shell` 请求的 intent 分类测试
- 新增显式 `run_shell` 请求只暴露目标工具的测试
- 新增显式子 Agent 请求只暴露目标工具的测试
- 新增项目问题工具暴露收窄和一轮后关闭工具的测试
- 新增子 Agent 工具调用预算和轮次限制测试
- 新增子 Agent 到达轮次上限后的 finalization 测试
- 新增显式子 Agent 工具只执行一次的 runtime 测试
- 新增 `list_files` 默认隐藏噪音和显式显示隐藏项测试
- 新增 system prompt 真实工具调用约束测试

### Verified

- `66 passed`

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
