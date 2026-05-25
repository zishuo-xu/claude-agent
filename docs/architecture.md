# Architecture

这份文档只记录稳定架构。具体版本变化看 `CHANGELOG.md`，当前能力清单看 `docs/current-features.md`，下一步计划看 `docs/roadmap.md`。

## 目标

本项目是 mini-claude：一个参考 Claude Code 的轻量级工程化 agent。目标不是完整复刻 Claude Code，而是在较小代码量里保留它的核心架构形状：

```text
用户目标 -> Agent Loop -> LLM -> 工具调用 -> 权限/校验 -> 本地执行 -> 工具结果 -> 下一轮推理
```

实现可以轻量，但概念边界尽量对齐 Claude Code。

## 分层

当前架构明确分为 8 层，`Sub Agents` 是独立一层，不应合并到其他层：

```text
CLI / Config
  -> agent.py
  -> config.py / settings.py

Agent Runtime
  -> runtime.py
  -> AgentState
  -> events.py
  -> pseudo_tools.py

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
- `AgentState` 保存对话历史、事件、轮次、当前 intent、上下文摘要和当前请求内工具轮次
- 判断当前 intent
- 将主循环拆成 begin turn、record assistant、final answer、tool turn 等阶段
- 根据工具策略暴露工具 schema
- 调用模型并消费流式输出
- system prompt 保留高层运行原则，具体场景约束由 `intent_prompt()` 注入
- 模型输入动态拼接边界固定为：base system、workspace、intent、historical summary、live task state、messages/tool results
- 产生轻量运行时事件
- 通过 `tool_error`、`model_error`、`turn_limit_reached` 标记轻量错误恢复路径
- 委托 `pseudo_tools.py` 识别少量伪工具调用标记
- 调度工具轮次并写入 `tool_result`
- 必要时触发 micro/full compact

当前 `runtime.py` 保留主循环协调职责；模型输出兼容、工具执行、事件展示等细节应尽量留在独立边界内。

### `mini_agent.pseudo_tools`

模型输出兼容边界：

- 识别少量 XML/JSON/function 风格伪工具调用标记
- 将可见工具范围内的伪工具调用转成内部 `ToolUseBlock`
- 保留 reasoning block，避免 thinking provider 下一轮丢失推理续传信息
- 隐藏工具不归一化，继续由 runtime 的可见工具边界约束

它是 Runtime 的辅助边界，不是新的工具系统。

### `mini_agent.tool_executor`

工具轮次执行器，对应 Claude 工具执行服务 / StreamingToolExecutor 的简化边界：

- 接收一轮 `tool_use`
- 判断是否可以并发执行
- 做工具输入校验、权限判断和用户确认
- 执行工具并组装 `tool_result`
- 将工具错误统一转成 `tool_error` 事件和错误 `tool_result`
- 按 Claude `partitionToolCalls()` 思想做轻量批次分区：连续并发安全工具并发，不安全工具串行
- 发出 `tool_batch_start` / `tool_batch_end`，让事件流表达批次边界

当前决策：暂不实现流中工具执行，也不改变 tool result 格式。

### `mini_agent.events`

轻量运行时事件层，对应 Claude `queryLoop` / AsyncGenerator 的事件化思想：

- `RuntimeEvent`: 描述 runtime 中发生的事情
- `EventHandler`: CLI 或测试可消费事件
- `PermissionRequestHandler`: CLI 或测试可接管权限确认
- `print_runtime_event()`: 默认 CLI 打印器
- 权限确认由 `prompt_permission_request()` 集中展示，避免事件打印和输入提示重复
- `read_file` / `search_text` 成功结果在 CLI 中只显示摘要，模型上下文仍保留完整工具结果
- 错误工具结果在 CLI 中带 `[tool_error]` 前缀展示，模型上下文仍保留原始错误内容
- `run_shell` 展示会被格式化为 exit/stdout/stderr，避免把 JSON 直接暴露给用户
- `list_files` 展示会被压缩成条目数和少量预览，避免目录刷屏

当前只做轻量边界拆分：runtime 产生事件，CLI 展示事件；不做完整事件总线，也不做 StreamingToolExecutor。

### `mini_agent.llm`

LLM provider 适配层。统一 Anthropic 和 OpenAI-compatible provider 的消息、工具调用、streaming event 和 `reasoning_content` 续传。
OpenAI-compatible 无效工具参数会降级为 `raw_arguments`，streaming 空 `choices` chunk 会跳过，避免 provider 边界噪音进入 runtime。

对应 Claude 的模型请求边界：runtime 不直接依赖某个 SDK 返回格式。

### `mini_agent.tool_core` / `builtin_tools` / `tool_registry`

工具系统，对应 Claude 的 `buildTool()` 思路：

- `Tool`: 工具元信息、schema、输入校验和执行函数
- `build_tool()`: 工具构造入口
- `builtin_tools`: 文件、搜索、shell、task 等内置工具构造和少量直接相关 helper
- `ToolRegistry`: 当前 runtime 可用工具集合
- `tool_policy`: 当前 intent 能看到哪些工具
- `ToolTurnExecutor`: 权限判断、批次分区、工具执行和结果包装
- 严格输入校验：执行前拒绝缺少必填字段、schema 以外字段、基础类型不匹配和 enum 不匹配
- 工具结果预算：大输出在进入上下文前被截断，保留开头、结尾和截断说明

工具定义回答“怎么执行”，注册表回答“有哪些工具”，策略层回答“本轮能看见哪些工具”，执行器回答“如何安全执行这一轮工具调用”。

### `mini_agent.intent` / `tool_policy`

工具可见性边界：

- `intent.py`: 判断寒暄、泛学习、项目问题、编码任务、危险请求
- `tool_choice_guidance()`: 根据 intent 给模型注入轻量工具选择策略
- 明确文档入口的项目问答会隐藏 `list_files`，优先读架构、功能或路线图文档
- 启动和用法问题优先读 `docs/current-features.md`
- 明确路径和内容的 coding task 会隐藏 `list_files`，避免先做目录探索
- `tool_policy.py`: 决定本轮模型能看到哪些工具
- runtime 执行工具前会再次使用当前可见工具集合，避免隐藏工具通过伪工具调用或异常 tool_use 被执行

这样可以避免简单聊天或泛学习问题误触发读文件、shell 或子 Agent。

### `mini_agent.permissions` / `workspace`

本地安全边界：

- `workspace.py`: 限制文件路径在 workspace 内
- `permissions.py`: 根据权限模式、规则和工具风险决定 allow / ask / deny
- 工具输入校验在权限判断前执行
- 权限被拒绝后，本轮会关闭工具暴露，让模型解释权限边界而不是继续换工具尝试

当前是轻量权限管线，不追求 Claude 完整复杂度。

### `mini_agent.context`

上下文管理：

- tool result budget：工具结果进入上下文前先截断
- micro-compact：不调用模型，只压缩旧工具结果
- full compact：仍超预算时让模型总结旧历史
- summary 注入：full compact 摘要会进入后续 system prompt
- TaskState 注入：当前任务状态独立进入 system prompt，不合并进 summary
- prompt/context 拼接顺序：historical summary 先于 live task state，避免把历史记忆当成当前任务清单

对应 Claude 的分层上下文压缩思想。

### `mini_agent.tasks`

轻量 Task/Todo 状态：

- `TaskState`: 保存当前多步骤任务进度
- `set_tasks` / `update_task` / `list_tasks`: 通过工具让模型显式维护计划
- CLI 将 task 工具结果渲染成 `[tasks]` 区块，便于用户观察进度

当前只做前台 todo 状态，不实现 Claude 的后台任务、任务通知、持久化和并发任务引擎。

### `mini_agent.subagent`

AgentTool 风格的内置只读子 Agent：

- `explore_agent`
- `plan_agent`
- `verify_agent`

子 Agent 使用独立 runtime、独立 state、只读工具集。主 Agent 只接收最终总结；即使子 Agent 超限或 finalization 失败，也只返回短 `inconclusive` 摘要和少量最近证据，避免把探索过程全部塞进主上下文。

子 Agent 内部不会再暴露 `explore_agent`、`plan_agent`、`verify_agent` 这类子 Agent 工具自身，prompt 也明确不委托其他 Agent，避免形成递归 AgentTool 调用。当前只保留固定内置角色，不支持自定义 agent、后台并行、独立模型或 worktree 隔离。

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
