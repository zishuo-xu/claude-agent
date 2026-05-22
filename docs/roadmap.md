# Roadmap

这份文档只记录方向、取舍和下一步。详细版本变化见 `CHANGELOG.md`，当前能力清单见 `docs/current-features.md`。

当前版本：`0.9.1`

## 已完成主线

- `0.1.0`: 最小 Agent 闭环
- `0.2.0`: LLM 适配层、工具系统、权限骨架、工作区边界、意图门控
- `0.2.1`: Diff 预览和 patch 风格编辑
- `0.3.0`: Task/Todo 状态
- `0.4.0`: 流式输出
- `0.4.1`: OpenAI-compatible streaming 空 `choices` 修复
- `0.4.2`: Tool Registry / Tool Policy 边界
- `0.5.0`: 上下文 micro-compact
- `0.6.0`: Explore / Plan 只读子 Agent
- `0.6.1`: Verification 只读子 Agent
- `0.6.2`: 子 Agent 输出结构化
- `0.6.3`: 工具输入验证层
- `0.6.4`: Tool Result Budget / 输出收敛
- `0.6.5`: Context Map / 文档导航索引
- `0.7.0`: Lightweight Runtime Events / 轻量运行时事件
- `0.7.1`: Runtime Print Cleanup / 输出边界收敛
- `0.7.2`: Runtime Loop Shape / 主循环形态整理
- `0.7.3`: Runtime Error Recovery / 轻量错误恢复
- `0.7.4`: Tool Turn Executor / 工具轮次执行器
- `0.7.5`: Runtime Boundary Review / 主循环边界验收
- `0.8.0`: Streaming Tool Execution Decision / 流式工具执行取舍
- `0.8.1`: Tool Batch Partition / 工具批次分区
- `0.8.2`: Tool Batch Events / 工具批次事件
- `0.8.3`: Project Question Follow-up Fix / 项目问答跟进修复
- `0.8.4`: Tool Executor Boundary Review / 工具执行边界复查
- `0.9.0`: Context Strategy Review / 上下文策略复查
- `0.9.1`: Context Boundary Tests / 上下文边界测试

## 架构减重审视

结论：当前架构主线仍然清楚，但文档和后续规划已经有变重趋势。下一阶段应少加功能，先保持项目轻。

### 保留

- `AgentRuntime`: 仍作为主循环协调器，暂不拆更细。
- `ToolRegistry` / `tool_policy`: 保留，后续工具和子 Agent 都依赖这个边界。
- `context.py`: 保留，micro-compact 是上下文管理主线的一部分。
- `subagent.py`: 保留，但暂停继续增加 Agent 类型。
- `PROJECT_PRINCIPLES.md`: 保留为最高层工作原则。
- `CHANGELOG.md`: 作为详细历史，不把完整历史重复写进 roadmap。

### 暂不做

- 不继续新增更多子 Agent。
- 不急着做 MCP。
- 不急着做 Git 专用工具。
- 不做复杂权限深化；仅保留当前轻量输入校验。
- 不把子 Agent 输出改成 JSON 解析。
- 不拆分 `AgentRuntime`，除非出现真实复杂度压力。

### 当前风险

- `docs/current-features.md` 和 `docs/architecture.md` 已经偏长，后续只更新必要内容。
- `builtin_tools.py` 和 `llm.py` 是目前最大的代码文件，但职责仍清楚，暂不拆。
- `runtime.py` 已拆出事件展示和工具执行细节；剩余复杂度主要来自 provider 兼容、伪工具调用和上下文处理。
- 真实验收发现的空回复、项目解释读太多文件、只列目录不总结问题已做轻量收敛；后续继续先观察真实使用，不急着继续加复杂调度。

### 参考资料使用原则

- Claude-Code-Source-Study 仍作为主要参考。
- CoreCoder `article/` 作为辅助解读参考，帮助理解架构总览、Agent Loop、工具系统、上下文压缩、流式执行、多 Agent 等主题。
- 参考资料用于帮助判断设计方向；实现保持 mini-claude 的轻量级工程化，不直接照搬完整复杂度。

## 当前设计对比 Claude

### 已对齐的主干

- Agent Loop：本项目的 `AgentRuntime.run_user_turn()` 对应 Claude 的 `queryLoop`，负责用户输入、模型调用、工具执行、工具结果回传和下一轮推理。
- LLM 边界：`mini_agent.llm.LLMClient` 对应 Claude 的模型请求边界，把 provider 差异隔离在适配层。
- 工具系统：`Tool` / `build_tool()` / `ToolRegistry` 对应 Claude 的 `buildTool()` 思路，统一描述 schema、输入校验、执行函数和风险元信息。
- 权限与门控：`intent.py`、`tool_policy.py`、`permissions.py` 对应 Claude 的工具可用性判断和 Permission Pipeline，但保持轻量。
- 上下文管理：`micro_compact` 和 `full compact` 对应 Claude 的上下文压缩主线。
- 子 Agent：`explore_agent`、`plan_agent`、`verify_agent` 对应 Claude 的 AgentTool / built-in agent 思路，但仅保留轻量只读形态。

