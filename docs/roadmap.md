# Roadmap

这份文档只记录方向、取舍和下一步。详细版本变化见 `CHANGELOG.md`，当前能力清单见 `docs/current-features.md`。

当前版本：`0.25.0`

## 当前进展

mini-claude 当前已经具备一个可学习、可运行的 Claude-style agent 骨架：

- Agent Loop：多轮模型调用、工具调用、工具结果回传、轻量错误恢复。
- LLM Adapter：Anthropic / OpenAI-compatible 适配，支持 streaming 和 `reasoning_content` 续传。
- Tool System：统一 `Tool` 抽象、schema、输入校验、工具注册、工具可见性和工具执行器。
- Tool Choice：intent prompt 注入轻量工具选择策略，项目入口问题优先读对应文档。
- Working State：澄清问题后的用户补充、写作任务继续追加可继承上一轮任务意图。
- Permission Pipeline：工作区边界、权限模式、权限规则、危险操作确认和拒绝后防绕路。
- Context：tool result budget、micro-compact、full compact、summary 注入。
- Sub Agents：固定内置的 `explore_agent`、`plan_agent`、`verify_agent`，只读隔离执行。
- Task/Todo：轻量 `TaskState`，多步骤任务可用 todo 推进，CLI 显示 `[tasks]` 区块。
- CLI Output：工具过程可见但收敛，读文件和搜索结果默认摘要展示。

## 与 Claude 的对齐

已对齐的核心思想：

- `queryLoop` 风格主循环。
- 模型 provider 适配层。
- `buildTool()` 风格工具抽象。
- 工具可见性和权限管线。
- 上下文压缩分层：原始消息、工具结果预算、历史 summary、当前 task state。
- AgentTool 风格子 Agent：隔离上下文，只返回精炼结果。
- 任务状态辅助长任务推进。
- 当前任务状态参与下一轮 intent resolution，避免把补充参数误判成新闲聊。

## 与 Claude 的差异

这些是 mini-claude 的刻意简化：

- 没有 StreamingToolExecutor：当前等模型一轮输出结束后再执行工具。
- 没有完整事件总线：只有轻量 `RuntimeEvent` 和 CLI 打印器。
- 没有 MCP / 插件工具发现：工具仍是本地静态注册。
- 没有复杂 TUI：只保留 CLI。
- 没有自定义 `.claude/agents`、后台并行子 Agent、独立模型或 worktree 隔离。
- 没有 Claude 完整任务系统：不做后台任务、任务通知、任务清理和并发任务引擎。
- 没有 session resume：先不做会话保存与恢复，避免偏向产品工程。
- 没有复杂 token 预算器、长期记忆或向量库。

当前判断：这些差异是可接受的。项目目标是 mini-claude，不是完整 Claude Code 复刻。下一步应继续围绕 agent 如何决策、如何选择工具、如何保持上下文边界来推进。

## 架构减重审视

当前代码边界总体还清楚：

- `runtime.py` 已经拆出事件展示、工具执行和伪工具解析，暂不继续拆。
- `builtin_tools.py` 和 `llm.py` 较大，但职责仍单一，暂不拆。
- `subagent.py` 较长但角色固定，暂不新增更多子 Agent。
- `docs/architecture.md` 和 `docs/current-features.md` 偏长，但仍是稳定入口，后续只做必要更新。
- `docs/roadmap.md` 已完成减重：历史细节交给 `CHANGELOG.md`。

继续遵守：

- 不为优化而优化。
- 不因复查制造新层。
- 不把 Claude 的重工程能力照搬进 mini-claude。
- 新功能优先复用现有边界。

## 下一步

### P1 / `0.26.0`: Focused Streaming Review / 流式边界复查

目标：复查当前“文本流式 + 工具整轮执行”的边界是否需要继续保持。

作用：

- 当前不是完整 Claude StreamingToolExecutor，而是轻量半流式。
- 下一步只做边界评估和测试，不急着实现流中工具执行。

