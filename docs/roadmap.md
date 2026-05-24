# Roadmap

这份文档只记录方向、取舍和下一步。详细版本变化见 `CHANGELOG.md`，当前能力清单见 `docs/current-features.md`。

当前版本：`0.15.1`

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
- `0.9.2`: Strict Tool Input Validation / 严格工具输入校验
- `0.9.3`: Project Question Read Strategy / 项目问答读取策略
- `0.9.4`: Project Answer Compression / 项目问答输出收敛
- `0.9.5`: Manual Usage Review / 手动使用复查
- `0.9.6`: Tool Result Display Compact / 工具结果展示收敛
- `0.9.7`: Shell Execution UX / Shell 执行体验收敛
- `0.9.8`: Direct File Task UX / 明确文件任务体验收敛
- `0.9.9`: Direct File Tool Gating / 明确文件任务工具门控
- `0.10.0`: Project Read Strategy Hardening / 项目读取策略硬化
- `0.10.1`: Visible Tool Enforcement / 可见工具执行校验
- `0.10.2`: Create Intent Recognition / 创建意图识别补强
- `0.10.3`: Output Style Review / 输出风格复查
- `0.10.4`: Architecture Answer Accuracy Review / 架构问答准确性复查
- `0.10.5`: 0.10 Line Review / 0.10 主线复查
- `0.11.0`: Context Compact Real-World Review / 上下文压缩真实复查
- `0.11.1`: Summary Boundary Review / 摘要边界复查
- `0.11.2`: Tool Result Compact Policy Review / 工具结果压缩策略复查
- `0.11.3`: Context / TaskState Relationship Review / 上下文与任务状态关系复查
- `0.11.4`: Context Line Review / 上下文主线收尾复查
- `0.12.0`: Runtime Boundary Slim Review / Runtime 边界减重复查
- `0.12.1`: Runtime Prompt Boundary Review / Runtime 提示词边界复查
- `0.12.2`: Runtime State Boundary Review / Runtime 状态边界复查
- `0.12.3`: Runtime Line Review / Runtime 主线收尾复查
- `0.13.0`: Tool Boundary Line Review / 工具系统边界主线复查
- `0.13.1`: Builtin Tools Shape Review / 内置工具形态复查
- `0.13.2`: Tool Input Schema Review / 工具输入 Schema 复查
- `0.13.3`: Tool Error Surface Review / 工具错误表现复查
- `0.13.4`: Tool Line Review / 工具系统主线收尾复查
- `0.14.0`: Subagent Boundary Line Review / 子 Agent 边界主线复查
- `0.14.1`: Subagent Prompt Boundary Review / 子 Agent 提示词边界复查
- `0.14.2`: Subagent Finalization Review / 子 Agent 兜底总结复查
- `0.14.3`: Subagent Line Review / 子 Agent 主线收尾复查
- `0.15.0`: Real Usage Acceptance Review / 真实使用验收复查
- `0.15.1`: Acceptance Follow-up Review / 验收跟进复查

## 架构减重审视

结论：当前架构主线仍然清楚，但文档和后续规划已经有变重趋势。下一阶段应少加功能，先保持项目轻。

### 保留

- `AgentRuntime`: 仍作为主循环协调器，只拆出已经形成独立责任的兼容逻辑。
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
- `runtime.py` 已拆出事件展示、工具执行和伪工具调用解析；剩余复杂度主要来自主循环协调和上下文处理。
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

这些差异是可接受的：本项目目标是 mini-claude，即轻量级工程化地实现 Claude 的核心架构，而不是复制完整产品复杂度。当前最需要警惕的不是“功能不够多”，而是主循环边界变重。后续新增能力应优先围绕“让主循环更清楚、更可维护”展开。

## 下一步

### P1 / `0.15.2`: Acceptance Summary / 验收阶段总结

目标：总结 0.15.x 真实使用验收结果，判断是否进入下一条架构主线或继续真实场景验收。

作用：

