# PostgreSQL Hard Gate CI Evidence (TASK-002H7C)

## 当前状态

- 状态：`待仓库管理员闭环`
- 目标：清零全部关键 `<pending>` 字段并提交审计官最终复审
- 边界确认：未修改外发结算业务逻辑；未进入 TASK-006

## 固定门禁对象

- Workflow：`Backend PostgreSQL Hard Gate`
- Job/Check：`subcontract-postgresql-gate`
- Required check（目标）：`Backend PostgreSQL Hard Gate / subcontract-postgresql-gate`（或 GitHub 实际显示等效名称）

## Hosted Runner 证据（管理员回填）

- Run URL：`<pending>`
- Run status：`<pending>`
- Runner：`<pending>`
- Artifact：`<pending>`
- JUnit tests：`<pending>`
- JUnit skipped：`<pending>`
- JUnit failures：`<pending>`
- JUnit errors：`<pending>`
- PostgreSQL test database（name only）：`<pending>`

## Required Check 配置（管理员回填）

- Required check target branch：`<pending>`
- Required check name（GitHub exact display）：`<pending>`
- 配置方式（Branch protection / Ruleset）：`<pending>`
- Required check status：`<pending>`
- Configured by：`<pending>`
- Configured at（CST）：`<pending>`

## 安全检查（管理员回填）

- workflow log 敏感信息扫描：`<pending>`
- artifact 敏感信息扫描：`<pending>`
- evidence 文档敏感信息扫描：`<pending>`

要求：不得出现完整 DSN、账号、密码、token。

## PostgreSQL Marker 覆盖（管理员回填）

- 同 key 并发 lock replay：`<pending>`
- 同 key 并发 release replay：`<pending>`
- 同 key 不同 payload 冲突：`<pending>`
- operation 唯一约束存在并生效：`<pending>`

## Pending 清零清单（必须全部完成）

1. Hosted Runner run URL
2. Runner 类型
3. Artifact 名称
4. JUnit tests
5. JUnit skipped
6. JUnit failures
7. JUnit errors
8. PostgreSQL 测试库名（仅库名）
9. Required Check 目标分支
10. Required Check 配置方式
11. Required Check GitHub 实际显示名称
12. Required Check 配置状态
13. Configured by
14. Configured at
15. workflow log 敏感信息扫描结果
16. artifact 敏感信息扫描结果
17. evidence 文档敏感信息扫描结果

## 管理员闭环步骤

1. 在 GitHub Actions 手动触发 `Backend PostgreSQL Hard Gate`（workflow_dispatch）。
2. 等待 `subcontract-postgresql-gate` 成功完成。
3. 核验 artifact JUnit：`tests=4`、`skipped=0`、`failures=0`、`errors=0`。
4. 在主干 Branch Protection 或 Ruleset 配置 required check。
5. 回填本文件及同目录两份证据文件的全部关键 `<pending>`。
6. 向审计官提交最终复审材料。
