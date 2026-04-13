# TASK-002H7B GitHub 平台最终闭环证据提交任务单

- 任务编号：TASK-002H7B
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 17:02 CST
- 作者：技术架构师
- 审计来源：TASK-002H7A 审计意见书第 59 份通过，但 Hosted Runner Run URL、artifact 核验、required check 配置仍为 `<pending>`，需管理员完成真实平台动作后提交最终证据复审
- 架构裁决：TASK-002H7B 是进入 TASK-006 前最后一项平台证据门禁；只有 hosted runner artifact 与主干 required check 均完成并通过审计，才允许进入 TASK-006
- 前置依赖：TASK-002H7A 已通过审计意见书第 59 份；继续遵守外发模块 V1.27、ADR-055
- 任务边界：只提交 GitHub 平台最终证据、更新 CI 证据 README、请求审计复核；不得修改外发结算业务逻辑、不得进入 TASK-006、不得调用 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H7B
模块：GitHub 平台最终闭环证据提交
优先级：P0（TASK-006 前最后门禁）
════════════════════════════════════════════════════════════════════════════

【任务目标】
在仓库管理员完成 Hosted Runner 实跑和 required check 配置后，提交完整证据给审计官复审，关闭外发结算 PostgreSQL CI 门禁的最后阻塞。

【模块概述】
TASK-002H7A 已把管理员操作步骤、证据字段和 required check 名称模板化，审计已确认模板合格。但模板不是最终闭环，当前 `<pending>` 字段必须由真实 GitHub hosted runner 和分支保护配置结果替换。本任务只做证据提交，不做任何业务开发。

【执行前提】
1. 仓库管理员已经触发 `Backend PostgreSQL Hard Gate`。
2. workflow 已在 GitHub Actions hosted runner 上成功完成。
3. 已下载或在线核验 `postgresql-gate-junit` artifact。
4. JUnit 结果为 `tests=4, skipped=0, failures=0, errors=0`。
5. 已将 `Backend PostgreSQL Hard Gate / subcontract-postgresql-gate` 或 GitHub 实际等效 check 配置为主干 required check。
6. workflow log 和 artifact 已完成敏感信息扫描。

【涉及文件】
必须更新：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/README.md

允许新增：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/postgresql-gate-junit-summary.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/required-check-config.md

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
- 任意 TASK-006 业务实现文件

【必须提交的证据】
1. GitHub Actions run URL。
2. Workflow 名称：`Backend PostgreSQL Hard Gate`。
3. Job/check 名称：`subcontract-postgresql-gate` 或 GitHub 实际显示名称。
4. Runner 类型：GitHub Actions hosted runner。
5. PostgreSQL 测试库名：`lingyi_test_ci` 或实际测试库名，只写库名，不写完整 DSN。
6. Artifact 名称：`postgresql-gate-junit` 或实际 artifact 名称。
7. JUnit 摘要：
   - `tests=4`
   - `skipped=0`
   - `failures=0`
   - `errors=0`
8. 4 条 PostgreSQL marker 用例名称：
   - 同 key 并发 lock replay
   - 同 key 并发 release replay
   - 同 key 不同 payload 冲突
   - operation 唯一约束存在并生效
9. Required check 配置：
   - 目标分支：`main` / `master` / 实际主干分支
   - 配置方式：Branch protection / Ruleset
   - required check 名称：GitHub 实际显示名称
   - 配置状态：已配置
   - 配置人和配置时间
10. 敏感信息扫描结果：
   - workflow log 未发现完整 DSN、账号、密码、token
   - artifact 未发现完整 DSN、账号、密码、token
   - 证据 README 未发现完整 DSN、账号、密码、token

【CI门禁证据 README 更新要求】
必须将所有 `<pending>` 替换为真实值。不得保留以下字段为 `<pending>`：
- Run URL
- Runner
- Artifact
- JUnit tests
- JUnit skipped
- JUnit failures
- JUnit errors
- Required check target branch
- Required check name
- Required check status
- Configured by
- Configured at
- Sensitive log scan

【验收标准】
□ `CI门禁证据/README.md` 已无关键 `<pending>` 字段。  
□ GitHub Actions run URL 可打开并指向 `Backend PostgreSQL Hard Gate`。  
□ Hosted runner 执行成功。  
□ JUnit artifact 已核验。  
□ JUnit `tests=4`。  
□ JUnit `skipped=0`。  
□ JUnit `failures=0`。  
□ JUnit `errors=0`。  
□ 4 条 PostgreSQL marker 用例名称已记录。  
□ required check 已配置到主干 branch protection 或 ruleset。  
□ required check 名称为 GitHub 实际显示名称。  
□ workflow log、artifact、证据 README 均未泄露完整 DSN、账号、密码、token。  
□ 已把证据提交给审计官复审。  
□ 未修改外发结算业务逻辑。  
□ 未创建 TASK-006 对账单主表。  
□ 未调用 ERPNext 写接口。  

【回报格式】
管理员/工程师完成后按以下格式回报审计官：

```text
TASK-002H7B GitHub 平台最终闭环证据提交完成。

GitHub Actions：
- workflow：Backend PostgreSQL Hard Gate
- job/check：subcontract-postgresql-gate / <GitHub 实际名称>
- run URL：<GitHub Actions hosted runner run URL>
- runner：GitHub Actions hosted runner
- PostgreSQL 测试库：lingyi_test_ci（仅库名，已脱敏）

JUnit artifact：
- artifact 名称：postgresql-gate-junit / <实际名称>
- tests：4
- skipped：0
- failures：0
- errors：0
- 用例覆盖：并发 lock replay、并发 release replay、不同 payload 冲突、operation 唯一约束

Required check：
- 目标分支：main/master/<实际分支>
- 配置方式：Branch protection / Ruleset
- required check 名称：<GitHub 实际显示名称>
- 配置状态：已配置
- 配置人：<账号>
- 配置时间：YYYY-MM-DD HH:MM CST

安全检查：
- workflow log 敏感信息扫描：未发现完整 DSN、账号、密码、token
- artifact 敏感信息扫描：未发现完整 DSN、账号、密码、token
- 证据 README 敏感信息扫描：未发现完整 DSN、账号、密码、token

改动文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/README.md
- [如新增 summary/config 文件，列出路径]

风险/说明：
- [如无，写“无”]
```

【禁止事项】
- 禁止保留关键字段为 `<pending>` 后回报完成。
- 禁止用本地 `.pytest-postgresql.xml` 替代 hosted runner artifact。
- 禁止只提供截图，不提供 JUnit 四项摘要。
- 禁止 required check 未配置就回报完成。
- 禁止使用非 GitHub 实际显示名称作为 required check 名称。
- 禁止在日志、artifact、README 或回报中泄露完整 DSN、账号、密码、token。
- 禁止修改外发结算业务逻辑。
- 禁止进入 TASK-006 代码实现。
- 禁止创建加工厂对账单主表、Purchase Invoice、Payment Entry 或 GL。
- 禁止调用 ERPNext 写接口。

【前置依赖】
TASK-002H7A 审计意见书第 59 份通过。

【后置门禁】
TASK-002H7B 通过审计后，允许进入 TASK-006 加工厂对账单模块开发。

【预计工时】
0.25 天

════════════════════════════════════════════════════════════════════════════
