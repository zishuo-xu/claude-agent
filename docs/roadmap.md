# Roadmap

这份文档只记录方向、取舍和下一步。详细版本变化见 `CHANGELOG.md`，当前能力清单见 `docs/current-features.md`。

当前版本：`0.6.3`

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

## 架构减重审视

结论：当前架构主线仍然清楚，但文档和后续规划已经有变重趋势。下一阶段应少加功能，先保持项目轻。

### 保留

- `AgentRuntime`: 仍作为学习主循环入口，暂不拆更细。
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
- `runtime.py` 职责较多，但作为学习版主循环仍可接受。
- 子 Agent 已有空结果兜底、伪工具调用兼容、3 次工具调用预算、轮次上限 finalization 和显式单次调用收敛；后续先观察真实使用，不急着继续加复杂调度。

## 下一步

### P2 / 文档与设计: 保持简洁

短期目标不是加功能，而是观察现有架构是否仍易读、易讲、易维护。

验收标准：

- 新功能必须能说明对应 Claude 的哪个概念。
- 新功能必须比现有方案明显更有学习价值。
- 文档更新要短，不重复 changelog。
- 不为了版本号继续堆功能。

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
