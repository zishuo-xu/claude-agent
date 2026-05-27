# Maintenance Log

这份文档记录不单独提升 `VERSION` 的维护类工作。

适合记录：

- Bug Fix
- Acceptance
- Review
- Docs
- Test-only

原则：

- 简短记录事实和验证结果。
- 不重复 `CHANGELOG.md` 的正式版本说明。
- 不把维护记录扩写成设计文档。

## 2026-05-27

### Review

- 复查 `classify_intent()` 中的硬边界和语义猜测：危险请求、显式工具名、项目文档入口、明确文件生成请求仍适合保留在客户端边界。
- 宽泛学习词、宽泛编码词和部分项目词仍带有语义分类性质，后续只在真实误判出现时收敛，不引入 LLM intent classifier。
- 结论：当前方向继续贴近 Claude 的“模型决定下一步，客户端守边界”，但 mini-claude 保留轻量工具可见性保护；本次不改代码、不升版本。

### Acceptance

- 真实 CLI 执行 Context Preflight 长任务验收：创建并修改 `tmp_context_acceptance/mini_notes.py`，验证 `NoteStore.add/list_titles/search/count` 和 `__main__` 自检。
- 发现问题：模型运行脚本时使用裸 `python tmp_context_acceptance/mini_notes.py`，在当前环境不友好。
- 修复记录为 `0.28.2`：workspace 有 `.venv` 时，`run_shell` 拒绝裸 Python 脚本命令并引导使用 `.venv/bin/python script.py`。
- 复验通过：真实 CLI 中模型被拒绝后自动改用 `.venv/bin/python tmp_context_acceptance/mini_notes.py`，自检退出码 0。
- 验收 `0.28.1` Context Preflight Token Guard。
- 正常预算真实 CLI 冒烟受外部 LLM 配置阻断：当前 `.env` 返回 `401 invalid_key`，因此未能验证真实模型回复。
- 极低预算真实 CLI 验收通过：使用 `--context-char-budget 50` 输入长文本，runtime 在模型调用前输出 `Context preflight stopped before the model call`，没有触发外部 API 401。
- 更新本地 `.env` 的 `LLM_API_KEY` 后复验正常预算真实 CLI：寒暄可直接回复，项目架构问题会读取 `docs/architecture.md` 后简洁回答。
- 结论：常规模型闭环和超预算阻断路径均符合预期；本次不改代码、不升版本。
- 真实 `agent.py` CLI 压力验收开始执行 `docs/stress-test-cases.md`。案例 1 未通过：模型把“长压力测试”发散成系统压力脚本 `stress_test.py`，没有严格完成 `calc.py` 的 `add/subtract/multiply/divide` 和 `__main__` 正确性自检。
- 结论：真实 CLI 自由对话压力测试已暴露任务遵循问题，未继续标记全量通过；失败现场临时目录 `tmp_stress_code/` 暂时保留。
- `0.27.4` 后真实 CLI 复验案例 1：模型按步骤创建并修改 `tmp_stress_code/calc.py`，实现 `add/subtract/multiply/divide` 和除 0 自检，外部核对 `python3 tmp_stress_code/calc.py` 输出 `ok`。
- 观察：`--max-turns 16` 下任务在总结阶段触发 stopped，需要用户说“继续”完成总结；后续可单独验收完成后停止体验。
- 按 `docs/stress-test-cases.md` 执行全部 10 个压力案例，覆盖代码、写作、上下文、大文件、权限取消、项目问答、错误恢复和综合验收。
- 结果：全部通过。案例 6 首轮因验证脚本虚拟环境路径写错失败，修正后重跑通过；临时目录已清理。
- 说明：本轮是按案例内容做本地确定性验收，并用命令和内容断言核对正确性；真实 LLM CLI 自由对话仍可作为下一轮单独验收。
- 用临时工作区验收长代码任务：创建 `calc.py`，连续多轮追加 `subtract`、`multiply`、`divide`，补充自检并运行 `python3 calc.py`。
- 结论：deterministic runtime 验收通过，Agent Loop 可以完成多轮创建、修改和验证；真实模型自由对话仍需 CLI 继续验收。
- 验收会话焦点短追问：内容生成后“就按这个来 / 整理一下 / 完整版本 / 保存一下”。
- 验收无焦点短句：“保存一下 / 就按这个来”会先澄清，不直接动工具。
- 验收项目焦点短追问：项目架构问答后“整理成文档”会基于当前回答落盘。
- 结论：`ConversationFocus` 当前方向稳定，暂不新增规则、不升版本。

## 2026-05-26

### Bug Fix

- 修复缺少目标路径的创作保存请求过早暴露写入工具的问题，正式记录为 `0.26.1`。
- 保存类请求缺少路径时先进入澄清；用户下一轮补充后恢复工具可用。
- 真实 CLI 验收通过：先澄清 -> 写入指定文件 -> 继续追加 -> 切换项目问答。

### Acceptance

- 验收普通问答、项目问答、文件创建运行、多轮创作保存任务。
- 发现普通泛学习回答仍可能偏短，项目问答和创作总结偶尔仍会使用表格；先记录观察，不扩大修复范围。

### Review

- 收敛版本策略：以后用户可见 bugfix 和小体验修复走 PATCH；acceptance、review、docs-only、test-only 默认不单独升正式版本。
- 保留既有历史版本，不回滚已经发布的版本记录。

### Docs

- 新增 `docs/maintenance-log.md`，承接不需要升版本的维护记录。
- 更新 `docs/versioning.md`，明确只有能力边界变化才提升 `VERSION`。
