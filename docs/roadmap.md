# Roadmap

这份文档记录项目规划、下一步工作、优先级和暂缓项。

它用于承载“接下来做什么”这类规划内容；技术疑问和解答仍放在 `docs/learning-qa.md`。

当前版本：`0.3.0`

## 已完成

### P1 / 大特性 / 0.3.0: Task/Todo 状态

目标：让 agent 能把较大任务拆成 todo，并在执行过程中更新状态。

完成情况：

- 新增 `mini_agent/tasks.py`
- 新增 `TaskState`、`TaskItem`、`TaskStatus`
- Runtime 持有共享任务状态
- system prompt 注入当前任务摘要
- 新增 `set_tasks`、`update_task`、`list_tasks`
- 工具系统和 runtime 共享同一个 `TaskState`
- 增加任务状态和工具共享测试

验收标准：

- 可以设置任务列表
- 可以更新任务状态和备注
- 可以读取当前任务状态
- prompt 中包含当前任务摘要
- 测试覆盖任务状态模块和 runtime 集成

### P1 / 小特性 / 0.2.1: Diff 预览和 patch 工具

目标：把文件编辑流程从“直接写文件”升级为“先生成 diff，再应用修改”。

完成情况：

- 新增 `preview_edit` 工具，只生成 unified diff，不修改文件
- 新增 `apply_edit` 工具，应用文本替换并返回实际 diff
- `edit_file` 返回 diff，减少黑盒修改
- 新增 `unified_diff()` 和 `replace_text()` 辅助函数
- 更新权限示例：`preview_edit` 只读允许，`apply_edit` 需要确认
- 增加 diff/patch 工具测试

验收标准：

- `preview_edit` 不修改文件
- `apply_edit` 修改文件并返回 diff
- 修改前后差异可见
- 测试覆盖只读属性和实际文件变化

### P0: 意图识别 / 工具使用门控

目标：让 agent 在调用模型和工具前，先判断用户输入属于哪类意图，再决定是否允许或鼓励使用工具。

建议意图分类：

```text
casual_chat       -> 短回答，不用工具
general_learning  -> 简洁建议或询问水平，不用工具
project_question  -> 可以读文档或代码后解释
coding_task       -> 可以使用工具、改代码、测试
dangerous_request -> 谨慎确认或拒绝
```

为什么优先做：

- 最近的问题都指向“agent 没有先判断用户意图”
- 可以减少无意义工具调用
- 可以避免普通问题被回答成项目架构说明
- 是后续增加更多工具、MCP、多 agent 前的基础安全层

完成情况：

- 新增 `mini_agent/intent.py`
- 定义 `Intent` 枚举和简单规则分类器
- 在 `AgentRuntime.run_user_turn()` 开始时分类用户输入
- 在 system prompt 中注入当前 intent 和工具使用约束
- 对 `casual_chat`、`general_learning`、`dangerous_request` 隐藏工具 schema
- 增加 `tests/test_intent.py` 和 `tests/test_runtime_intent.py`
- 更新架构文档、当前功能文档和 README

验收标准：

- 输入“你好”时不暴露工具，短回答
- 输入“我想学习 Python”时不暴露工具，短回答或询问水平
- 输入“解释这个项目架构”时可以暴露工具读取文档
- 输入“帮我修改代码”时可以进入工具循环
- 测试覆盖 intent 分类、prompt 注入和工具过滤

## 当前下一步

### P2 / 大特性 / 0.4.0: 流式输出

支持模型 token 级流式输出，让交互更接近 Claude Code。

## 后续候选

### P2 / 小特性: Git 专用工具

增加 `git_status`、`git_diff`、`git_log` 等工具，减少直接使用 shell 的风险。

### P3 / 大特性: MCP 工具注册

学习 Claude Code 的 MCP 扩展能力，支持外部工具发现和注册。

### P3 / 大特性: 多 agent 分工

实现简化版 `explore / plan / implement / verify` 多 agent 模式。

## 暂缓项

- 复杂终端 UI：当前先保持 CLI 简单可读
- 大规模 settings 合并：当前只需要最小 `agent_settings.json`
- 自动发布或远程执行：学习阶段风险高，暂不做