- 0.15.0 / 0.15.1 已验证项目问答、文件任务、错误恢复和泛学习边界。
- 如果没有明显高收益问题，应先总结阶段结论，而不是为了版本继续加功能。
- 继续保持轻量工程化，避免凭空新增模块。

### 已完成 / `0.15.1`: Acceptance Follow-up Review / 验收跟进复查

目标：继续观察真实 CLI 使用中是否还有高收益小问题，优先修体验问题，不新增架构主线。

作用：

- 0.15.0 已完成第一轮真实使用验收并修复两个具体问题。
- 0.15.1 继续跟进真实使用暴露的问题。
- 本轮未发现必须改代码的问题，只修正 CLI 项目的交付流程文档。

结果：

- 跟进“Agent Loop”后续问题：能沿用上下文回答，未重复读文档。
- 错误命令场景：能清楚显示 exit 127 和 command not found。
- 泛学习 agent 场景：保持短回答，未调用工具。
- `PROJECT_PRINCIPLES.md` 已明确：本项目是 CLI，不需要重启；代码改动后做测试和必要 CLI 烟测。

### 已完成 / `0.15.0`: Real Usage Acceptance Review / 真实使用验收复查

目标：用真实 CLI 场景复查 mini-claude 当前体验，优先发现高收益问题，而不是继续扩展架构。

作用：

- Runtime、工具系统、上下文、子 Agent 主线都已阶段性收尾。
- 下一步更适合回到真实使用，看项目问答、文件编辑、测试运行、错误恢复是否顺滑。
- 只修真实体验暴露的问题，不预设新增大模块。

结果：

- 验收“当前版本有什么功能”：只读 `docs/current-features.md`，输出收敛，通过。
- 验收“创建 hello.py 并运行”：未先 `list_files`，直接写文件并用 `python3` 运行，通过。
- 验收“现在的 Agent Loop 怎么做”：发现误走泛化回答，已将 `Agent Loop / 主循环 / 对话循环` 归为项目文档入口问题。
- 验收“我想学习 Python”：确认不调用工具，但回答偏长，已收紧泛学习输出到 3-5 行。

### 已完成 / `0.14.3`: Subagent Line Review / 子 Agent 主线收尾复查

目标：复查 0.14.x 子 Agent 主线是否已经足够清楚，决定是否暂停继续改子 Agent。

作用：

- 0.14.x 已覆盖运行隔离、prompt 边界和兜底总结。
- 继续优化子 Agent 收益会降低，容易滑向复杂多 Agent 框架。
- 先做收尾复查，再转向真实使用验收或更高收益的问题。

结果：

- 子 Agent 当前保持固定三角色：Explore / Plan / Verification。
- 子 Agent 边界已覆盖只读隔离、不递归、短 prompt contract 和短兜底总结。
- 暂停继续扩展自定义 Agent、后台并行、独立模型、worktree 隔离或 JSON 输出解析。

### 已完成 / `0.14.2`: Subagent Finalization Review / 子 Agent 兜底总结复查

目标：复查子 Agent 达到轮次上限后的 finalization 是否仍然简单可靠。

作用：

- 0.14.0 固定运行隔离，0.14.1 固定 prompt 边界。
- 下一步只看“到达轮次上限后如何给主 Agent 一个可用总结”，避免隐藏失败或输出过长 transcript。
- 不新增复杂状态机，不做后台重试，不做多模型路由。

结果：

- finalizer 可用时仍优先把捕获 transcript 压成结构化最终答案。
- finalizer 失败时返回短 `Result: inconclusive`，只附少量最近证据。
- 不把长 transcript 直接返回给主 Agent。

### 已完成 / `0.14.1`: Subagent Prompt Boundary Review / 子 Agent 提示词边界复查

目标：复查 Explore / Plan / Verification 的 prompt 是否仍然短、稳定、角色清楚。

作用：

- 0.14.0 已固定子 Agent 的运行隔离边界。
- 下一步只看 prompt contract 是否足够清楚，避免通过提示词偷偷增加复杂流程。
- 不新增 Agent 类型，不做 JSON 输出解析，不做自定义 markdown agent。

