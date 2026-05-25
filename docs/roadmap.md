# Roadmap

这份文档只记录方向、取舍和下一步。详细版本变化见 `CHANGELOG.md`，当前能力清单见 `docs/current-features.md`。

当前版本：`0.19.0`

## 当前进展

mini-claude 当前已经具备一个可学习、可运行的 Claude-style agent 骨架：

- Agent Loop：多轮模型调用、工具调用、工具结果回传、轻量错误恢复。
- LLM Adapter：Anthropic / OpenAI-compatible 适配，支持 streaming 和 `reasoning_content` 续传。
- Tool System：统一 `Tool` 抽象、schema、输入校验、工具注册、工具可见性和工具执行器。
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

### P1 / `0.20.0`: Tool Choice Strategy / 工具选择策略

目标：让 agent 更清楚什么时候该用工具、该暴露哪些工具、该优先读什么上下文。

作用：

- 这是 agent 核心设计，不是外围工程能力。
- 当前已经有 `intent.py`、`tool_policy.py` 和项目问答读取策略，但规则散在多个位置。
- 下一步应把“意图 -> 工具可见性 -> 工具选择提示”这条链路收紧，减少不必要工具调用和错误工具顺序。

计划范围：

- 不新增工具。
- 不新增 planner 架构层。
- 不做 session save / resume。
- 优先补轻量策略说明和边界测试。
- 重点固定这些行为：
  - 寒暄和泛学习不暴露工具。
  - 项目架构问题优先读 `docs/architecture.md`。
  - 当前功能问题优先读 `docs/current-features.md`。
  - 下一步计划问题优先读 `docs/roadmap.md`。
  - 明确文件创建任务不先 `list_files`。
  - 路径或目标不清楚时才使用 `list_files` / `search_text`。

## 暂缓项

- Session Save / Resume：Claude 有这个能力，但当前更偏产品工程，先暂停。
- StreamingToolExecutor：架构上重要，但会明显增加调度复杂度。
- MCP / 插件工具发现：等工具系统主线更稳定后再看。
- Git 专用工具：当前收益不够高，继续使用 shell 的保守只读识别。
- 自定义 Agent markdown：会扩大子 Agent 系统复杂度，暂缓。
- 复杂终端 UI / TUI：当前 CLI 足够支撑学习和验证。