### mini-claude 的轻量化差异

- 没有完整事件总线：当前 runtime 直接消费流式文本和工具调用，尚未抽象成统一事件流。
- 没有 StreamingToolExecutor：已有工具轮次执行边界，但决策为暂不做“模型边输出、工具边执行”的并发调度。
- 没有复杂 UI/TUI 协议：当前只做 CLI 输出，便于理解主循环。
- 没有动态工具发现：工具注册是本地静态注册，暂不做 MCP / 插件工具。
- 权限系统较轻：当前重点是输入校验、危险工具确认和工作区边界，不做复杂规则合并。
- 子 Agent 较轻：只有内置只读 Agent，不支持自定义 `.claude/agents`、后台并行、独立模型、worktree/remote 隔离。
- 上下文预算较轻：已有 tool result budget、micro/full compact，暂不做更复杂预算器。

### 当前判断

这些差异是可接受的：本项目目标是 mini-claude，即轻量级工程化地实现 Claude 的核心架构，而不是复制完整产品复杂度。当前最需要警惕的不是“功能不够多”，而是 `runtime.py` 承载了越来越多 provider 兼容、伪工具调用、流式输出和上下文处理逻辑。后续新增能力应优先围绕“让主循环更清楚、更可维护”展开。

## 下一步

### P1 / `0.9.2`: Context Strategy Decision / 上下文策略取舍

目标：基于 0.9.0/0.9.1 的复查结果，决定上下文策略是否暂时收尾，还是需要一个轻量增强点。

作用：

- 避免为了上下文继续堆复杂功能。
- 明确是否离开上下文主题，转向子 Agent 或权限体验。
- 保持 mini-claude 的轻量工程化边界。

建议范围：

- 优先做设计判断。
- 不做复杂 token 预算器。
- 不引入长期记忆系统。
- 不改变 compact 主流程。

### 已完成 / `0.9.1`: Context Boundary Tests / 上下文边界测试

目标：补少量上下文边界测试，确认 micro/full compact 不会误伤用户目标、任务状态和最新工具结果。

结果：

- 新增测试确认 micro-compact 不会压缩没有对应 `tool_use` 的孤立 `tool_result`。
- 新增接近用户长任务的 full compact 测试：旧目标进入摘要 prompt，最近 4 条原始消息保留。
- 不改变 compact 主流程。

### 已完成 / `0.9.0`: Context Strategy Review / 上下文策略复查

目标：离开工具执行主题，复查当前 tool result budget、micro-compact、full compact 是否形成清晰上下文策略。

结论：

- 当前上下文策略保持四段式：tool result budget -> micro-compact -> full compact -> summary 注入 system prompt。
- 暂不做复杂 token 预算器、长期记忆系统或向量库。
- 新增测试确认 full compact 摘要会进入后续 system prompt。

### 已完成 / `0.8.4`: Tool Executor Boundary Review / 工具执行边界复查

目标：复查 `ToolTurnExecutor` 在批次分区和批次事件后是否仍然简洁，避免工具执行层继续膨胀。

结论：

- `ToolTurnExecutor` 职责仍集中：分区、执行、权限、错误包装和批次事件。
- `AgentRuntime` 没有重新承担工具并发、权限决策或终端 IO。
- 新增测试固定批次事件默认不打印，避免内部事件变成用户噪音。

### 已完成 / `0.8.3`: Project Question Follow-up Fix / 项目问答跟进修复

目标：修复“解释项目架构”这类问题只执行 `list_files` 后就返回提示符、不继续总结的问题。

结果：

- 项目问题第一轮如果只用了 `list_files`，允许第二轮继续读取必要文件。
- 一旦使用 `read_file` / `search_text`，或第二轮仍只列目录，就关闭项目问答工具。
- `list_files` 的模型可见 schema 不再暴露 `include_hidden`，减少 `.env`、`.venv` 等隐藏项出现在普通项目问答中的概率。

### 已完成 / `0.8.2`: Tool Batch Events / 工具批次事件

目标：让事件流能表达工具批次边界，但默认 CLI 不打印批次事件，避免增加用户噪音。

结果：

- 新增 `tool_batch_start`
- 新增 `tool_batch_end`
- 批次事件包含 `parallel`、`tools`、`tool_use_ids`
- 不改变 tool result 格式、权限逻辑、Agent Loop 和 CLI 默认输出

### 已完成 / `0.8.1`: Tool Batch Partition / 工具批次分区

目标：把工具执行的“全安全才并发，否则全串行”改成更接近 Claude 的批次分区：连续安全工具并发，写入或不安全工具串行。

结果：

- 新增轻量 `ToolBatch`
- `ToolTurnExecutor` 会把连续并发安全工具合并为并发批次
- 写入、未知或不安全工具单独串行执行
- 保持 tool result 格式、权限逻辑和输入校验顺序不变