结果：

- 三个子 Agent prompt 明确“不委托其他 Agent”。
- 继续使用短文本结构化输出，不改成 JSON 解析。
- 不抽象 prompt builder，避免为了消除少量重复而增加概念。

### 已完成 / `0.14.0`: Subagent Boundary Line Review / 子 Agent 边界主线复查

目标：复查 Explore / Plan / Verification 子 Agent 是否仍然保持只读、轻量、隔离，是否有继续扩展的必要。

作用：

- Runtime 和工具系统主线已经收尾，下一条 Claude-style 主线适合看 AgentTool / 子 Agent 边界。
- 当前已有 3 个内置只读子 Agent，需要确认它们没有变成隐藏的复杂执行框架。
- 先收紧边界，不急着新增 Agent 类型、自定义 markdown agent 或后台并行。

结果：

- 子 Agent 继续使用独立 runtime、独立 state、独立 task state 和只读工具集。
- 子 Agent 内部过滤 `explore_agent`、`plan_agent`、`verify_agent` 工具自身，避免递归 AgentTool 调用。
- 当前不扩展自定义 Agent、后台并行、独立模型或 worktree 隔离。

### 已完成 / `0.13.4`: Tool Line Review / 工具系统主线收尾复查

目标：复查 0.13.x 工具系统边界是否已经足够清楚，决定是否暂停继续改工具系统。

作用：

- 0.13.x 已经复查工具边界、内置工具形态、输入 schema 和错误表现。
- 继续优化工具系统收益变低，容易进入“为了优化而优化”。
- 结束工具系统主线，转向下一条 Claude-style 主线。

结果：

- 工具链路保持清楚：定义、注册、可见性、权限执行、结果包装各有边界。
- `builtin_tools.py` 保持单文件，不因较长而拆。
- 工具 schema 校验和错误展示已经补齐当前阶段需要的轻量边界。
- 暂不新增 Git 工具、MCP、复杂权限或插件系统。

### 已完成 / `0.13.3`: Tool Error Surface Review / 工具错误表现复查

目标：复查工具输入错误、权限错误、执行异常在 CLI 和模型上下文中的表现是否清楚。

作用：

- 0.13.2 已让 schema 校验更贴近工具声明。
- 检查错误返回是否足够可理解，避免模型或用户看到含糊的工具失败。
- 不引入复杂错误类型系统，只收敛 CLI 展示。

结果：

- 错误工具结果在 CLI 中显示为 `[tool_error] tool_name: ...`。
- 模型上下文中的 `tool_result` 内容不变，仍可继续用于下一轮修正。
- 保持 `tool_error` 事件和错误 `tool_result` 双路径，不新增错误总线。

### 已完成 / `0.13.2`: Tool Input Schema Review / 工具输入 Schema 复查

目标：复查内置工具的 JSON schema 是否清楚、一致，并与严格输入校验保持匹配。

作用：

- 0.13.1 已确认 `builtin_tools.py` 当前只是较长，不急着拆。
- 检查工具 schema 是否足够稳定，避免模型传入无效参数或隐藏参数。
- 不引入复杂 schema 框架，只做基础类型和 enum 校验。

结果：

- `Tool.validation_error()` 增加基础 JSON 类型校验：string、integer、boolean、array、object。
- `Tool.validation_error()` 增加 enum 校验。
- 新增测试覆盖类型不匹配、enum 不匹配和内置工具 schema 形态。

### 已完成 / `0.13.1`: Builtin Tools Shape Review / 内置工具形态复查

目标：复查 `builtin_tools.py` 是否仍然适合作为单文件内置工具集合，重点看是否需要文档化约束，而不是急着拆文件。

作用：

- `builtin_tools.py` 是当前工具系统最大的文件，但职责仍然单一：构造内置工具。
- 判断它目前只是“长”，不是已经“杂”。
- 先用测试固定工具集合形态，不急着拆文件，避免制造碎片化架构。

结果：

