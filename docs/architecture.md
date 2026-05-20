# Architecture

这份文档记录当前项目架构。它的目标是帮助学习者和其他 AI 工具快速理解：这个简化版 Claude-style agent 由哪些模块组成、数据如何流动、每个模块参考了 Claude Code 的哪个设计思想。

## 项目目标

本项目不是复刻 Claude Code，而是把 Claude Code 的核心设计拆成初学者能理解、能运行、能逐步扩展的小系统。

架构设计原则：实现可以简化，但架构分层和概念边界应参考 Claude Code。每个重要模块都应尽量说明它对应 Claude Code 的哪个概念，以及本项目做了哪些学习型简化。

当前主线：

```text
用户目标 -> LLM 推理 -> 工具调用 -> 权限判断 -> 本地执行 -> 工具结果回传 -> 下一轮推理
```

## 顶层模块

```text
agent.py
  -> mini_agent.config
  -> mini_agent.intent
  -> mini_agent.llm
  -> mini_agent.context
  -> mini_agent.runtime
  -> mini_agent.subagent
  -> mini_agent.tasks
  -> mini_agent.tool_core
  -> mini_agent.builtin_tools
  -> mini_agent.tool_registry
  -> mini_agent.tool_policy
  -> mini_agent.permissions
  -> mini_agent.settings
  -> mini_agent.workspace
```

## 模块职责

### `agent.py`

CLI 入口。

职责：

- 加载 `.env`
- 解析命令行参数
- 创建 LLM client
- 创建 `AgentConfig`
- 加载权限规则
- 启动 `AgentRuntime`

学习重点：真实 agent 通常会把“入口配置”和“核心运行时”分开，避免 runtime 被 CLI 细节污染。

### `mini_agent.runtime`

agent 主循环。

职责：

- 保存对话历史 `AgentState`
- 保存当前用户意图 `current_intent`
- 持有共享任务状态 `TaskState`
- 持有工具注册表 `ToolRegistry`
- 调用模型
- 流式消费模型 text delta
- 在 provider 最终响应缺失文本时，用 stream delta 累计文本补回
- 通过工具策略根据 intent 决定是否暴露工具 schema
- system prompt 明确区分真实 tool call 和文本形式的伪工具调用
- 兼容模型输出的 XML/JSON 简单伪工具调用标记，并转成内部 `tool_use`
- 将当前任务状态注入 system prompt
- 识别模型返回的 `tool_use`
- 调度本地工具
- 在权限判断前执行工具输入校验
- 把 `tool_result` 回传给模型
- 在上下文过大时先触发 micro-compact，再用 full compact 兜底

对应 Claude Code 概念：

- `queryLoop`
- 对话状态 `State`
- 工具调用后的 follow-up turn
- 上下文 compact
- micro-compact
- task/todo 状态注入
- streaming event 消费

### `mini_agent.context`

上下文管理模块。

职责：

- 统计消息历史字符预算
- 识别可压缩工具结果
- 保留最近 N 个工具结果
- 将更早的工具结果替换为短占位文本
- 避免误清理普通用户消息和 assistant 文本

对应 Claude Code 概念：

- Microcompact
- 工具结果清理
- full compact 之前的轻量上下文减压

### `mini_agent.subagent`

内置子 Agent 和 AgentTool 风格工具。

职责：

- 定义 `AgentDefinition`
- 定义内置 `EXPLORE_AGENT`、`PLAN_AGENT` 和 `VERIFY_AGENT`
- 将子 Agent 包装成 `explore_agent` / `plan_agent` / `verify_agent` 工具
- 为子 Agent 创建独立 `AgentRuntime`
- 为子 Agent 创建独立 `AgentState` 和 `TaskState`
- 只向子 Agent 暴露只读工具
- 只把最终总结返回主 Agent，不把内部工具历史塞回主 Agent
- 当子 Agent 未产出最终文本时，用捕获输出兜底，避免主 Agent 拿到空结果
- 子 Agent 默认最多 3 次工具调用，随后必须返回最终总结
- 子 Agent 到达轮次上限时，追加一次无工具 finalization，把 transcript 压成最终答案

对应 Claude Code 概念：

- `AgentTool`
- Built-in Agents
- Explore Agent
- Plan Agent
- Verification Agent
- `runAgent()`
- 子 Agent context 隔离

当前简化：

