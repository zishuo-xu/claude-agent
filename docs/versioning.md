# Versioning

这份文档定义本项目的版本概念。

本项目是学习型项目，版本号不只表示代码发布，也表示学习阶段。版本应帮助学习者理解：当前 agent 已经学到了 Claude Code 的哪一层设计。

## 版本格式

使用简化语义化版本：

```text
MAJOR.MINOR.PATCH
```

例如：

```text
0.3.0
```

## 版本含义

### MAJOR

表示项目学习主线发生重大变化。

例如：

- 从单 agent 变成多 agent 架构
- 从本地 CLI 变成完整 TUI/GUI
- 从学习 demo 变成生产化框架

当前项目仍处于 `0.x`，表示学习版早期阶段，接口和结构可以继续调整。

### MINOR

表示完成一个清晰的学习里程碑，通常对应一个 **大特性**。

例如：

- `0.1.0`: 最小工具调用闭环
- `0.2.0`: 工具系统、权限、provider 适配、意图门控
- `0.2.1`: diff/patch 编辑增强
- `0.3.0`: task/todo 状态
- `0.4.0`: 流式输出

### PATCH

表示修复、文档同步、小范围行为调整，通常对应 **小特性**、bug fix 或文档维护。

例如：

- 修复 provider 适配 bug
- 修正 prompt 行为
- 增加测试
- 补文档

## 特性分级

为了避免版本号被小改动推得太快，本项目区分“大特性”和“小特性”。

### 大特性

大特性是能形成一个清晰学习阶段的能力，通常会改变 agent 的架构、核心流程或学习主题。

大特性通常推动 `MINOR` 版本。

判断标准：

- 引入新的核心模块
- 改变主循环、工具系统、权限系统、上下文系统等关键路径
- 对学习路线有独立章节价值
- 需要更新架构文档和 roadmap
- 通常需要新增一组测试

例子：

- LLM provider 适配层
- 工具系统
- 权限系统
- 意图识别 / 工具使用门控
- diff/patch 编辑流程
- task/todo 状态
- 流式输出
- MCP 工具注册
- 多 agent 分工

### 小特性

小特性是在现有模块内增强体验、补齐边界或修正行为。

小特性通常推动 `PATCH` 版本，或者只记录到当前未发布 changelog 中。

判断标准：

- 不引入新的核心模块
- 不改变主学习阶段
- 只增强已有能力
- 风险较小、范围清晰
- 文档可在 current features 或 Q&A 中补充

例子：

- shell 只读命令分类
- prompt 输出收敛
- provider reasoning 续传
- 权限规则匹配顺序调整
- README 和文档入口整理
- 增加某个边界测试

### 修复和文档

修复和文档维护通常推动 `PATCH`，但如果只是尚未发布的当前工作，可以只更新文档和 changelog，不立刻改 `VERSION`。

例子：

- bug fix
- typo
- 补测试
- 补充技术 Q&A
- 更新 roadmap

## 版本提升规则

| 变更类型 | 版本影响 | 示例 |
|---|---|---|
| 学习主线重大变化 | `MAJOR` | 单 agent 到多 agent 主架构 |
| 大特性完成 | `MINOR` | `0.2.0` -> `0.3.0` |
| 小特性完成 | `PATCH` | `0.2.0` -> `0.2.1` |
| bug fix | `PATCH` | 修复 provider 适配 |
| 纯文档变更 | 通常不改版本；必要时 `PATCH` | 整理 README |

## 当前版本

当前版本记录在项目根目录：

```text
VERSION
```

当前版本：

```text
0.3.0
```

当前版本的既有特性已在 `CHANGELOG.md` 中按以下类别归档：

- Major Features
- Minor Features
- Fixes / Behavior Adjustments
- Documentation
- Tests

## 版本更新规则

每次版本变化至少更新：

- `VERSION`
- `CHANGELOG.md`
- `docs/current-features.md`
- `docs/roadmap.md`
- 必要时更新 `README.md` 和 `docs/architecture.md`

每次功能变化都要先判断：

```text
这是大特性、小特性、修复，还是纯文档？
```

再决定是否修改 `VERSION`。

## 当前版本路线

### `0.1.0`: 最小 Agent 闭环

目标：

- 用户输入
- 模型调用
- 工具调用
- 工具结果回传

### `0.2.0`: 安全可学习的 Agent 骨架

目标：

- LLM provider 适配层
- 工具系统
- 权限系统
- 工作区边界
- reasoning 续传
- 意图识别 / 工具使用门控
- 测试和长期文档体系

### `0.2.1`: 可解释的代码编辑增强

目标：

- diff 预览
- patch 风格编辑
- 修改前后可见
- 更适合学习 coding agent 如何安全改文件

说明：这是工具系统内的小特性增强，不单独作为新的学习阶段。

### `0.3.0`: Task/Todo 状态

目标：

- 引入任务状态模块
- 支持较大任务拆解
- 支持执行过程中的状态更新
- 学习 agent 如何保持任务进度

### `0.4.0`: 流式输出

计划目标：

- 支持模型 token 级输出
- 学习 agent 如何处理 streaming event
- 为更接近 Claude Code 的交互体验打基础
