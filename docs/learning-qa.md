# Learning Notes

这份文档是独立学习沉淀，不参与日常上下文加载。

它只记录高价值技术解释：实现机制、架构原理、Claude 对照、provider 行为、报错原因。普通聊天、规划、偏好和操作指令不写入。

写法原则：每个问题只保留结论、原因、影响和关键代码位置；不复制长篇对话。

## 2026-05-20

### Q: Verification 只读验证子 Agent 有什么作用？

它是只读验收员。主 Agent 负责执行，Verification 负责独立检查结果是否可靠，重点看问题、缺失测试、回归和证据不足。

对应 Claude 的 Verification Agent / AgentTool 思想。本项目中它使用独立 runtime、只读工具，最终返回 `passed` / `failed` / `inconclusive` 风格总结。

关键位置：`mini_agent/subagent.py`、`tests/test_subagent.py`。版本：`0.6.1`。

### Q: Explore / Plan 子 Agent 有什么作用？

核心是上下文隔离和角色隔离。探索、阅读、规划会产生大量中间工具结果，放在子 Agent 内部处理，主 Agent 只接收最终总结。

对应 Claude 的 AgentTool / built-in agents。本项目只实现内置只读版，不支持自定义 Agent、插件、后台并行、独立模型和 worktree 隔离。

关键位置：`mini_agent/subagent.py`。版本：`0.6.0`。

### Q: micro-compact 和 full compact 有什么区别？

micro-compact 是轻量压缩：不调用模型，只把旧工具结果替换为短占位文本。full compact 是强压缩：让模型总结旧消息，只保留摘要和最近原始消息。

执行顺序：

```text
上下文超预算 -> micro-compact -> 仍超预算 -> full compact
```

关键位置：`mini_agent/context.py`、`mini_agent/runtime.py`。版本：`0.5.0`。

### Q: 为什么 streaming 答案输出完后还会 `IndexError: list index out of range`？

OpenAI-compatible streaming 可能返回 `choices=[]` 的 usage/结束 chunk。旧代码直接访问 `chunk.choices[0]`，所以在结束阶段崩溃。

修复：streaming 循环先判断空 `choices` 并跳过。

关键位置：`mini_agent/llm.py`、`tests/test_llm_adapter.py`。版本：`0.4.1`。

### Q: Diff 预览和 patch 工具有什么作用？

作用是让代码修改可见、可审查、可确认。agent 不应该总是直接写文件，而应尽量先展示 diff，再按权限应用修改。

当前相关工具：`preview_edit`、`apply_edit`、`edit_file`。

关键位置：`mini_agent/builtin_tools.py`。

### Q: 为什么“我想学习 Python”会输出项目 README 和架构？

原因是早期 prompt 没有区分“泛学习请求”和“结合当前项目学习”。模型把学习 Python 误扩展成介绍本项目。

修复：泛学习请求默认不读 workspace，不介绍项目；只有用户明确要求结合项目时才读取文件。

关键位置：`mini_agent/runtime.py`、`tests/test_runtime_intent.py`。

### Q: 为什么“我想学习 python”会触发 `pwd` 和权限确认？

原因是模型想确认当前目录，调用了 `run_shell {"command":"pwd"}`。早期 `run_shell` 默认被视为非只读工具，所以 `plan` 模式要求确认。

修复：给常见只读 shell 命令做保守分类；包含组合符、管道、重定向等内容时仍不自动放行。

关键位置：`mini_agent/builtin_tools.py`、`tests/test_permissions.py`。

### Q: 为什么只问“你好”会输出很多系统设计？

原因是早期 system prompt 过度强调项目和架构，没有要求寒暄短回答。

修复：寒暄和普通聊天短回答；只有用户明确问架构、工具、权限或实现时才展开。

关键位置：`mini_agent/runtime.py`、`tests/test_runtime_intent.py`。

### Q: system prompt 里两条响应分级规则有什么作用？

第一条约束寒暄：短回答，不介绍项目架构。第二条约束解释范围：只有被问到或任务需要时才讲架构、工具、权限和实现细节。

合起来形成响应分级：

```text
寒暄 -> 短回答
明确提问 -> 解释
执行任务 -> 调工具/改代码/测试/更新文档
```

关键位置：`mini_agent/runtime.py`。

### Q: 为什么 provider 会报 `reasoning_content in the thinking mode must be passed back`？

OpenAI-compatible thinking/reasoning 模式下，模型返回的 `reasoning_content` 是下一轮工具调用上下文的一部分。旧适配层只保存 tool call，丢了 reasoning 内容，provider 认为上下文不完整。

修复：引入内部 `ReasoningBlock`，保存但不展示 reasoning 内容，并在下一轮请求中传回 provider。

关键位置：`mini_agent/llm.py`、`docs/01-llm-provider-adapter.md`、`tests/test_llm_adapter.py`。

### Q: 伪工具调用修复改了什么？

问题：模型有时不会返回真实 tool call，而是输出 XML/JSON/function-parameter 形式的工具调用文本，导致用户看到内部标记或子 Agent 没被真正执行。

修复：

- intent 能识别显式 `explore_agent` / `plan_agent` / `verify_agent`
- tool policy 只暴露被点名工具
- runtime 将简单伪工具标记转换为内部 `ToolUseBlock`
- 伪工具调用文本不直接展示
- 转换时保留 `ReasoningBlock`

关键位置：`mini_agent/intent.py`、`mini_agent/tool_policy.py`、`mini_agent/runtime.py`。

### Q: 当前 Agent Loop 是怎么做的？

核心在 `AgentRuntime.run_user_turn()`：

```text
用户输入
  -> classify_intent()
  -> append user message
  -> compact_if_needed()
  -> select visible tools
  -> call LLM
  -> append assistant
  -> no tool_use: return text
  -> tool_use: validate -> permission -> run -> append tool_result -> next turn
```

它对应 Claude 的 `queryLoop`：模型、工具、本地执行和工具结果回传组成一个可重复闭环。

关键位置：`mini_agent/runtime.py`。
