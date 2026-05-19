# Changelog

本文件记录项目版本变化。

## 0.3.0 - 2026-05-20

当前学习阶段：Task/Todo 状态管理。

变更级别：大特性版本。

### Major Features

- 新增 `mini_agent.tasks` 核心状态模块
- 新增 `TaskState`，用于保存当前任务列表
- 新增 `TaskItem` 和 `TaskStatus`
- Runtime 持有共享 `TaskState`
- System prompt 每轮注入当前任务状态
- 工具系统和 runtime 共享同一个任务状态

这些属于大特性，因为它们引入了新的核心状态模块，让 agent 从“单轮工具执行”升级到“能跟踪多步骤任务进度”。

### Tools

- 新增 `set_tasks`：替换当前 todo 列表
- 新增 `update_task`：更新单个任务状态和备注
- 新增 `list_tasks`：读取当前任务状态

### Tests

- 新增任务状态测试：
  - 设置任务列表
  - 更新任务状态和备注
  - 拒绝未知任务 id
  - prompt summary
  - 工具共享同一个 `TaskState`
  - runtime prompt 注入任务状态

### Verified

- `29 passed`

## 0.2.1 - 2026-05-20

当前学习阶段：安全可学习的 Claude-style agent 骨架。

变更级别：小特性版本。

### Minor Features

- 新增 `preview_edit` 工具，只生成 unified diff，不修改文件
- 新增 `apply_edit` 工具，应用文本替换并返回实际 diff
- `edit_file` 现在会返回修改 diff，减少黑盒文件修改
- 新增 `unified_diff()` 辅助函数
- 新增 `replace_text()` 辅助函数，统一文本替换校验
- 权限示例中允许 `preview_edit`，并让 `apply_edit` 进入确认流程

这些属于小特性，因为它们增强现有工具系统的编辑体验，但没有引入新的核心模块，也没有改变 agent 的主循环学习阶段。

### Tests

- 新增 diff/patch 工具测试：
  - `preview_edit` 返回 diff 且不修改文件
  - `apply_edit` 返回 diff 且修改文件
  - `preview_edit` 是只读工具，`apply_edit` 不是只读工具

### Verified

- `23 passed`

## 0.2.0 - 2026-05-20

当前学习阶段：安全可学习的 Claude-style agent 骨架。

变更级别：大特性版本。

### Major Features

- LLM provider 适配层，支持 Anthropic 和 OpenAI-compatible `/v1`
- 工具系统：`Tool`、`build_tool()`、工具 schema、结果截断
- 权限系统：`default`、`plan`、`acceptEdits`、`bypassPermissions`、`dontAsk`
- 工作区路径边界，阻止文件工具逃逸 workspace
- 意图识别 / 工具使用门控

这些属于大特性，因为它们引入或改变了 agent 的核心模块和主流程。

### Minor Features

- OpenAI-compatible `reasoning_content` 续传
- 内置工具：`list_files`、`read_file`、`write_file`、`edit_file`、`search_text`、`run_shell`
- 权限规则：`allow`、`deny`、`ask`
- shell 只读命令保守分类
- 简单上下文摘要压缩
- fallback model 配置

这些属于小特性，因为它们增强现有模块能力，但不单独构成新的学习阶段。

### Fixes / Behavior Adjustments

- 普通寒暄默认短回答，不主动输出项目架构
- 泛学习请求默认不读取工作区，不主动介绍本项目
- `run_shell("pwd")` 等只读命令在 `plan` 模式不再错误触发写操作确认
- Q&A 文档仅记录技术疑问和解答

### Documentation

- 长期文档体系：
  - `PROJECT_PRINCIPLES.md`
  - `docs/architecture.md`
  - `docs/current-features.md`
  - `docs/roadmap.md`
  - `docs/learning-qa.md`
  - `docs/01-llm-provider-adapter.md`
  - `docs/versioning.md`
- 版本管理文件：
  - `VERSION`
  - `CHANGELOG.md`

### Tests

- 测试套件覆盖：
  - intent 分类和 runtime 工具过滤
  - LLM provider 适配层转换
  - `reasoning_content` 续传
  - 权限规则和权限模式
  - shell 只读命令分类
  - 工作区路径边界

### Verified

- `20 passed`

## 0.1.0 - 2026-05-20

当前学习阶段：最小 Claude-style agent 闭环。

变更级别：大特性版本。

### Added

- 最小对话循环
- Anthropic Messages API 工具调用
- 基础工具：列目录、读文件、写文件、运行 shell
- 初始 README