### 已完成 / `0.25.0`: Context Stress Acceptance / 上下文压力验收

目标：验收长对话、工具结果压缩、WorkingState、TaskState 和 summary 注入是否能稳定共存。

作用：

- 上下文管理是 Claude-style agent 长任务能力的核心。
- 当前已有 micro-compact、full compact、summary、TaskState 和 WorkingState，本次只验证组合稳定性，不新增 memory 系统。

结果：

- 新增压力测试：compact 后 pending task 仍能继承 coding task。
- 新增压力测试：full compact 后 TaskState 仍作为 live task state 独立注入，不与 historical summary 混合。
- 验证 micro/full compact 可以和 WorkingState、TaskState 一起工作。
- 不新增长期记忆、向量库、session resume 或复杂 token 预算器。

### 已完成 / `0.24.3`: Architecture Slim Review / 架构减重复查

目标：审视当前分层和代码规模，做必要的小命名和路线图收敛。

作用：

- 保持 mini-claude 简洁，避免为了优化继续拆碎架构。
- 让 WorkingState 的命名更准确，避免误解它只处理“等待用户”。

结果：

- `should_wait_for_user()` 改名为 `should_keep_pending_task()`，覆盖澄清等待和继续追加两个语义。
- 保持 `runtime.py`、`tool_executor.py`、`working_state.py` 等现有边界，不做新层。
- 将已完成的真实 CLI 长对话验收从下一步中移出，下一步转为流式边界复查。
- 不拆 `runtime.py`、`builtin_tools.py`、`llm.py` 或 `subagent.py`。

### 已完成 / `0.24.2`: Permission Edit Acceptance / 编辑权限体验验收

目标：复查并修复 `acceptEdits` 下 `apply_edit` 的权限体验。

作用：

- `apply_edit` 是工作区编辑工具，和 `write_file`、`edit_file` 一样应在 `acceptEdits` 下自动允许。
- 这能避免长对话续写时被权限确认打断。

结果：

- `acceptEdits` 自动允许 `write_file`、`edit_file`、`apply_edit`。
- Shell 和其他非编辑操作仍按原策略确认。
- 新增权限和工具执行测试，确认 `apply_edit` 不触发 `permission_request`。
- 不新增权限模式，不改复杂权限系统。

### 已完成 / `0.24.1`: Pending Task Real Usage Fix / 短期任务真实使用修复

目标：修复真实 CLI 长对话中“只读预检后追问”和“继续追加”导致 pending task 断掉的问题。

作用：

- 0.24.0 已加入 WorkingState，但真实模型可能先 `list_files` 再追问，不能把只读工具当成任务完成。
- 写作任务完成一批后，用户说“继续/追加”也应该继承当前文件任务。

结果：

- Runtime 改为区分只读工具和非只读工具；只读预检不会阻止进入 pending。
- 写入类工具仍会标记为 mutating，避免无边界继承。
- final answer 中出现继续/追加信号时，会保留短期 pending，支持下一轮继续写。
- 真实 CLI 长对话验收通过：补充参数后真实 `write_file`，继续后真实追加写入，切换项目问题正常读架构文档。
- 不做长期记忆、任务队列或 planner。

### 已完成 / `0.24.0`: Working State For Pending Task / 短期任务意图延续

目标：让 Agent 能理解“用户第二轮是在补充上一轮未完成任务”，尤其是创作型保存文件任务。

作用：

- 这更贴近 Claude-style agent loop：当前任务状态参与下一轮决策，而不是每轮孤立分类。
- 修复“保存为文件后追问，用户补充参数却被当成闲聊”的问题。

结果：

