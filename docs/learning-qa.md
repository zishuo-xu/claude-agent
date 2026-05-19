# Learning Q&A

这个文档用于沉淀学习过程中提出的技术疑问和解答。

规则：只有当学习者提出关于实现机制、架构原理、Claude Code 对照、LLM provider 行为、报错原因等技术问题时，才把高价值解释追加到这里。

不记录普通聊天、项目规划、偏好约定、下一步安排、简单操作指令。这些内容应放到 `docs/current-features.md`、`docs/architecture.md` 或 `PROJECT_PRINCIPLES.md`。

## 2026-05-20

### Q: Diff 预览和 patch 工具有什么作用？

Diff 预览和 patch 工具的核心作用是：**让 agent 的代码修改变得可见、可审查、可控制**。

当前 `write_file` / `edit_file` 可以直接修改文件，但学习者不容易在修改前看清楚：

- 哪个文件会被改
- 哪些行会被删
- 哪些行会被加
- 修改范围是否过大
- 模型有没有误改无关内容

Diff 预览会把修改前后差异展示出来：

```diff
- old line
+ new line
```

Patch 工具则把“修改”变成一个更明确的步骤：

```text
模型提出修改 -> 生成 diff -> 权限/用户确认 -> 应用 patch -> 测试验证
```

它的学习价值：

1. **理解 coding agent 如何安全改文件**
   agent 不应该只是直接写文件，而应尽量让修改过程可检查。

2. **降低误改风险**
   用户或权限系统可以先看到修改摘要，再决定是否允许。

3. **更接近 Claude Code 的体验**
   Claude Code 类 coding agent 很重视修改前后的可见性，diff 是核心中间表示。

4. **方便测试和回滚**
   patch 比整文件写入更容易定位变更，也更适合做小步修改。

5. **帮助学习者建立代码审查习惯**
   看 diff 是理解和审查代码修改的基本能力。

在本项目中，`0.3.0` 计划通过 diff/patch 能力，把文件编辑流程从：

```text
直接写文件
```

升级为：

```text
先展示差异，再应用修改
```

对应规划：

- `docs/roadmap.md`: `P1 / 大特性 / 0.3.0: Diff 预览和 patch 工具`

### Q: 为什么我说“我想学习 Python”，agent 又输出了很多项目 README 和架构信息？

这是因为上一版 prompt 只限制了“寒暄”和“架构解释”，但没有单独限制“泛学习请求”。

“我想学习 Python”本质上不是一个代码执行任务，也不是“请用当前项目教我 Python”。更合理的回答应该是短短问一句基础水平，或者给一个简洁学习路径。

错误行为是：

1. agent 看到“学习 Python”
2. 联想到当前项目是 Python 写的学习 agent
3. 主动读取或引用项目 README
4. 把 Claude Code 对照阅读路线、项目功能、下一步扩展都讲出来

这对用户来说就是噪音。

本项目的修复方式是在 `SYSTEM_PROMPT` 里增加“泛学习请求”规则：

```text
For general learning requests like "I want to learn Python", do not inspect the workspace or describe this project unless the user explicitly asks to use the project as learning material. Give a concise learning path or ask about their current level.
```

修复后的预期行为：

```text
可以。你现在是零基础，还是已经会一点语法？如果零基础，我建议先从变量、条件、循环、函数开始。
```

只有当用户明确说：

```text
用这个项目教我 Python
```

或者：

```text
结合当前代码讲 Python
```

agent 才应该读取项目文件并解释。

对应代码：

- `mini_agent/runtime.py`: `SYSTEM_PROMPT`
- `tests/test_runtime_prompt.py`: prompt 约束测试
- `docs/current-features.md`: 对话循环能力说明

### Q: 为什么我说“我想学习 python”，agent 要执行 `pwd`，还问 `Allow run_shell ...`？

这段输出：

```text
[tool] run_shell {'command': 'pwd', 'timeout_seconds': 5}
[permission] write/destructive action in plan mode
Allow run_shell {'command': 'pwd', 'timeout_seconds': 5}? [y/N]
```

意思是：

1. 模型决定先执行 `pwd`，想确认当前工作目录
2. `pwd` 是通过 `run_shell` 工具执行的
3. 当前启动模式是 `plan`
4. `plan` 模式只自动允许只读操作
5. 之前 `run_shell` 整体默认不是只读工具，所以权限系统要求用户确认

这里的提示文案说 `write/destructive action`，不是因为 `pwd` 真会写文件，而是因为我们的工具风险分类太粗：`run_shell` 这个工具可能执行任何 shell 命令，所以默认被当成非只读。

修复方式是给 `run_shell` 加一个保守的只读命令分类：

```text
pwd, ls, find, cat, head, tail, wc, rg, grep,
git status, git diff, git log, git show, git branch
```

同时，如果命令里包含这些组合或重定向符号，就不会自动视为只读：