验证：

- 新增批次分区测试
- 新增跨批次结果顺序测试

### 已完成 / `0.8.0`: Streaming Tool Execution Decision / 流式工具执行取舍

目标：判断是否进入简化版流式工具执行，而不是直接实现 Claude 的完整 StreamingToolExecutor。

结论：

- 暂不实现 StreamingToolExecutor。
- 保留当前“模型流结束后执行工具”的 batch execution。
- 下一步先做更轻量、更有收益的工具批次分区。

理由：

- Claude 的流式工具执行涉及流中启动、挂起结果、fallback 丢弃、取消原因和合成错误结果，复杂度较高。
- mini-claude 当前更需要保持 Agent Loop 清晰。
- Claude 的批次分区思想收益明确，且可以在现有 `ToolTurnExecutor` 内轻量实现。

### 已完成 / `0.7.5`: Runtime Boundary Review / 主循环边界验收

目标：在继续加功能前，验证 `runtime.py`、`tool_executor.py`、`events.py` 的边界是否清楚，避免为了优化继续拆出不必要模块。

结果：

- Runtime 不再直接持有工具并发执行、权限决策和终端输入输出细节。
- 新增边界守护测试，防止这些职责回流到 runtime。
- 修正 roadmap 中关于 tool result budget 的过期判断。

### 已完成 / `0.7.4`: Tool Turn Executor / 工具轮次执行器

目标：把工具轮次执行从 runtime 主循环中再收敛一层，让主循环只负责调度“这一轮需要执行工具”，具体的校验、权限、执行、结果组装由工具轮次执行器处理。

结果：

- 对齐 Claude 工具执行服务 / StreamingToolExecutor 的架构边界。
- `runtime.py` 不再直接持有工具执行细节。
- 新增 `mini_agent.tool_executor.ToolTurnExecutor`。
- 为未来简化版流中工具执行保留位置。

### 已完成 / `0.7.3`: Runtime Error Recovery / 轻量错误恢复

目标：补一个 mini-claude 级别的错误恢复边界，让模型调用失败、工具失败、轮次耗尽等路径更清楚。

结果：

- 工具错误发出 `tool_error`，同时仍作为 `tool_result` 回传模型。
- 模型调用失败发出 `model_error`，fallback 路径发出 `model_fallback`。
- 轮次耗尽发出 `turn_limit_reached` 和 `stopped`。
- 不做 429/413/529 全套生产级恢复。

### 已完成 / `0.7.2`: Runtime Loop Shape / 主循环形态整理

目标：在不拆大模块的前提下，让 `run_user_turn()` 的阶段更清楚，减少主循环阅读负担。

结果：

- 提取 `_begin_turn()`、`_record_assistant_response()`、`_handle_final_answer()`、`_handle_tool_turn()`。
- 主循环更接近 Claude `queryLoop` 的阶段感。
- 行为保持不变。

### 已完成 / `0.7.1`: Runtime Print Cleanup / 输出边界收敛

目标：继续收敛 runtime 内残留的直接输出和交互边界，让运行时事件层更干净。

结果：

- 移除 runtime 内残留文本打印路径。
- 权限确认改为 `permission_request` 事件 + 可注入 permission handler。
- Runtime 不再直接 `print/input`，终端交互集中到事件/CLI 边界。

### 已完成 / `0.7.0`: Lightweight Runtime Events / 轻量运行时事件

目标：runtime 产生轻量事件，CLI 消费事件并打印，降低主循环和输出展示的耦合。

保留的复杂度边界：

- 不实现 StreamingToolExecutor。
- 不引入完整事件总线。
- 不改变工具执行模型。
- 保持 CLI 行为基本不变。

### 已完成 / `0.6.4`: Tool Result Budget / 输出收敛

目标：在工具结果进入上下文前做轻量预算，避免 `read_file`、`search_text`、`run_shell` 等工具把过长输出塞进对话历史。

作用：

- 让项目问答更快收敛，不因为读了大文档而拖长上下文。
- 让 micro/full compact 的压力变小，提前减少噪音。
- 对齐 Claude 中“工具结果需要被预算和裁剪”的设计思想。

建议范围：

- 给工具结果增加统一截断说明。
- 对大文本工具保留开头和结尾。
- 不引入复杂预算器，不拆 runtime。
- 已增加大输出截断测试。

## 候选但暂缓

### 权限深化

Claude 的 `Tool` 还有更细的 `checkPermissions()` 等边界。本项目当前权限骨架够用，等工具复杂度真正上来再做。

### Git 专用工具

`git_status`、`git_diff`、`git_log` 能减少 shell 风险，但当前学习主线收益不大，暂缓。

### MCP 工具注册

MCP 是重要方向，但会引入配置、连接、外部工具发现等复杂度。等项目主线更稳后再进入。

## 暂缓项

- 复杂终端 UI
- 大规模 settings 合并
- 自定义 Agent markdown
- 插件 Agent
- 后台并行子 Agent
- 自动发布或远程执行