- 不支持自定义 `.claude/agents/*.md`
- 不支持 plugin agent
- 不支持后台并行
- 不支持每个子 Agent 单独选择模型
- 不支持 worktree / remote 隔离
- 不做复杂预算器；当前只用 prompt 约束、`max_turns=4` 和最终总结兜底

### `mini_agent.intent`

意图识别和工具使用门控。

职责：

- 将用户输入分类为 `casual_chat`、`general_learning`、`project_question`、`coding_task`、`dangerous_request`
- 为每类 intent 提供工具使用建议
- 在简单聊天和泛学习咨询中隐藏工具 schema，避免模型无意义读取项目或执行 shell
- 显式请求内置子 Agent 时，只暴露被点名的子 Agent 工具；该工具执行一次后关闭工具暴露

对应 Claude Code 概念：

- query 前的预处理
- tool use gating
- permission pipeline 之前的轻量意图判断

### `mini_agent.llm`

LLM provider 适配层。

职责：

- 定义 runtime 依赖的统一 `LLMClient`
- 适配 Anthropic Messages API
- 适配 OpenAI-compatible `/v1/chat/completions`
- 在 provider 边界转换工具调用格式
- 提供统一流式事件接口
- 保留并续传 `reasoning_content`

对应 Claude Code 概念：

- API 调用边界
- provider 细节隔离
- runtime 不直接依赖某个 SDK 的返回格式
- streaming 和非 streaming 在适配层统一

### `mini_agent.tool_core`

工具核心类型。

职责：

- 定义 `Tool`
- 提供 `build_tool()` builder
- 暴露工具 schema 给模型
- 支持轻量输入校验
- 封装工具执行和结果长度截断
- 标记工具是否只读、是否可并发、是否危险

对应 Claude Code 概念：

- `buildTool()`
- `validateInput()`
- 工具统一接口
- fail-closed 默认值

### `mini_agent.builtin_tools`

内置工具集合。

职责：

- 构造项目内置工具
- 维护文件、搜索、shell、task 工具的具体实现
- 复用 `Workspace` 限制文件路径
- 为每个工具声明只读、并发、安全风险元信息
- `list_files` 默认隐藏常见噪音项，必要时可显式包含隐藏项

当前内置工具：

- `list_files`
- `read_file`
- `write_file`
- `edit_file`
- `preview_edit`
- `apply_edit`
- `search_text`
- `run_shell`
- `set_tasks`
- `update_task`
- `list_tasks`

对应 Claude Code 概念：

- 内置 Tool 实现
- 只读工具可并发
- diff/patch 风格的可审查文件编辑

### `mini_agent.tool_registry`

工具注册表。

职责：

- 保存当前 runtime 可用的工具集合
- 支持按名称查询工具
- 为模型生成当前可见工具 schema
- 隔离 runtime 和具体工具分组

学习重点：runtime 不应该知道“哪些工具来自内置、Git、MCP 或多 agent 子系统”。它只通过注册表拿到“当前能用什么”。

### `mini_agent.tool_policy`

工具暴露策略。

职责：

- 根据 `IntentDecision` 决定当前是否暴露工具
- 把“工具存在”和“工具对模型可见”分开

当前策略仍很简单：`casual_chat`、`general_learning`、`dangerous_request` 等不允许工具的 intent 会隐藏全部工具。后续可以扩展成更细的只读工具集、Git 工具集或 MCP 工具集。

### `mini_agent.tools`

兼容入口。

职责：

- 继续导出 `Tool`、`build_tool()`、`default_tools()` 等旧接口
- 让已有测试和简单调用方不用一次性迁移
- 新代码优先使用 `tool_core`、`builtin_tools`、`tool_registry`、`tool_policy`

### `mini_agent.tasks`

Task/Todo 状态模块。

职责：

- 定义 `TaskItem`
- 定义 `TaskStatus`
- 通过 `TaskState` 保存当前任务列表
- 渲染任务状态给用户和 system prompt

对应 Claude Code 概念：

- 任务状态
- 多步骤任务进度管理
- agent 在较大目标中的持续上下文

### `mini_agent.permissions`

权限系统。

职责：

- 定义权限模式
- 解析权限规则
- 根据模式、规则、工具风险做权限决策

当前权限模式：

- `default`
- `plan`
- `acceptEdits`
- `bypassPermissions`
- `dontAsk`

规则判断顺序：

