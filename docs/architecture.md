# Architecture

这份文档记录当前项目架构。它的目标是帮助学习者和其他 AI 工具快速理解：这个简化版 Claude-style agent 由哪些模块组成、数据如何流动、每个模块参考了 Claude Code 的哪个设计思想。

## 项目目标

本项目不是复刻 Claude Code，而是把 Claude Code 的核心设计拆成初学者能理解、能运行、能逐步扩展的小系统。

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
  -> mini_agent.runtime
  -> mini_agent.tasks
  -> mini_agent.tools
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
- 调用模型
- 根据 intent 决定是否暴露工具 schema
- 将当前任务状态注入 system prompt
- 识别模型返回的 `tool_use`
- 调度本地工具
- 把 `tool_result` 回传给模型
- 在上下文过大时触发摘要压缩

对应 Claude Code 概念：

- `queryLoop`
- 对话状态 `State`
- 工具调用后的 follow-up turn
- 上下文 compact
- task/todo 状态注入

### `mini_agent.intent`

意图识别和工具使用门控。

职责：

- 将用户输入分类为 `casual_chat`、`general_learning`、`project_question`、`coding_task`、`dangerous_request`
- 为每类 intent 提供工具使用建议
- 在简单聊天和泛学习咨询中隐藏工具 schema，避免模型无意义读取项目或执行 shell

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
- 保留并续传 `reasoning_content`

对应 Claude Code 概念：

- API 调用边界
- provider 细节隔离
- runtime 不直接依赖某个 SDK 的返回格式

### `mini_agent.tools`

工具系统。

职责：

- 定义 `Tool`
- 提供 `build_tool()` builder
- 暴露工具 schema 给模型
- 执行本地工具
- 标记工具是否只读、是否可并发、是否危险

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

- `buildTool()`
- 工具统一接口
- fail-closed 默认值
- 只读工具可并发
- diff/patch 风格的可审查文件编辑

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
  -> filter available tools
  -> inject task state
  -> LLMClient.complete()
  -> model returns ToolUseBlock
  -> decide_permission()
  -> Tool.run()
  -> tool_result
  -> append to messages
  -> LLMClient.complete()
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

## 当前简化点

为了保持学习友好，当前没有实现：

- streaming token 输出
- stop hooks
- 多层 settings 合并
- MCP 工具发现
- 多 agent 编排
- 自动 retry/backoff
- token 级精确预算
