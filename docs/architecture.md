# Architecture

这份文档只记录稳定架构。具体版本变化看 `CHANGELOG.md`，当前能力清单看 `docs/current-features.md`，下一步计划看 `docs/roadmap.md`。

## 目标

本项目是 mini-claude：一个参考 Claude Code 的轻量级工程化 agent。目标不是完整复刻 Claude Code，而是在较小代码量里保留它的核心架构形状：

```text
用户目标 -> Agent Loop -> LLM -> 工具调用 -> 权限/校验 -> 本地执行 -> 工具结果 -> 下一轮推理
```

实现可以轻量，但概念边界尽量对齐 Claude Code。

## 分层

```text
CLI / Config
  -> agent.py
  -> config.py / settings.py

Agent Runtime
  -> runtime.py
  -> AgentState
  -> events.py

Tool Execution
  -> tool_executor.py

LLM Adapter
  -> llm.py

Intent / Tool Visibility
  -> intent.py
  -> tool_policy.py

Tool System
  -> tool_core.py
  -> builtin_tools.py
  -> tool_registry.py
  -> workspace.py
  -> permissions.py

Context / Task State
  -> context.py
  -> tasks.py

Sub Agents
  -> subagent.py
```

## 核心模块

### `agent.py`

CLI 入口。负责加载 `.env`、解析参数、创建 LLM client、权限规则和 `AgentRuntime`。

### `mini_agent.runtime`

主循环协调器，对应 Claude 的 `queryLoop`：

- 保存对话状态和任务状态
- 判断当前 intent
- 将主循环拆成 begin turn、record assistant、final answer、tool turn 等阶段
- 根据工具策略暴露工具 schema
- 调用模型并消费流式输出
- 产生轻量运行时事件
- 通过 `tool_error`、`model_error`、`turn_limit_reached` 标记轻量错误恢复路径
- 识别真实 `tool_use` 和少量伪工具调用标记
- 调度工具轮次并写入 `tool_result`
- 必要时触发 micro/full compact

当前 `runtime.py` 承载了较多兼容逻辑，是后续最需要保持克制的模块。

### `mini_agent.tool_executor`

工具轮次执行器，对应 Claude 工具执行服务 / StreamingToolExecutor 的简化边界：

- 接收一轮 `tool_use`
- 判断是否可以并发执行
- 做工具输入校验、权限判断和用户确认
- 执行工具并组装 `tool_result`
- 将工具错误统一转成 `tool_error` 事件和错误 `tool_result`
- 按 Claude `partitionToolCalls()` 思想做轻量批次分区：连续并发安全工具并发，不安全工具串行

当前决策：暂不实现流中工具执行，也不改变 tool result 格式。

### `mini_agent.events`

轻量运行时事件层，对应 Claude `queryLoop` / AsyncGenerator 的事件化思想：

- `RuntimeEvent`: 描述 runtime 中发生的事情
- `EventHandler`: CLI 或测试可消费事件
- `PermissionRequestHandler`: CLI 或测试可接管权限确认
- `print_runtime_event()`: 默认 CLI 打印器

当前只做轻量边界拆分：runtime 产生事件，CLI 展示事件；不做完整事件总线，也不做 StreamingToolExecutor。

### `mini_agent.llm`

LLM provider 适配层。统一 Anthropic 和 OpenAI-compatible provider 的消息、工具调用、streaming event 和 `reasoning_content` 续传。

对应 Claude 的模型请求边界：runtime 不直接依赖某个 SDK 返回格式。

### `mini_agent.tool_core` / `builtin_tools` / `tool_registry`

工具系统，对应 Claude 的 `buildTool()` 思路：

- `Tool`: 工具元信息、schema、输入校验和执行函数
- `build_tool()`: 工具构造入口
- `builtin_tools`: 文件、搜索、shell、task 等内置工具
- `ToolRegistry`: 当前 runtime 可用工具集合
- 工具结果预算：大输出在进入上下文前被截断，保留开头、结尾和截断说明

工具定义回答“怎么执行”，注册表回答“有哪些工具”。

### `mini_agent.intent` / `tool_policy`

工具可见性边界：

- `intent.py`: 判断寒暄、泛学习、项目问题、编码任务、危险请求
- `tool_policy.py`: 决定本轮模型能看到哪些工具

这样可以避免简单聊天或泛学习问题误触发读文件、shell 或子 Agent。

### `mini_agent.permissions` / `workspace`

本地安全边界：

- `workspace.py`: 限制文件路径在 workspace 内
- `permissions.py`: 根据权限模式、规则和工具风险决定 allow / ask / deny
- 工具输入校验在权限判断前执行

当前是轻量权限管线，不追求 Claude 完整复杂度。

### `mini_agent.context`

上下文管理：

- micro-compact：不调用模型，只压缩旧工具结果
- full compact：仍超预算时让模型总结旧历史

对应 Claude 的分层上下文压缩思想。

### `mini_agent.subagent`

AgentTool 风格的内置只读子 Agent：

- `explore_agent`
- `plan_agent`
- `verify_agent`

子 Agent 使用独立 runtime、独立 state、只读工具集。主 Agent 只接收最终总结，避免把探索过程全部塞进主上下文。

## 主要数据流

### 一次用户请求

```text
run_user_turn()
  -> classify_intent()
  -> begin_turn()
  -> compact_if_needed()
  -> LLMClient.stream_complete()
  -> normalize pseudo tool calls
  -> record_assistant_response()
  -> if tool_use: handle_tool_turn()
  -> if no tool_use: handle_final_answer()
  -> if max turns exhausted: emit turn_limit_reached / stopped
```

### 子 Agent

```text
main agent
  -> model calls explore_agent / plan_agent / verify_agent
  -> isolated sub AgentRuntime
  -> read-only tools
  -> final summary only
  -> main agent continues
```

### 上下文压缩

```text
messages over budget
  -> micro_compact old tool results
  -> if still over budget: full compact with summary
  -> keep recent raw messages
```

## 与 Claude 的对齐和简化

已对齐：

- `queryLoop` 风格主循环
- lightweight runtime events
- provider 适配层
- `buildTool()` 风格工具抽象
- 权限/工具门控管线
- micro/full compact
- tool result budget
- AgentTool 风格子 Agent

mini-claude 的轻量化取舍：

- 没有 StreamingToolExecutor
- 没有完整事件总线
- 没有 MCP / 插件工具发现
- 没有自定义 `.claude/agents`
- 没有后台并行子 Agent
- 没有复杂 TUI、hooks、settings 合并和精确 token 预算
