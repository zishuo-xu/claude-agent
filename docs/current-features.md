# Current Features

这份文档只记录“当前能做什么”。历史变化见 `CHANGELOG.md`，设计解释见 `docs/architecture.md`。

当前版本：`0.19.0`

## 启动

```bash
cd /Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent
.venv/bin/python agent.py --permission-mode plan
```

退出：

```text
/exit
```

运行测试：

```bash
.venv/bin/python -m pytest
```

当前测试：`143 tests`

## LLM Provider

支持：

- `openai-compatible`
- `anthropic`

当前本地 `.env` 使用 OpenAI-compatible `/v1` 服务和 `mimo-v2-omni` 模型。

## 架构取舍

- 暂不实现完整 StreamingToolExecutor
- 保留当前“模型流结束后执行工具”的批量执行路径
- 已吸收 Claude 的工具批次分区思想，不做流中工具调度

相关文件：`mini_agent/llm.py`、`docs/01-llm-provider-adapter.md`

## Agent Loop

已支持：

- 多轮消息历史
- 阶段化主循环：begin turn、record assistant、final answer、tool turn
- 意图识别和工具门控
- 流式文本输出
- 工具调用、工具执行、工具结果回传
- 工具轮次执行器
- 工具批次分区：连续并发安全工具并发执行，不安全工具串行执行
- 工具批次事件：`tool_batch_start` / `tool_batch_end`
- Runtime 边界守护测试
- Runtime 状态边界测试
- Runtime 0.12 主线已收尾，暂不继续拆主循环
- 轻量错误恢复事件
- 轻量运行时事件
- 最大轮次限制
- 空响应兜底
- 伪工具调用标记兼容，解析逻辑独立在 `pseudo_tools.py`
- 系统提示只保留高层运行原则，具体场景约束由 intent prompt 注入
- 模型输入按固定边界拼接：base system -> workspace -> intent -> historical summary -> live task state -> messages
- Prompt / Context 0.16 主线已收尾，暂不增加 prompt 规则或模板系统
- 当前用户请求内的工具轮次计数独立命名为 `current_turn_tool_rounds`
- `reasoning_content` 续传
- task/todo 状态注入 system prompt
- micro-compact 和 full compact

普通寒暄、泛学习请求默认不读项目、不调用工具；泛学习默认保持 3-5 行，不主动给链接或 emoji。项目问题和编码任务才进入工具循环。中文“创建文件并给出内容”的请求会进入 coding task。明确给出目标路径和内容的 coding task 会隐藏 `list_files`，让模型直接创建或编辑文件。
项目问题会按问题选择最相关文档入口：架构和 Agent Loop 问题读 `docs/architecture.md`，功能/版本问题读 `docs/current-features.md`，下一步/roadmap 问题读 `docs/roadmap.md`，宽泛项目概览再读 `README.md` 或 `docs/context-map.md`。项目结构、架构、Agent Loop、当前功能、当前版本、下一步这类问题会隐藏 `list_files`，直接读文档；即使问题没有显式出现“项目”二字，只要命中文档入口问题，也按项目问答处理。隐藏工具即使被模型输出，也会在执行层转成内部引导结果，不按普通未知工具错误展示。目标文件不清楚时才列目录或搜索。项目问答默认简洁回答，不复述整份文档或长历史；默认用短段落或 3-6 条短要点，不主动使用 emoji、表格、目录树或额外学习链接。

当前运行时事件包括：

- `turn_start`
- `model_start`
- `text_delta`
- `assistant_message`
- `tool_start`
- `tool_result`
- `tool_error`
- `tool_batch_start`
- `tool_batch_end`
- `model_error`
- `model_fallback`
- `turn_limit_reached`
- `permission_request`
- `turn_transition`
- `final_answer`

CLI 通过事件打印输出；权限确认通过可注入 handler 处理；runtime 同时保留事件列表，方便测试和后续演进。
`tool_batch_start` / `tool_batch_end` 是内部可观测事件，默认 CLI 不打印。工具结果仍完整进入模型上下文，但 CLI 会按工具类型控制展示：`read_file` 和 `search_text` 成功结果只显示摘要，错误结果带 `[tool_error]` 前缀完整展示。`run_shell` 结果在 CLI 中按 exit/stdout/stderr 展示，不再原样打印 JSON。`list_files` 结果在 CLI 中显示摘要，避免目录列表刷屏。写入、编辑、任务类短结果仍直接显示，方便确认动作结果。

相关文件：`mini_agent/runtime.py`、`mini_agent/pseudo_tools.py`、`mini_agent/tool_executor.py`、`mini_agent/events.py`、`mini_agent/intent.py`、`mini_agent/tool_policy.py`

## 工具系统

当前 CLI 启动后共有 14 个模型可用工具：11 个基础工具 + 3 个只读子 Agent 工具。
内置工具当前仍集中在 `builtin_tools.py`，职责限定为构造内置工具和少量直接相关 helper，暂不拆文件。

基础工具：

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

子 Agent 工具：

- `explore_agent`
- `plan_agent`
- `verify_agent`

已支持工具元信息：

