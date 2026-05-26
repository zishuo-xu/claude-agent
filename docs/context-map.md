# Context Map

这份文档是项目上下文地图。它帮助学习者和 AI 工具快速判断“该读哪个文件”，避免一次性读取过多文档。

## 先读什么

- 项目是什么、怎么启动：`README.md`
- 长期原则和工作方式：`PROJECT_PRINCIPLES.md`
- 当前架构分层：`docs/architecture.md`
- 当前已经能做什么：`docs/current-features.md`
- 下一步计划和暂缓项：`docs/roadmap.md`

## 按问题找文件

| 你想了解 | 入口 |
|---|---|
| 版本规则 | `docs/versioning.md` |
| 历史变化 | `CHANGELOG.md` |
| 维护记录 | `docs/maintenance-log.md` |
| 长压力测试案例 | `docs/stress-test-cases.md` |
| LLM provider 适配 | `docs/01-llm-provider-adapter.md` |
| Agent Loop | `mini_agent/runtime.py` |
| 会话焦点 | `mini_agent/focus.py` |
| 短期工作状态 | `mini_agent/working_state.py` |
| 运行时事件 | `mini_agent/events.py` |
| LLM API 边界 | `mini_agent/llm.py` |
| 伪工具调用兼容 | `mini_agent/pseudo_tools.py` |
| 工具抽象 | `mini_agent/tool_core.py` |
| 内置工具 | `mini_agent/builtin_tools.py` |
| 工具注册 | `mini_agent/tool_registry.py` |
| 工具可见性 | `mini_agent/tool_policy.py` |
| 意图识别 | `mini_agent/intent.py` |
| 权限判断 | `mini_agent/permissions.py` |
| 工作区边界 | `mini_agent/workspace.py` |
| 上下文压缩 | `mini_agent/context.py` |
| 子 Agent | `mini_agent/subagent.py` |
| Task/Todo 状态 | `mini_agent/tasks.py` |

## 文档读取建议

- 问“现在有什么”：读 `docs/current-features.md`。
- 问“为什么这样设计”：读 `docs/architecture.md` 和 `docs/roadmap.md`。
- 问“这次改了什么”：读 `CHANGELOG.md`。
- 问“最近修了什么但没升版本”：读 `docs/maintenance-log.md`。
- 问“下一步做什么”：读 `docs/roadmap.md`。

原则：先读最小入口，只有需要细节时再打开对应代码或专题文档。

## 低频学习沉淀

`docs/learning-qa.md` 是独立学习沉淀文档，不参与日常上下文加载。只有当问题明确要求查看学习记录、历史解释或技术问答沉淀时才读取。
