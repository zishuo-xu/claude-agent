# Mini-Claude

这是一个参考 Claude Code 设计思想实现的轻量级工程化 agent。它不复刻任何非公开源码，而是在较小代码量里保留 Claude-style agent 的核心架构边界。

当前版本：`0.24.1`

项目长期原则见 [PROJECT_PRINCIPLES.md](/Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent/PROJECT_PRINCIPLES.md)。后续所有实现都应及时更新文档，方便学习者和其他 AI 工具理解项目进展。

文档必须跟随项目变化及时更新：代码、功能、架构、配置、测试或规划发生变化后，都要检查并同步对应文档。

长期文档入口：

- [Context Map](/Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent/docs/context-map.md): 文档和代码阅读导航
- [Architecture](/Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent/docs/architecture.md): 当前架构和模块职责
- [Current Features](/Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent/docs/current-features.md): 当前功能清单
- [Roadmap](/Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent/docs/roadmap.md): 下一步工作和优先级
- [Versioning](/Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent/docs/versioning.md): 版本规则和学习阶段
- [Learning Notes](/Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent/docs/learning-qa.md): 独立学习沉淀，默认不参与日常上下文加载

核心闭环：

```text
user message -> model -> tool_use -> permission check -> local tool -> tool_result -> model
```

## 已实现的 Claude Code 设计点

- **对话循环**：`AgentRuntime.run_user_turn()` 管理多轮 `tool_use / tool_result`
- **轻量运行时事件**：runtime 产生事件，CLI 负责展示，降低主循环和输出的耦合
- **工具结果展示收敛**：长工具结果仍进入模型上下文，但 CLI 默认只显示摘要
- **Shell 输出友好化**：`run_shell` 结果按 exit/stdout/stderr 展示，避免原样输出 JSON
- **明确文件任务直达**：用户给出明确路径和内容时，coding task 不暴露 `list_files`
- **工具轮次执行器**：工具执行从 runtime 拆出，统一处理校验、权限、执行和错误结果
- **流式输出**：主模型调用支持 text delta 接收，并会抑制伪工具调用文本
- **伪工具调用兼容边界**：`mini_agent/pseudo_tools.py` 负责解析模型误输出的工具标记，runtime 只负责调用
- **Task/Todo 状态**：`mini_agent/tasks.py` 保存多步骤任务进度，并通过工具更新
- **意图识别 / 工具门控**：`mini_agent/intent.py` 先判断用户输入，再决定是否暴露工具
- **短期工作状态**：澄清问题和继续追加会继承上一轮任务意图，避免多轮文件任务断掉
- **项目问答策略**：明确文档入口的问题会隐藏并拒绝执行 `list_files`，优先读架构、功能或路线图文档
- **Diff 预览和 patch 工具**：`preview_edit` 先看差异，`apply_edit` 应用修改并返回 diff
- **模型适配层**：`mini_agent/llm.py` 把不同 LLM API 转成统一的 agent 内部格式
- **reasoning 续传**：OpenAI-compatible provider 的 `reasoning_content` 会被保留并传回下一轮
- **工具系统**：`Tool` + `build_tool()` 提供统一 schema、严格输入校验、执行、只读/并发/危险标记
- **工具结果预算**：大输出在进入上下文前截断，保留开头、结尾和截断说明
- **工具注册表 / 策略边界**：`ToolRegistry` 统一管理工具集合，`tool_policy` 决定当前 intent 能看到哪些工具
- **上下文 micro-compact**：上下文过大时先清理旧工具结果，再用 full compact 兜底
- **Explore / Plan / Verification 子 Agent**：以 AgentTool 形式运行只读子 Agent，隔离探索、规划和验证上下文
- **子 Agent 输出结构化**：Explore / Plan / Verification 按固定小模板汇报结果
- **子 Agent 上下文策略**：子任务输入、内部 transcript 和返回结果都有轻量预算，只把最终摘要回传主 Agent
- **安全默认值**：工具默认不是只读、不可并发，接近 fail-closed 思路
- **权限模式**：支持 `default`、`plan`、`acceptEdits`、`bypassPermissions`、`dontAsk`
- **权限规则**：可用 `agent_settings.json` 配置 allow/deny/ask
- **只读并发**：多个只读且 concurrency-safe 的工具调用会并发执行
- **工作区边界**：文件工具不能逃出当前 workspace
- **上下文压缩**：历史过大时先 micro-compact，仍超预算再摘要旧消息
- **模型降级**：主模型失败时可切 fallback model