```text
deny -> allow -> ask -> mode fallback
```

对应 Claude Code 概念：

- Permission Mode
- Permission Rules
- Permission Pipeline

### `mini_agent.settings`

设置加载。

职责：

- 从 `agent_settings.json` 加载权限规则

当前只实现了最小设置系统，后续可以扩展成多层配置合并。

### `mini_agent.workspace`

工作区边界。

职责：

- 把相对路径解析到 workspace 内
- 阻止 `../` 逃逸工作区

这是本地 agent 的基础安全边界。

## 一次工具调用的数据流

```text
User
  -> AgentRuntime.run_user_turn()
  -> classify_intent()
  -> ToolRegistry.api_specs_for_intent()
  -> tool_policy filters available tools
  -> inject task state
  -> LLMClient.stream_complete()
  -> stream text deltas to terminal
  -> final LLMResponse
  -> model may return ToolUseBlock
  -> decide_permission()
  -> Tool.run()
  -> tool_result
  -> append to messages
  -> LLMClient.stream_complete()
  -> final assistant answer
```

## 文件编辑数据流

```text
preview_edit
  -> read file
  -> replace in memory
  -> generate unified diff
  -> return diff without writing

apply_edit / edit_file
  -> read file
  -> replace in memory
  -> generate unified diff
  -> write file
  -> return applied diff
```

学习重点：coding agent 的文件修改不应该是黑盒。diff 是让修改可见、可审查、可确认的中间表示。

## 任务状态数据流

```text
set_tasks
  -> replace TaskState items
  -> render task list
  -> next model call sees task summary

update_task
  -> update TaskItem status/note
  -> render task list
  -> next model call sees updated progress

list_tasks
  -> read TaskState
  -> return current progress
```

学习重点：较大任务需要显式进度状态。Task/Todo 让 agent 不只是在调用工具，也在维护“当前做到哪一步”。

## 工具注册数据流

```text
ToolRegistry.with_builtin_tools()
  -> build_builtin_tools()
  -> Tool objects
  -> Runtime asks api_specs_for_intent()
  -> tool_policy hides or exposes tools
  -> LLM sees only current allowed schemas
```

学习重点：工具系统分成三层会更容易扩展。工具定义回答“这个工具怎么执行”，工具注册表回答“当前有哪些工具”，工具策略回答“这次模型能看到哪些工具”。

## 上下文压缩数据流

```text
AgentRuntime._compact_if_needed()
  -> count_message_chars()
  -> if over budget: micro_compact_messages()
  -> clear old compactable tool_result content
  -> if under budget: continue without model summary
  -> if still over budget: full compact with LLM summary
  -> keep recent 4 raw messages
```

学习重点：micro-compact 和 full compact 是两层不同力度的上下文管理。micro-compact 不调用模型，只替换旧工具结果；full compact 调用模型总结旧历史，压缩力度更强，但成本更高。

## 子 Agent 数据流

```text
Main Agent
  -> model calls explore_agent / plan_agent / verify_agent
  -> subagent tool creates isolated AgentRuntime
  -> subagent gets read-only ToolRegistry
  -> subagent runs its own observe-think-act loop
  -> subagent internal messages stay isolated
  -> final text summary returns as tool_result
  -> Main Agent continues with compact summary only
```

学习重点：子 Agent 的价值不是“多一个函数调用”，而是上下文隔离和角色隔离。Explore / Plan / Verification 可以产生大量搜索、阅读、分析和验证中间过程，但主 Agent 只拿到最终总结。

## 流式输出数据流

```text
LLMClient.stream_complete()
  -> TextDeltaEvent
  -> Runtime buffers text delta
  -> FinalResponseEvent
  -> Runtime prints ordinary text or converts pseudo tool markup
  -> Runtime appends assistant message
  -> Runtime executes tool_use if present
```

学习重点：流式输出改变的是模型调用主路径。当前实现为了兼容会输出伪工具调用文本的 OpenAI-compatible 模型，会先累计 text delta，确认不是伪工具调用后再展示，同时保留最终结构化响应供工具循环使用。

## 当前简化点

为了保持学习友好，当前没有实现：

- 流中提前执行工具
- stop hooks
- 多层 settings 合并
- MCP 工具发现
- 自定义 / 插件 agent
- 多 agent 后台并行
- 自动 retry/backoff
- token 级精确预算
