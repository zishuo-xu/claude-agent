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

### Review

- 收敛版本策略：以后 bugfix、acceptance、review、docs-only、test-only 默认不单独升正式版本。
- 保留既有历史版本，不回滚已经发布的版本记录。

### Docs

- 新增 `docs/maintenance-log.md`，承接不需要升版本的维护记录。
- 更新 `docs/versioning.md`，明确只有能力边界变化才提升 `VERSION`。