- 新增 `mini_agent/working_state.py`，保存当前 runtime 内的单个 pending task。
- Runtime 使用 `WorkingState.resolve_intent()`，在用户补充参数时继承上一轮 coding task。
- 工具执行、用户取消或任务完成后清空 pending 状态。
- “保存为文件 / 写成文件 / 输出到文件”等创作型文件请求会进入 coding task。
- coding task guidance 增加超长内容分批写入文件策略。
- 不做长期记忆、session resume、多任务队列、planner 或专用小说生成器。

### 候选 / `0.23.1`: Subagent Context Acceptance / 子 Agent 上下文验收

目标：用测试和一次真实模拟任务验收子 Agent 上下文策略是否足够稳定。

作用：

- 0.23.0 已把子任务输入、内部 transcript 和返回结果预算写进代码。
- 后续可验证真实项目问答和长 transcript 情况，不新增子 Agent 类型或复杂多 Agent 能力。

### 已完成 / `0.23.0`: Subagent Context Policy / 子 Agent 上下文策略

目标：复查并收紧子 Agent 的上下文隔离、工具暴露、结果回传和失败兜底策略。

作用：

- 子 Agent 是 Claude-style 架构中的重要能力，但也是最容易膨胀的一条线。
- 本次保留固定只读 `explore_agent`、`plan_agent`、`verify_agent`，只把上下文边界显式化。

结果：

- 新增子 Agent 上下文策略提示：内部探索留在子 Agent，本轮只返回最终结构化摘要。
- 新增子任务输入预算，避免主 Agent 把过长上下文直接塞给子 Agent。
- 新增内部 transcript 预算，避免超限 finalization 再次携带过长过程。
- 新增子 Agent 工具返回预算，避免最终摘要污染主上下文。
- 新增测试覆盖 oversized task、trimmed transcript 和 compact result budget。
- 不新增自定义 agent、后台并行、独立模型、worktree 隔离或子 Agent 间通信。

### 已完成 / `0.22.1`: Context Budget Acceptance / 上下文预算验收

目标：用现有测试和少量模拟长任务验收上下文预算策略是否足够稳定。

作用：

- 0.22.0 已集中表达 micro-compact 的默认保留数量和可压缩工具集合。
- 下一步只验收长任务、错误结果、task state 和 summary 注入，不新增复杂 memory 系统。

结果：

- 上下文相关测试覆盖旧工具结果清理、最近工具结果保留、错误结果保留、task 工具结果保留、孤立 tool_result 保留。
- Runtime 压缩测试覆盖 micro-compact 先于 full compact、summary 注入、summary 和 TaskState 分离、真实长任务关键上下文保留。
- 全量测试通过，确认当前上下文预算策略够用。
- 暂不新增 token 精确预算、长期记忆、向量库或 session resume。

### 已完成 / `0.22.0`: Context Budget Policy / 上下文预算策略

目标：复查当前 context budget、tool result budget、micro-compact 和 full compact 的策略边界。

作用：

- LLM Adapter 主线已稳定，下一条更贴近 agent 核心的是上下文预算。
- Claude Code 对上下文预算、工具结果裁剪和摘要注入非常重视；mini-claude 已有轻量实现，但策略还可以更清楚。
- 本次优先复查策略和测试，不引入向量库、长期记忆或复杂 token 预算器。

结果：

- 新增 `DEFAULT_KEEP_RECENT_TOOL_RESULTS`，明确 micro-compact 默认保留最近 6 个可压缩工具结果。
- `COMPACTABLE_TOOL_NAMES` 增加注释，明确只包含高噪音成功工具结果。
- 新增测试固定 task/todo 工具不在默认可压缩集合中。
- 不改变 compact 流程，不引入 token 精确预算、长期记忆或向量库。

### 已完成 / `0.21.1`: LLM Adapter Acceptance / 模型适配验收

目标：用现有测试和少量模拟场景验收 LLM Adapter 协议边界是否足够稳定。

作用：

- 0.21.0 已补协议护栏测试，下一步只确认真实/模拟路径是否覆盖当前风险。
- 如果没有新问题，结束 LLM Adapter 主线，不做 provider 框架或多模型路由。

