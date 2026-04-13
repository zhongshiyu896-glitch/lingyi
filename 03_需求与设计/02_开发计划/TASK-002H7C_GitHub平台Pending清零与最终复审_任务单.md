# TASK-002H7C GitHub 平台 Pending 清零与最终复审任务单

- 任务编号：TASK-002H7C
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 17:10 CST
- 作者：技术架构师
- 审计来源：TASK-002H7B 审计意见书第 60 份通过，但 GitHub 平台闭环仍未完成；Hosted Runner、JUnit artifact、Required Check 三份证据文档仍存在 `<pending>` 字段
- 架构裁决：TASK-002H7C 不再接受模板化交付或本地证据替代；必须由仓库管理员完成 GitHub 平台真实动作并清零全部关键 `<pending>` 字段，审计通过后才允许进入 TASK-006
- 前置依赖：TASK-002H7B 已通过审计意见书第 60 份；继续遵守外发模块 V1.28、ADR-056
- 任务边界：只做 GitHub 平台真实执行、证据回填、pending 清零和最终复审；不得修改外发结算业务逻辑、不得进入 TASK-006、不得调用 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H7C
模块：GitHub 平台 Pending 清零与最终复审
优先级：P0（TASK-006 前最终放行门禁）
════════════════════════════════════════════════════════════════════════════

【任务目标】
由仓库管理员完成 GitHub hosted runner 实跑、JUnit artifact 核验、Required Check 配置，并把三份证据文档的关键 `<pending>` 字段全部清零后提交审计官最终复审。

【模块概述】
TASK-002H7B 已完成证据模板拆分并通过审计，但模板不是平台闭环。当前外发结算进入 TASK-006 前，只剩 GitHub 平台真实门禁未闭环：Hosted Runner run URL、artifact JUnit 四项、Required Check 配置状态必须全部有真实值。该任务是最终放行门禁，不再拆分模板任务。

【执行人】
仓库管理员 / DevOps 管理员 / 具备 GitHub Actions 与 Branch Protection 或 Ruleset 权限的负责人。

【必须更新的证据文件】
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/README.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/postgresql-gate-junit-summary.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/required-check-config.md

【禁止修改】
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
- 任意 TASK-006 业务实现文件

【必须执行】
1. 在 GitHub Actions 页面手动触发 `Backend PostgreSQL Hard Gate`。
2. 确认 workflow 在 GitHub Actions hosted runner 上执行。
3. 等待 `subcontract-postgresql-gate` 或 GitHub 实际等效 job/check 成功。
4. 下载或查看 `postgresql-gate-junit` artifact。
5. 核验 artifact：
   - `tests=4`
   - `skipped=0`
   - `failures=0`
   - `errors=0`
6. 核验 4 条 PostgreSQL marker 用例均出现：
   - 同 key 并发 lock replay
   - 同 key 并发 release replay
   - 同 key 不同 payload 冲突
   - operation 唯一约束存在并生效
7. 扫描 workflow log，不得出现完整 DSN、账号、密码、token。
8. 扫描 artifact，不得出现完整 DSN、账号、密码、token。
9. 将 `Backend PostgreSQL Hard Gate / subcontract-postgresql-gate` 或 GitHub 实际等效 check 配置为主干 required check。
10. 如果仓库使用 Ruleset，必须在 Ruleset 中配置同一 required check。
11. 回填三份证据文档中所有关键 `<pending>` 字段。
12. 提交审计官最终复审。

【关键 Pending 清零要求】
以下字段不得再是 `<pending>`：
1. Hosted Runner run URL
2. Runner 类型
3. Artifact 名称
4. JUnit tests
5. JUnit skipped
6. JUnit failures
7. JUnit errors
8. PostgreSQL 测试库名
9. Required Check 目标分支
10. Required Check 配置方式
11. Required Check GitHub 实际显示名称
12. Required Check 配置状态
13. Configured by
14. Configured at
15. Workflow log 敏感信息扫描结果
16. Artifact 敏感信息扫描结果
17. Evidence documents 敏感信息扫描结果

【验收标准】
□ 三份证据文档的关键 `<pending>` 字段全部清零。  
□ GitHub Actions hosted runner run URL 已填写。  
□ Run URL 指向 `Backend PostgreSQL Hard Gate`。  
□ Workflow run 成功。  
□ Artifact 名称已填写。  
□ JUnit `tests=4`。  
□ JUnit `skipped=0`。  
□ JUnit `failures=0`。  
□ JUnit `errors=0`。  
□ 4 条 PostgreSQL marker 用例名称已记录。  
□ Required Check 已配置到主干 Branch Protection 或 Ruleset。  
□ Required Check 名称为 GitHub 实际显示名称。  
□ 配置人和配置时间已记录。  
□ workflow log 未泄露完整 DSN、账号、密码、token。  
□ artifact 未泄露完整 DSN、账号、密码、token。  
□ 证据文档未泄露完整 DSN、账号、密码、token。  
□ 已提交审计官最终复审。  
□ 未修改外发结算业务逻辑。  
□ 未进入 TASK-006 代码实现。  
□ 未调用 ERPNext 写接口。  

【回报格式】
```text
TASK-002H7C GitHub 平台 Pending 清零与最终复审完成。

GitHub Actions Hosted Runner：
- workflow：Backend PostgreSQL Hard Gate
- job/check：subcontract-postgresql-gate / <GitHub 实际名称>
- run URL：<GitHub Actions hosted runner run URL>
- run status：success
- runner：GitHub Actions hosted runner
- PostgreSQL 测试库：lingyi_test_ci（仅库名，已脱敏）

JUnit artifact：
- artifact 名称：postgresql-gate-junit / <实际名称>
- tests：4
- skipped：0
- failures：0
- errors：0
- 用例覆盖：并发 lock replay、并发 release replay、不同 payload 冲突、operation 唯一约束

Required Check：
- 目标分支：main/master/<实际分支>
- 配置方式：Branch protection / Ruleset
- required check 名称：<GitHub 实际显示名称>
- 配置状态：已配置
- 配置人：<账号>
- 配置时间：YYYY-MM-DD HH:MM CST

Pending 清零：
- README.md：已清零
- postgresql-gate-junit-summary.md：已清零
- required-check-config.md：已清零

安全检查：
- workflow log 敏感信息扫描：未发现完整 DSN、账号、密码、token
- artifact 敏感信息扫描：未发现完整 DSN、账号、密码、token
- 证据文档敏感信息扫描：未发现完整 DSN、账号、密码、token

改动文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/README.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/postgresql-gate-junit-summary.md
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/required-check-config.md

风险/说明：
- [如无，写“无”]
```

【禁止事项】
- 禁止继续提交模板或部分回填内容。
- 禁止保留关键 `<pending>` 字段后回报完成。
- 禁止用本地 `.pytest-postgresql.xml` 替代 hosted runner artifact。
- 禁止只提供截图，不提供 JUnit 四项摘要。
- 禁止 Required Check 未配置就回报完成。
- 禁止使用非 GitHub 实际显示名称作为 Required Check 名称。
- 禁止泄露完整 DSN、账号、密码、token。
- 禁止修改外发结算业务逻辑。
- 禁止进入 TASK-006 代码实现。
- 禁止创建加工厂对账单主表、Purchase Invoice、Payment Entry 或 GL。
- 禁止调用 ERPNext 写接口。

【前置依赖】
TASK-002H7B 审计意见书第 60 份通过。

【后置门禁】
TASK-002H7C 通过审计后，允许进入 TASK-006 加工厂对账单模块开发。

【预计工时】
0.25 天

════════════════════════════════════════════════════════════════════════════
