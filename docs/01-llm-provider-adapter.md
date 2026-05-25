# LLM Provider Adapter

本项目最初直接调用 Anthropic SDK。为了支持其他 OpenAI-compatible `/v1` 模型服务，现在加入了 `mini_agent/llm.py` 作为模型适配层。

## 为什么需要适配层？

Claude Code 的核心不是某一个 SDK 调用，而是这条 agent 主线：

```text
messages -> model -> tool_use -> tool_result -> model
```

不同模型服务的 API 形状不一样：

- Anthropic Messages API 使用 `tool_use` / `tool_result` content block
- OpenAI-compatible Chat Completions 使用 `tool_calls` / `role=tool`

如果 runtime 直接依赖某个 SDK，学习者会很难看清 agent 主循环本身。所以我们把差异放进适配层。

## 当前结构

- `LLMClient`: runtime 依赖的最小协议，暴露 `complete()` 和 `stream_complete()`
- `AnthropicLLM`: Anthropic Messages API 适配器
- `OpenAICompatibleLLM`: OpenAI-compatible `/v1/chat/completions` 适配器
- `TextBlock` / `ToolUseBlock` / `ReasoningBlock` / `LLMResponse`: agent 内部统一格式
- `TextDeltaEvent` / `FinalResponseEvent`: runtime 看到的统一 streaming 事件

## OpenAI-compatible 转换规则

发给模型时：

- 内部 `assistant` 的 `tool_use` block 转成 OpenAI `tool_calls`
- 内部 `tool_result` block 转成 OpenAI `role=tool`
- 工具 schema 从 Anthropic 风格的 `input_schema` 转成 OpenAI function `parameters`

模型返回时：

- `message.content` 转成 `TextBlock`
- `message.tool_calls` 转成 `ToolUseBlock`
- `message.reasoning_content` 转成内部 `ReasoningBlock`
- `model_extra.reasoning_content` 也会转成内部 `ReasoningBlock`
- 无效 JSON 工具参数保留为 `{"raw_arguments": "..."}`

这样 `AgentRuntime` 不需要知道底层 provider 是 Anthropic 还是 OpenAI-compatible。

## Streaming 边界

OpenAI-compatible streaming 会把文本 delta、reasoning delta 和工具调用 delta 分块返回。适配层使用 `OpenAIStreamAccumulator` 重建内部最终响应。

一些 provider 会返回 `choices=[]` 的 usage 或结束 chunk。适配层会跳过这类 chunk，避免 runtime 访问 `choices[0]` 崩溃。

## reasoning_content 续传

有些 OpenAI-compatible 服务会启用 thinking/reasoning 模式。它们会在 assistant 消息里返回 `reasoning_content`，并要求下一轮请求把这段内容原样带回去。

如果丢掉它，下一轮工具结果回传时可能报错：

```text
The reasoning_content in the thinking mode must be passed back to the API.
```

因此本项目在适配层保留了一个内部 `ReasoningBlock`：

```text
provider reasoning_content -> ReasoningBlock -> provider reasoning_content
```

这属于 provider 适配细节，不参与本地工具执行，也不会打印给用户。

## 当前配置

`.env` 使用：

```bash
LLM_PROVIDER=openai-compatible
LLM_BASE_URL=https://example.com/v1
LLM_API_KEY=your-api-key
LLM_MODEL_NAME=your-model-name
```

## 简化点

为了保持学习友好，当前还没有实现：

- provider 能力探测
- tool calling 兼容性降级
- 多模态输入
- retry/backoff
- token 级预算统计

这些都可以作为后续学习 Claude Code 时逐步扩展的模块。