版本记录见 [CHANGELOG.md](/Users/xuzishuo/Documents/Codex/2026-05-20/claude-agent/CHANGELOG.md)。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
cp agent_settings.example.json agent_settings.json
```

然后编辑 `.env`，填入你的 LLM 配置。

当前项目默认支持 OpenAI-compatible `/v1` 接口：

```bash
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL_NAME=your-model-name
```

也保留 Anthropic provider，方便对照 Claude API 的 tool use 形状：

```bash
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514
```

## 运行

```bash
python agent.py
```

常用参数：

```bash
python agent.py --permission-mode plan
python agent.py --permission-mode acceptEdits
python agent.py --provider openai-compatible --model mimo-v2-omni
```

## 测试

项目有一组轻量测试，用来保护 mini-claude 的核心边界：

- 意图分类和工具门控
- 权限规则和权限模式
- 工作区路径不能逃逸
- OpenAI-compatible provider 适配层的消息转换

运行：

```bash
.venv/bin/python -m pytest
```

或者只跑某一组：

```bash
.venv/bin/python -m pytest tests/test_permissions.py
```

权限模式建议：

- `plan`: 学习/观察模式，只读工具自动允许，写入会确认
- `default`: 非只读操作需要确认
- `acceptEdits`: 工作区文件编辑自动允许，Shell 仍会确认
- `dontAsk`: 需要确认的操作直接拒绝，适合非交互环境
- `bypassPermissions`: 学习时不建议，除非你非常清楚模型会做什么

## 试试这些任务

```text
列出当前目录文件，读取 README.md，然后总结这个项目结构
```

```text
搜索 AgentRuntime 在哪里定义，并解释对话循环
```

```text
创建 hello.py，内容是打印 hello agent，然后运行它
```

## 代码结构

- `agent.py`: CLI 入口，加载配置并启动 runtime
- `mini_agent/llm.py`: LLM provider 适配层，把 Anthropic / OpenAI-compatible API 转成统一格式
- `mini_agent/context.py`: 上下文 micro-compact 和消息字符预算辅助函数
- `mini_agent/runtime.py`: 对话状态、模型调用、工具调度、上下文压缩
- `mini_agent/working_state.py`: 短期 pending task 状态和 intent 延续
- `mini_agent/pseudo_tools.py`: 伪工具调用标记解析和归一化
- `mini_agent/subagent.py`: Explore / Plan / Verification 只读子 Agent 定义、运行和工具包装
- `mini_agent/tasks.py`: Task/Todo 状态模块
- `mini_agent/tool_core.py`: 工具核心类型和 `build_tool()`
- `mini_agent/builtin_tools.py`: 内置工具构造
- `mini_agent/tool_registry.py`: 工具注册、查询和对模型暴露 schema
- `mini_agent/tool_policy.py`: 根据 intent 决定哪些工具可见
- `mini_agent/tools.py`: 兼容入口，保留 `default_tools()` 等旧调用方式
- `mini_agent/permissions.py`: 权限模式、规则匹配、决策管线
- `mini_agent/settings.py`: 从 `agent_settings.json` 加载权限规则
- `mini_agent/workspace.py`: 工作区路径边界
- `references/Claude-Code-Source-Study`: Claude Code 源码分析参考仓库

## 外部参考

本项目设计主要参考 Claude Code 的核心思想，并对照两组解读资料：

- [Claude-Code-Source-Study](https://github.com/luyao618/Claude-Code-Source-Study): 作为主要源码学习参考。
- [CoreCoder article](https://github.com/he-yufeng/CoreCoder/tree/main/article): 作为辅助文章参考，重点对照 Agent Loop、工具系统、上下文压缩、流式执行和多 Agent 设计。

## 对照阅读路线

建议先读：

1. `references/Claude-Code-Source-Study/docs/05-对话循环.md`
2. `references/Claude-Code-Source-Study/docs/09-工具系统设计.md`
3. `references/Claude-Code-Source-Study/docs/16-权限系统.md`
4. `references/Claude-Code-Source-Study/docs/06-上下文管理.md`
5. `references/Claude-Code-Source-Study/docs/12-Agent-系统.md`

再结合 CoreCoder 文章：

1. `CoreCoder/article/01-architecture-overview.md`
2. `CoreCoder/article/02-agent-loop.md`
3. `CoreCoder/article/03-tool-system.md`
4. `CoreCoder/article/04-context-compression.md`
5. `CoreCoder/article/05-streaming-executor.md`
6. `CoreCoder/article/06-multi-agent.md`

对照本项目：

- `queryLoop` 思想对应 `AgentRuntime.run_user_turn()`
- `queryModelWithStreaming` 的边界思想对应 `mini_agent.llm.LLMClient`
- `buildTool()` 思想对应 `mini_agent.tool_core.build_tool()`
- `Permission Pipeline` 思想对应 `mini_agent.permissions.decide_permission()`
- `ToolUseContext / State` 思想对应 `AgentState` 和 `AgentConfig`
- `AgentTool / Built-in Agent` 思想对应 `mini_agent.subagent`

## 后续方向

当前先保持简洁，不急着加功能。候选方向见 `docs/roadmap.md`。
