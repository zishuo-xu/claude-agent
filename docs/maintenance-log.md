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

## 2026-05-26

### Bug Fix

- 修复缺少目标路径的创作保存请求过早暴露写入工具的问题。
- 保存类请求缺少路径时先进入澄清；用户下一轮补充后恢复工具可用。
- 真实 CLI 验收通过：先澄清 -> 写入指定文件 -> 继续追加 -> 切换项目问答。

### Acceptance

- 验收普通问答、项目问答、文件创建运行、多轮创作保存任务。
- 发现普通泛学习回答仍可能偏短，项目问答和创作总结偶尔仍会使用表格；先记录观察，不扩大修复范围。

### Review

- 收敛版本策略：以后 bugfix、acceptance、review、docs-only、test-only 默认不单独升正式版本。
- 保留既有历史版本，不回滚已经发布的版本记录。

### Docs

- 新增 `docs/maintenance-log.md`，承接不需要升版本的维护记录。
- 更新 `docs/versioning.md`，明确只有能力边界变化才提升 `VERSION`。
