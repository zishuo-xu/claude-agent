# Versioning

这份文档只定义版本规则。版本历史写入 `CHANGELOG.md`，当前能力写入 `docs/current-features.md`。

## 格式

使用简化语义化版本：

```text
MAJOR.MINOR.PATCH
```

当前版本记录在根目录 `VERSION`。

## 含义

### MAJOR

学习主线发生重大变化。

例子：

- 单 agent 变成完整多 agent 框架
- 本地 CLI 变成 TUI/GUI
- 学习 demo 变成生产框架

当前仍是 `0.x`，表示 mini-claude 仍处于早期演进阶段。

### MINOR

完成一个清晰学习里程碑，通常对应大特性。

例子：

- LLM provider 适配层
- 工具系统
- 权限系统
- 上下文管理
- 子 Agent 架构

### PATCH

小特性、修复、测试补充或文档维护。

例子：

- provider 兼容修复
- prompt 行为收敛
- 工具输入校验
- 新增边界测试
- 文档同步

## 大特性和小特性

大特性通常满足至少一项：

- 引入新的核心模块
- 改变主循环、工具系统、权限系统、上下文系统等关键路径
- 对学习路线有独立章节价值
- 需要更新架构文档和一组测试

小特性通常满足：

- 不引入新核心模块
- 在现有模块内增强行为
- 风险小、范围清楚
- 文档只需轻量同步

## 更新规则

每次功能变化先判断：

```text
这是大特性、小特性、修复，还是纯文档？
```

再决定是否改版本。

版本变化至少更新：

- `VERSION`
- `CHANGELOG.md`
- `docs/current-features.md`
- `docs/roadmap.md`

必要时更新：

- `README.md`
- `docs/architecture.md`
- `docs/learning-qa.md`

纯文档整理通常不改版本。

## 当前阶段

当前版本：`0.17.1`

已完成学习主线：

- `0.1.0`: 最小 Agent 闭环
- `0.2.0`: 安全可学习的 Agent 骨架
- `0.2.1`: diff/patch 编辑增强
- `0.3.0`: Task/Todo 状态
- `0.4.0`: 流式输出
- `0.4.1`: streaming 空 `choices` 修复
- `0.4.2`: 工具系统架构整理
- `0.5.0`: 上下文 micro-compact
- `0.6.0`: Explore / Plan 子 Agent
- `0.6.1`: Verification 子 Agent
- `0.6.2`: 子 Agent 输出结构化
- `0.6.3`: 工具输入验证层
- `0.6.4`: Tool Result Budget / 输出收敛
- `0.6.5`: Context Map / 文档导航索引
- `0.7.0`: Lightweight Runtime Events / 轻量运行时事件
- `0.7.1`: Runtime Print Cleanup / 输出边界收敛
- `0.7.2`: Runtime Loop Shape / 主循环形态整理
- `0.7.3`: Runtime Error Recovery / 轻量错误恢复
- `0.7.4`: Tool Turn Executor / 工具轮次执行器
- `0.7.5`: Runtime Boundary Review / 主循环边界验收
- `0.8.0`: Streaming Tool Execution Decision / 流式工具执行取舍
- `0.8.1`: Tool Batch Partition / 工具批次分区
- `0.8.2`: Tool Batch Events / 工具批次事件
- `0.8.3`: Project Question Follow-up Fix / 项目问答跟进修复
- `0.8.4`: Tool Executor Boundary Review / 工具执行边界复查
- `0.9.0`: Context Strategy Review / 上下文策略复查
- `0.9.1`: Context Boundary Tests / 上下文边界测试
- `0.9.2`: Strict Tool Input Validation / 严格工具输入校验
- `0.9.3`: Project Question Read Strategy / 项目问答读取策略
- `0.9.4`: Project Answer Compression / 项目问答输出收敛
- `0.9.5`: Manual Usage Review / 手动使用复查
- `0.9.6`: Tool Result Display Compact / 工具结果展示收敛
- `0.9.7`: Shell Execution UX / Shell 执行体验收敛
- `0.9.8`: Direct File Task UX / 明确文件任务体验收敛
- `0.9.9`: Direct File Tool Gating / 明确文件任务工具门控
- `0.10.0`: Project Read Strategy Hardening / 项目读取策略硬化
- `0.10.1`: Visible Tool Enforcement / 可见工具执行校验
- `0.10.2`: Create Intent Recognition / 创建意图识别补强
- `0.10.3`: Output Style Review / 输出风格复查
- `0.10.4`: Architecture Answer Accuracy Review / 架构问答准确性复查
- `0.10.5`: 0.10 Line Review / 0.10 主线复查
- `0.11.0`: Context Compact Real-World Review / 上下文压缩真实复查
- `0.11.1`: Summary Boundary Review / 摘要边界复查
- `0.11.2`: Tool Result Compact Policy Review / 工具结果压缩策略复查
- `0.11.3`: Context / TaskState Relationship Review / 上下文与任务状态关系复查
- `0.11.4`: Context Line Review / 上下文主线收尾复查
- `0.12.0`: Runtime Boundary Slim Review / Runtime 边界减重复查
- `0.12.1`: Runtime Prompt Boundary Review / Runtime 提示词边界复查
- `0.12.2`: Runtime State Boundary Review / Runtime 状态边界复查
- `0.12.3`: Runtime Line Review / Runtime 主线收尾复查
- `0.13.0`: Tool Boundary Line Review / 工具系统边界主线复查
- `0.13.1`: Builtin Tools Shape Review / 内置工具形态复查
- `0.13.2`: Tool Input Schema Review / 工具输入 Schema 复查
- `0.13.3`: Tool Error Surface Review / 工具错误表现复查
- `0.13.4`: Tool Line Review / 工具系统主线收尾复查
- `0.14.0`: Subagent Boundary Line Review / 子 Agent 边界主线复查
- `0.14.1`: Subagent Prompt Boundary Review / 子 Agent 提示词边界复查
- `0.14.2`: Subagent Finalization Review / 子 Agent 兜底总结复查
- `0.14.3`: Subagent Line Review / 子 Agent 主线收尾复查
- `0.15.0`: Real Usage Acceptance Review / 真实使用验收复查
- `0.15.1`: Acceptance Follow-up Review / 验收跟进复查
- `0.15.2`: Acceptance Summary / 验收阶段总结
- `0.16.0`: Prompt / Context Boundary Review / 提示词与上下文边界复查
- `0.16.1`: Prompt / Context Acceptance Review / 提示词与上下文验收复查
- `0.16.2`: Prompt / Context Line Review / 提示词与上下文主线收尾复查
- `0.17.0`: Permission UX Review / 权限体验复查
- `0.17.1`: Permission Mode Acceptance Review / 权限模式验收复查

详细说明以 `CHANGELOG.md` 为准。