- 保持 `builtin_tools.py` 单文件，不新增 `file_tools.py` / `shell_tools.py` 等拆分。
- 明确它只承载内置工具构造和少量直接相关 helper。
- 新增工具集合形态测试，固定当前 11 个基础工具，防止内置工具悄悄变成杂物箱。

### 已完成 / `0.13.0`: Tool Boundary Line Review / 工具系统边界主线复查

目标：复查工具系统在当前阶段是否仍然清楚，重点看 `Tool`、`ToolRegistry`、`tool_policy`、`ToolTurnExecutor` 和内置工具之间的边界。

作用：

- Runtime 主线已经收尾，下一条更有价值的 Claude-style 主线是工具系统。
- Claude Code 的核心之一是工具定义、工具可见性、权限和执行边界分离；本项目已经有这些形状，但需要复查是否仍然轻量。
- 先 review，不急着新增工具或复杂权限。

结果：

- 工具链路保持清楚：`Tool` 定义工具，`ToolRegistry` 管工具集合，`tool_policy` 管可见性，`ToolTurnExecutor` 管权限、执行和结果包装。
- `ToolRegistry.read_only()` 只用于子 Agent 只读工具集过滤，当前不暴露依赖输入才可能只读的 `run_shell`。
- 新增测试固定只读工具集过滤边界。
- 暂不新增 Git 工具、MCP、复杂权限或插件系统。

### 已完成 / `0.12.3`: Runtime Line Review / Runtime 主线收尾复查

目标：复查 0.12.x 对 runtime 的减重是否已经足够，决定是否暂停继续改 runtime。

作用：

- 0.12.x 已经收敛了伪工具兼容、system prompt 和 state 命名，继续拆 runtime 的收益变低。
- 用测试、代码行数和文档检查确认 runtime 主线稳定。
- 避免继续为了优化而优化，结束 0.12 runtime 主线。

结果：

- `runtime.py` 保持 344 行，仍作为 `queryLoop` 风格协调器。
- 工具执行、伪工具调用解析、事件展示、intent 场景规则已经有独立边界。
- Runtime 相关测试和全量测试通过。
- 暂停继续拆 runtime，下一条主线转向工具系统边界复查。

### 已完成 / `0.12.2`: Runtime State Boundary Review / Runtime 状态边界复查

目标：复查 `AgentState` 当前保存的状态是否仍然必要、清楚，避免后续把临时流程变量都塞进 state。

作用：

- 防止 `AgentState` 变成临时变量堆放处。
- Claude-style agent loop 需要清楚区分对话历史、运行事件、当前 intent、上下文摘要、当前请求内计数和任务状态。
- 不新增 state 模块，只做命名收敛和边界测试。

结果：

- `project_question_tool_rounds` 改名为 `current_turn_tool_rounds`，表达它是当前用户请求内的工具轮次计数。
- 每次 `run_user_turn()` 开始都会重置该计数。
- 新增 runtime state 测试，固定当前请求内状态不会跨用户请求泄漏。

### 已完成 / `0.12.1`: Runtime Prompt Boundary Review / Runtime 提示词边界复查

目标：复查 `SYSTEM_PROMPT` 是否承担了过多行为约束，判断是否需要把稳定策略移到更清楚的策略边界。

作用：

- 防止把复杂度从 runtime 代码转移到一段越来越长的系统提示里。
- 让 system prompt 只保留高层运行原则，具体寒暄、泛学习、项目问答等场景约束继续由 `intent_prompt()` 注入。
- 不新增 prompt builder，避免为了整理 prompt 引入新抽象。

结果：

- 删除 system prompt 中已经由 intent 边界覆盖的寒暄和泛学习细则。
- 增加“遵循当前 intent guidance”的高层原则。
- 新增测试固定：system prompt 保持高层原则，不重复 intent-specific 规则。

### 已完成 / `0.12.0`: Runtime Boundary Slim Review / Runtime 边界减重复查

目标：复查 `AgentRuntime` 当前承担的职责，判断是否需要继续保持现状或做小幅边界整理。

作用：