```text
;  &&  ||  |  >  >>  <  `  $(
```

例如：

```text
pwd
```

可以自动视为只读。

但：

```text
pwd && rm file.txt
```

不会被视为只读，仍会触发确认。

对应代码：

- `mini_agent/tools.py`: `is_read_only_shell_command()`
- `tests/test_tools.py`: shell 只读分类测试
- `docs/current-features.md`: 当前工具能力说明

### Q: 为什么我只问“你好”，agent 却输出很多系统设计？

原因是早期 `SYSTEM_PROMPT` 过于强调“Claude Code inspired learning agent”和“完成后总结”，但没有明确告诉模型区分普通寒暄、解释类问题和执行类任务。

对 LLM 来说，如果 system prompt 一直强调项目架构、工具、权限、学习目标，它可能会把一个简单的“你好”理解成“介绍自己和项目”，于是输出很多系统设计内容。

本项目的修复方式是在 `mini_agent/runtime.py` 的 `SYSTEM_PROMPT` 中加入响应分级规则：

```text
For greetings or casual chat, reply briefly and do not describe the project architecture unless asked.
Only explain architecture, tools, permissions, or implementation details when the user asks for them or when they are necessary to complete the task.
```

也就是说：

- 用户只是打招呼：短回答
- 用户问实现细节：解释并可追加到 `docs/learning-qa.md`
- 用户要求改代码：执行、测试、更新文档；如果代码、配置、依赖或运行行为变化，再启动 agent

这个问题提醒我们：agent 的 system prompt 不能只写“它能做什么”，还要写“什么时候不要做太多”。

对应代码：

- `mini_agent/runtime.py`: `SYSTEM_PROMPT`
- `docs/current-features.md`: 对话循环能力说明

### Q: `SYSTEM_PROMPT` 里新增的两条规则分别有什么作用？

新增规则：

```text
For greetings or casual chat, reply briefly and do not describe the project architecture unless asked.
Only explain architecture, tools, permissions, or implementation details when the user asks for them or when they are necessary to complete the task.
```

第一条规则的作用是处理“普通聊天”。

当用户说“你好”“在吗”“早上好”这类话时，agent 应该把它识别成寒暄，而不是项目任务。它应该短回答，例如：

```text
你好，我在。想继续看 agent 哪一块？
```

这条规则避免模型一上来介绍整个项目架构、工具系统、权限系统。

第二条规则的作用是处理“解释范围”。

agent 只有在用户明确问到实现、架构、工具、权限，或者完成任务必须解释这些内容时，才展开讲。否则它不主动输出大量背景信息。

它解决的是另一个常见问题：模型为了显得有帮助，可能会过度解释。对于 coding agent 来说，过度解释会打断使用体验。

两条规则合起来，就是一个简单的响应分级策略：

```text
寒暄 -> 短回答
明确提问 -> 解释
要求执行 -> 调工具/改代码/测试/更新文档
```

这也是学习 agent prompt 设计时很重要的一点：system prompt 不只要告诉模型“能做什么”，也要告诉模型“什么时候不要做太多”。

### Q: 为什么 OpenAI-compatible 服务会报 `reasoning_content in the thinking mode must be passed back`？

原因是当前 LLM 服务启用了 thinking/reasoning 模式。

在一次工具调用里，模型可能不只返回“要调用哪个工具”，还会返回一段 provider 要求保留的内部推理状态：

```text
assistant:
  reasoning_content: "..."
  tool_call:
    name: list_files
    arguments: {"path": "."}
```

程序执行本地工具后，需要把工具结果发回模型：

```text
tool:
  README.md
  agent.py
  mini_agent/
```

但这个工具结果必须和上一条 assistant 消息一起构成完整上下文。对于这个 provider 来说，上一条 assistant 消息里的 `reasoning_content` 也必须原样带回去。

如果只保存了 `tool_call`，却丢掉了 `reasoning_content`，下一轮请求就会变成“不完整的工具调用上下文”，服务端会拒绝并返回：

```text
The reasoning_content in the thinking mode must be passed back to the API.
```

本项目的修复方式是在 LLM 适配层里加入内部 `ReasoningBlock`：

```text
provider reasoning_content -> ReasoningBlock -> provider reasoning_content
```

也就是说：

1. 模型返回 `reasoning_content`
2. agent 不展示它，但保存到对话历史
3. 下一轮把工具结果发回模型时，把 `reasoning_content` 一起带回去
4. provider 就能继续接上上一轮的 thinking 状态

这个逻辑属于 provider 适配层细节。`AgentRuntime` 只需要继续处理统一的内部消息格式，不需要知道底层 API 的差异。

对应代码：

- `mini_agent/llm.py`: `ReasoningBlock`、`OpenAICompatibleLLM._get_reasoning_content()`、`_to_openai_messages()`
- `tests/test_llm_adapter.py`: `test_openai_adapter_preserves_reasoning_content_for_next_turn`
- `docs/01-llm-provider-adapter.md`: provider reasoning 续传说明