结果：

- `tests/test_llm_adapter.py` 覆盖消息转换、工具调用、工具结果、reasoning 续传、streaming 空 `choices`、无效工具参数降级。
- 手动模拟 streaming 同时包含 text、reasoning、tool_call 和空 `choices`，最终内部 blocks 重建正常。
- LLM Adapter 主线当前够用，暂不新增 provider 框架、多模型路由或复杂 retry/backoff。

### 已完成 / `0.21.0`: LLM Adapter Protocol Review / 模型适配协议复查

目标：复查 Anthropic / OpenAI-compatible 适配层对消息、工具调用、工具结果、streaming 和 reasoning 续传的统一边界。

作用：

- LLM Adapter 是 agent loop 和具体模型 API 之间的协议层，直接影响工具调用是否稳定。
- 本项目已经遇到过 `reasoning_content` 续传和 OpenAI-compatible streaming 空 `choices` 问题，说明这条边界值得系统化收紧。
- 本次优先补协议边界测试，不引入多模型路由或复杂 provider 框架。

结果：

- 补充 `model_extra.reasoning_content` 进入 `ReasoningBlock` 的测试。
- 补充无效 JSON 工具参数降级为 `raw_arguments` 的测试。
- 更新 LLM Adapter 文档，修正 streaming 状态说明。
- 未拆分 `llm.py`，未新增 provider，未引入多模型路由。

### 已完成 / `0.20.1`: Tool Choice Acceptance / 工具选择验收

目标：用真实 CLI 场景验收工具选择策略是否减少了无意义工具调用。

作用：

- 0.20.0 已把策略从散落 prompt 收敛为 `tool_choice_guidance()`。
- 下一步应观察真实问题：项目架构、当前功能、怎么启动、明确文件创建、泛学习。
- 如果真实体验稳定，就结束工具选择主线，不继续加 planner。

结果：

- 泛学习请求没有调用工具。
- “怎么启动”直接读取 `docs/current-features.md`，没有先 `list_files` 或 `search_text`。
- “当前架构上分为几层”直接读取 `docs/architecture.md`，回答保留明确数字。
- “当前功能有哪些”直接读取 `docs/current-features.md`。
- 明确文件创建并运行任务直接使用 `write_file` 和 `run_shell`，没有先 `list_files`。
- 工具选择主线当前够用，暂不继续加 planner。

### 已完成 / `0.20.0`: Tool Choice Strategy / 工具选择策略

目标：让 agent 更清楚什么时候该用工具、该暴露哪些工具、该优先读什么上下文。

作用：

- 这是 agent 核心设计，不是外围工程能力。
- 当前已经有 `intent.py`、`tool_policy.py` 和项目问答读取策略，但规则散在多个位置。
- 本次把“意图 -> 工具可见性 -> 工具选择提示”这条链路收紧，减少不必要工具调用和错误工具顺序。

结果：

- 新增 `tool_choice_guidance()`，由 `intent_prompt()` 注入模型上下文。
- 项目入口问题继续隐藏 `list_files` / `search_text`，优先用 `read_file` 读文档。
- “怎么启动 / 如何启动 / 启动方式”会稳定归类为项目文档入口问题，优先读 `docs/current-features.md`。
- 显式请求某个工具时，策略提示只使用该工具。
- 未新增工具、planner 架构层或 session resume。

## 暂缓项

- Session Save / Resume：Claude 有这个能力，但当前更偏产品工程，先暂停。
- StreamingToolExecutor：架构上重要，但会明显增加调度复杂度。
- MCP / 插件工具发现：等工具系统主线更稳定后再看。
- Git 专用工具：当前收益不够高，继续使用 shell 的保守只读识别。
- 自定义 Agent markdown：会扩大子 Agent 系统复杂度，暂缓。
- 复杂终端 UI / TUI：当前 CLI 足够支撑学习和验证。