- 让 runtime 回到 Claude-style `queryLoop` 协调器角色。
- 把模型误输出伪工具调用的兼容解析移出主循环，避免主循环继续堆 provider / markup 细节。
- 保持轻量拆分，不引入完整事件总线或 StreamingToolExecutor。

结果：

- 新增 `mini_agent/pseudo_tools.py`，负责伪工具调用解析、参数别名归一和 reasoning block 保留。
- `AgentRuntime` 只委托该模块，并继续负责可见工具集合和工具执行边界。
- 新增独立伪工具调用测试；全量测试通过。

### 已完成 / `0.11.4`: Context Line Review / 上下文主线收尾复查

目标：复查 0.11.x 上下文管理主线是否已经覆盖主要边界，决定是否收尾。

作用：

- 用少量测试和文档检查确认 compact、summary、TaskState 边界是否稳定。
- 如果没有明显问题，转向下一条更有价值的 Claude-style 主线。

结果：

- 上下文主线已覆盖 tool result budget、micro-compact、full compact、summary 注入、错误结果保留、TaskState 边界。
- 针对性上下文测试和全量测试通过。
- 暂不继续新增上下文功能，下一步转向 Runtime 边界减重复查。

### 已完成 / `0.11.3`: Context / TaskState Relationship Review / 上下文与任务状态关系复查

目标：明确 summary 和 TaskState 各自负责什么，避免重复或冲突。

作用：

- TaskState 保存当前任务进度，summary 保存压缩后的历史决策和上下文。
- 防止后续把 todo 状态也塞进 summary，或把历史摘要当成实时任务状态。

结果：

- system prompt 明确区分 `Current tasks (live task state)` 和 `Conversation summary so far (historical context, not the current task list)`。
- 测试固定 TaskState 和 summary 可以同时存在，且各自独立注入。

### 已完成 / `0.11.2`: Tool Result Compact Policy Review / 工具结果压缩策略复查

目标：复查哪些工具结果应该参与 micro-compact，哪些结果应该完整保留。

作用：

- 避免把任务状态、权限结果等低噪音但有语义的内容误压缩。
- 继续围绕上下文管理主线补边界测试，不引入复杂策略系统。

结果：

- task/todo 工具结果继续保留，不参与 micro-compact。
- 错误工具结果不再参与 micro-compact，方便排查失败原因。
- 测试固定默认保留最近 6 个可压缩工具结果。

### 已完成 / `0.11.1`: Summary Boundary Review / 摘要边界复查

目标：进一步明确 full compact 摘要应该保留哪些信息，哪些信息不应塞进摘要。

作用：

- 让 summary 和 TaskState 的职责更清楚。
- 防止摘要变成新的“巨型上下文”。
- 继续保持轻量，优先测试和 prompt 边界，不引入长期记忆系统。

结果：

- full compact prompt 明确保留用户目标、决策、文件路径、命令和未完成事项。
- full compact prompt 明确不要复制长工具输出、闲聊或重复细节。
- 测试固定 summary prompt 的保留和排除边界。

### 已完成 / `0.11.0`: Context Compact Real-World Review / 上下文压缩真实复查

目标：用更接近真实长对话的场景复查 tool result budget、micro-compact、full compact 和 summary 注入是否稳定。

作用：

- 0.10 项目问答主线已经基本稳定，下一步转向 Claude-style agent 的另一条核心主线：上下文管理。
- 优先做复查和少量测试，不急着引入复杂 token 预算器或长期记忆。

结果：

- 新增真实长任务 compact 测试。
- 验证 micro/full compact 后仍保留用户目标、关键文件路径、测试命令和未完成事项。
- 验证最近 4 条原始消息仍被保留，summary 注入路径仍可用。

### 已完成 / `0.10.5`: 0.10 Line Review / 0.10 主线复查

目标：复查 0.10.x 项目问答体验是否已经足够稳定，决定是否结束这一条主线。

作用：

- 用少量真实问题验收读取路径、回答长度、准确性和工具噪音。
- 如果没有明显问题，暂停继续微调项目问答，转向下一条更有价值的主线。