- JSON schema
- 严格输入校验：缺少必填字段、传入 schema 以外字段、基础类型不匹配或 enum 不匹配会被拒绝
- 只读/写入/危险标记
- 工具结果预算和截断
- 权限判断
- 错误结果统一包装
- 只读子 Agent 工具集过滤会排除依赖输入才可能只读的 shell 工具
- 工具系统 0.13 主线已收尾，暂不新增 Git 工具、MCP 或复杂权限

`read_file`、`search_text`、`run_shell`、diff 类工具有较小结果预算。超长结果会保留开头和结尾，并插入截断说明，避免大输出污染上下文。

`list_files` 默认隐藏 `.env`、`.venv`、`__pycache__` 等噪音项；模型可见 schema 不暴露 `include_hidden`，避免无理由列出隐藏文件。`run_shell` 会拒绝空命令，并对部分只读命令做保守识别。运行 Python 脚本时，系统提示会优先建议使用 `python3`。

相关文件：`mini_agent/tool_core.py`、`mini_agent/builtin_tools.py`、`mini_agent/tool_registry.py`、`mini_agent/tool_policy.py`、`mini_agent/tool_executor.py`

## 权限和工作区安全

权限模式：

- `default`
- `plan`
- `acceptEdits`
- `bypassPermissions`
- `dontAsk`

规则顺序：

```text
deny -> allow -> ask -> mode fallback
```

已支持：

- 文件路径限制在 workspace 内
- 阻止 `../` 逃逸
- shell 基础风险识别
- 写入类操作按权限模式确认
- 权限确认提示显示工具名、原因、目标和默认拒绝说明
- 权限拒绝后同一轮会关闭工具暴露，避免换工具绕路重试
- `preview_edit` 只读预览，`apply_edit` 写入
- 权限体验 0.17 主线已收尾，暂不新增复杂权限规则或 TUI

相关文件：`mini_agent/permissions.py`、`mini_agent/workspace.py`

## 上下文管理

已支持：

- 工具结果进入上下文前先做结果预算截断
- 超过 `context_char_budget` 时触发压缩
- 先 micro-compact 旧工具结果
- 默认保留最近 6 个可压缩工具结果
- 错误工具结果不会被 micro-compact 清理，便于继续排查失败原因
- 仍超预算时 full compact
- full compact 保留最近 4 条原始消息
- full compact 摘要会注入后续 system prompt
- full compact 摘要提示会要求保留目标、决策、路径、命令和未完成事项，同时避免复制长工具输出、闲聊和重复细节
- `TaskState` 作为 live task state 独立注入；summary 作为 historical context 独立注入
- system prompt 中 historical summary 先于 live task state 注入，二者标签清楚且不合并
- 边界测试覆盖孤立 tool_result、旧目标摘要 prompt、最近消息保留
- 真实长任务测试覆盖用户目标、文件路径、命令、未完成事项和 summary 注入

可压缩工具结果包括文件、搜索、编辑、shell 等高噪音成功输出；task/todo 工具结果和错误工具结果暂不压缩。`TaskState` 负责当前任务进度，summary 负责压缩后的历史上下文，二者不合并。

相关文件：`mini_agent/context.py`

## 子 Agent

已支持内置只读子 Agent：

- `explore_agent`: 探索代码和文档
- `plan_agent`: 制定实现计划
- `verify_agent`: 只读验证结果

特性：

- 独立 `AgentRuntime`
- 独立 `AgentState` / `TaskState`
- 只暴露只读工具
- 不向子 Agent 暴露子 Agent 工具自身，避免递归调用
- 提示词明确不委托其他 Agent，保持单次只读子任务边界
- 内部工具历史不进入主 Agent
- 最终只返回总结
- finalization 失败时返回短 `inconclusive` 摘要和少量最近证据
- 显式调用后单次收敛
- 子 Agent 0.14 主线已收尾，暂不扩展复杂多 Agent 能力

当前不支持自定义 markdown Agent、插件 Agent、后台并行、独立模型或 worktree 隔离。

相关文件：`mini_agent/subagent.py`

## Task/Todo 状态

已支持：

- `TaskState`
- `TaskItem`
- `TaskStatus`: `todo`、`in_progress`、`done`、`blocked`
- `set_tasks`
- `update_task`
- `list_tasks`
- 多步骤 coding task 的 system prompt 会要求先创建 3-6 项短 todo，并在阶段开始或完成时更新
- CLI 中 task 工具结果显示为 `[tasks]` 区块，模型上下文仍保留原始任务状态文本

相关文件：`mini_agent/tasks.py`

## 文档体系

- `README.md`: 项目入口
- `PROJECT_PRINCIPLES.md`: 长期原则
- `docs/context-map.md`: 文档和代码阅读导航
- `docs/architecture.md`: 稳定架构
- `docs/current-features.md`: 当前能力
- `docs/roadmap.md`: 下一步计划
- `docs/versioning.md`: 版本规则
- `docs/learning-qa.md`: 独立学习沉淀，默认不参与日常上下文加载
- `CHANGELOG.md`: 版本历史