结果：

- 明确项目问题能按文档入口读取，模糊项目问题允许 `list_files`。
- 文件创建任务能直接请求 `write_file` 权限。
- 发现并修复工具数量回答不准的问题：当前 CLI 为 14 个模型可用工具，即 11 个基础工具 + 3 个只读子 Agent 工具。

### 已完成 / `0.10.4`: Architecture Answer Accuracy Review / 架构问答准确性复查

目标：复查“当前架构上分为几层？”这类问题的回答准确性，避免读了架构文档后把 8 层解释成 7 层。

结果：

- `docs/architecture.md` 明确写出当前架构分为 8 层。
- 明确 `Sub Agents` 是独立一层，不应合并到其他层。
- 项目问答 prompt 要求保留文档中的明确数字和有序列表。

### 已完成 / `0.10.3`: Output Style Review / 输出风格复查

目标：复查真实回答中仍偏长、偶尔使用 emoji 或过度结构化的问题。

结果：

- 项目问答 prompt 明确默认短答。
- 默认不使用 emoji、表格、目录树或额外学习链接。
- 明确要求始终给出可见最终回答。
- 隐藏工具误调用会转为内部引导结果，避免把普通用户暴露在 `Unknown tool` 噪音里。
- final response 只有最终文本、没有 text delta 时，CLI 也会展示答案。
- `下一步` 等文档入口问题即使没有显式项目词，也会走项目问答路径。
- 项目问答会优先选择最相关文档入口，避免先读 README 后再需要第二轮读 roadmap。

### 已完成 / `0.10.2`: Create Intent Recognition / 创建意图识别补强

目标：修复真实测试中发现的轻量意图问题：`创建 x.txt，内容是 x` 这类请求应进入 coding task，而不是被当成闲聊。

作用：

- 让中文创建文件请求更稳定地进入工具路径。
- 减少模型明明想写文件、runtime 却隐藏所有工具的错配。
- 保持范围很小，只调整 intent 关键词和测试，不新增模块。

结果：

- `创建` 进入 coding task 关键词。
- `创建 x.txt，内容是 x` 会识别为 coding task，并隐藏 `list_files`。
- 不带明确文件路径的创建请求仍进入普通 coding task，不提前隐藏探索工具。

### 已完成 / `0.10.1`: Visible Tool Enforcement / 可见工具执行校验

目标：修复 0.10.0 手动测试发现的问题：`list_files` 虽然从模型可见工具中隐藏，但模型如果仍输出该工具，执行层仍可能执行。

结果：

- runtime 执行工具前再次按当前 intent 过滤工具集合。
- 伪工具调用归一化也遵守当前可见工具集合。
- 明确项目问答中的隐藏 `list_files` 不能被绕过执行。

### 已完成 / Manual Usage Review / 手动使用复查

目标：用真实问题复查 0.10.0 的项目读取策略是否减少了无意义 `list_files`。

作用：

- 验证“项目结构是什么”是否直接读文档。
- 确认模糊项目问题仍能列目录。
- 决定 0.10 是否收尾，还是继续收紧项目问答。

结果：发现明确项目问题不会先列目录，但隐藏工具仍缺少执行层兜底，因此进入 `0.10.1` 修复。

### 已完成 / `0.10.0`: Project Read Strategy Hardening / 项目读取策略硬化

目标：让项目问答在目标文档明确时不再先 `list_files`。

结果：

- 项目结构、项目架构、当前功能、当前版本、下一步等问题会隐藏 `list_files`。
- 模糊问题如“看看这个项目”仍保留 `list_files`。
- 复用 `hidden_tools`，不新增 planner，不改工具执行层。

### 已完成 / `0.9.9`: Direct File Tool Gating / 明确文件任务工具门控

目标：修复明确文件任务仍可能先 `list_files` 的问题。

结果：

- `IntentDecision` 增加轻量 `hidden_tools`。
- 明确路径和内容的 coding task 会隐藏 `list_files`。
- 工具注册表测试确认这类任务看不到 `list_files`，但仍能使用 `write_file` 和 `run_shell`。

### 已完成 / `0.9.8`: Direct File Task UX / 明确文件任务体验收敛

目标：改善“创建明确文件并运行”这类任务的工具路径和展示噪音。

结果：

- coding task guidance 明确：用户给出路径和内容时直接写文件，不先 `list_files`。
- `list_files` 结果在 CLI 中显示摘要，避免目录列表刷屏。
- 不改变工具执行和权限管线。

### 已完成 / `0.9.7`: Shell Execution UX / Shell 执行体验收敛

目标：改善创建并运行 Python 脚本这类任务的交互体验。

结果：

- `run_shell` 结果在 CLI 中按 exit/stdout/stderr 展示，不再原样输出 JSON。
- 系统提示建议运行 Python 脚本时优先使用 `python3`。
- 不改变 shell 工具返回给模型的结构化内容。

### 已完成 / `0.9.6`: Tool Result Display Compact / 工具结果展示收敛

目标：长工具结果仍进入模型上下文，但 CLI 默认只展示摘要，避免读长文档时刷屏。

结果：

- 成功工具结果超过展示阈值时，CLI 显示一行摘要。
- 短工具结果照常展示。
- 错误工具结果保持完整展示，方便排查。

### 已完成 / `0.9.5`: Manual Usage Review / 手动使用复查

目标：用真实问题复查 0.9.x 的项目问答、工具输入校验、上下文行为和输出收敛效果，决定 0.9 是否收尾。

作用：

- 避免继续凭想象加功能。
- 发现真实用户使用中的输出噪音或工具误用。
- 为进入下一条主线前做轻量验收。

建议范围：

- 以手动案例和少量测试为主。
- 不新增大模块。
- 只修真实暴露的问题。

已观察到的手动验收结果：

- 寒暄和泛学习请求不调用工具，符合预期。
- 0.9.4 后泛学习回复明显更短，符合预期。
- “解释当前项目架构”仍会先 `list_files`，且会继续读取多份入口文档；读取策略仍需收紧。
- “当前版本有什么功能”没有额外调用工具，但回答仍偏完整清单。
- “下一步做什么”命中 `docs/roadmap.md`，但 CLI 会直接打印较长工具结果，用户感知仍偏吵。
- 写文件和运行脚本的权限路径正常；本轮直接使用 `python3` 成功运行。

下一步优先判断：先解决 CLI 工具结果展示噪音，再考虑继续收紧项目问答读取策略。

### 已完成 / `0.9.4`: Project Answer Compression / 项目问答输出收敛

目标：让项目问答默认只回答用户直接关心的内容，避免把读取到的文档大段复述出来。

结果：

- 项目问答 guidance 明确要求直接、简洁回答。
- 默认不复述整份文档、长历史或宽泛功能清单。
- 用户明确要求详细时再展开。

### 已完成 / `0.9.3`: Project Question Read Strategy / 项目问答读取策略

目标：复查“解释当前项目架构”这类问题的读取路径，让 agent 优先读少量入口文档，必要时再读代码。

作用：

- 减少无关文件读取，降低上下文消耗。
- 让项目问答更像 Claude 的按需探索，而不是一次性扫描。
- 保持实现轻量，不引入复杂规划器。

建议范围：

- 项目问答 guidance 优先推荐 `README.md`、`docs/context-map.md`、`docs/architecture.md`、`docs/current-features.md`、`docs/roadmap.md`。
- 明确只有目标文件不清楚时才使用 `list_files`。
- 新增 system prompt 边界测试。

### 已完成 / `0.9.2`: Strict Tool Input Validation / 严格工具输入校验

目标：让工具调用输入严格符合工具 schema，避免模型传入未知字段却被静默忽略。

结果：

- `Tool` 统一校验未知字段和必填字段。
- `ToolTurnExecutor` 使用统一校验入口。
- 伪工具调用的 `file_path` 别名会归一为 `path`，不再残留旧字段。
- 新增工具输入边界测试。

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
