# TASK-002H7A Hosted Runner 与 Required Check 管理员闭环任务单

- 任务编号：TASK-002H7A
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 16:55 CST
- 作者：技术架构师
- 审计来源：TASK-002H7 审计意见书第 58 份有条件通过，P1 阻断项为 Hosted Runner 实跑 URL 未提供、GitHub artifact 未核验、`Backend PostgreSQL Hard Gate / subcontract-postgresql-gate` 尚未配置为主干 required check
- 架构裁决：该任务必须由具备 GitHub Actions 与分支保护权限的仓库管理员执行；未完成前，TASK-006 不得进入主干
- 前置依赖：TASK-002H7 有条件通过；继续遵守外发模块 V1.26、ADR-054
- 任务边界：只做 GitHub 平台操作、证据归档、required check 配置和审计材料补齐；不得修改外发结算业务逻辑、不得进入 TASK-006、不得调用 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H7A
模块：Hosted Runner 与 Required Check 管理员闭环
优先级：P0（TASK-006 前最终门禁）
════════════════════════════════════════════════════════════════════════════

【任务目标】
由仓库管理员在 GitHub 平台完成 `Backend PostgreSQL Hard Gate` hosted runner 实跑、JUnit artifact 核验和主干 required check 配置，关闭 TASK-002H7 的权限阻塞项。

【模块概述】
TASK-002H7 已证明本地 hard gate、workflow 配置、JUnit 断言和证据 README 合格，但还没有仓库管理员权限完成 GitHub hosted runner 实跑与主干分支保护配置。该缺口不是代码缺陷，而是发布门禁未在 GitHub 平台真正生效。TASK-002H7A 的唯一目标是让平台门禁具备可审计证据和强制执行力。

【执行人要求】
1. 必须由仓库管理员、具备 branch protection / ruleset 权限的工程负责人，或 DevOps 管理员执行。
2. 普通工程师如果没有权限，不得声称完成，只能回报“权限阻塞”。
3. 所有回报必须使用脱敏信息，不得暴露完整 DSN、账号、密码、token。

【涉及文件】
必须更新：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/README.md

可能修改：
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/backend-postgresql.yml（仅限补 workflow_dispatch、artifact、job summary 或 check 名称稳定性）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md（仅限补 required check 操作说明）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
- 任意 TASK-006 业务实现文件

【管理员操作步骤】
1. 打开 GitHub 仓库 Actions 页面。
2. 找到 workflow：`Backend PostgreSQL Hard Gate`。
3. 使用 `workflow_dispatch` 手动触发一次。
4. 确认运行环境为 GitHub Actions hosted runner。
5. 确认 job/check 名称为 `subcontract-postgresql-gate` 或记录 GitHub 实际显示名称。
6. 等待 workflow 完成。
7. 下载或查看 artifact：`postgresql-gate-junit` 或 GitHub 实际 artifact 名称。
8. 核验 JUnit：
   - `tests=4`
   - `skipped=0`
   - `failures=0`
   - `errors=0`
9. 扫描 workflow log 和 artifact，不得包含完整 DSN、账号、密码、token。
10. 打开仓库 Settings -> Branches 或 Rulesets。
11. 在主干分支保护中加入 required check：`Backend PostgreSQL Hard Gate / subcontract-postgresql-gate` 或 GitHub 实际显示的等效 check 名称。
12. 如果仓库使用 ruleset，必须在 ruleset 中加入同一 required check。
13. 保存配置。
14. 更新 `CI门禁证据/README.md`，记录 run URL、artifact 名称、JUnit 摘要、required check 名称、配置人和配置时间。
15. 回报审计官复审。

【如使用 GitHub CLI】
```bash
cd /Users/hh/Desktop/领意服装管理系统

gh workflow run "Backend PostgreSQL Hard Gate"

gh run list --workflow "Backend PostgreSQL Hard Gate" --limit 5

# 用实际 run id 下载 artifact
gh run download <run_id> --name postgresql-gate-junit --dir /tmp/postgresql-gate-junit
```

说明：branch protection / ruleset 配置如果无法通过 CLI 完成，可使用 GitHub UI；但必须回报 exact required check 名称和配置截图/文字证据。

【CI门禁证据 README 必填内容】
```text
# PostgreSQL Hard Gate CI Evidence

- Workflow：Backend PostgreSQL Hard Gate
- Job/Check：subcontract-postgresql-gate
- Run URL：<GitHub Actions hosted runner run URL>
- Runner：GitHub Actions hosted runner
- Artifact：postgresql-gate-junit / <actual artifact name>
- JUnit tests：4
- JUnit skipped：0
- JUnit failures：0
- JUnit errors：0
- PostgreSQL test database：lingyi_test_ci（脱敏，仅库名）
- Required check target branch：main/master/<actual>
- Required check name：Backend PostgreSQL Hard Gate / subcontract-postgresql-gate
- Required check status：已配置
- Configured by：<管理员姓名或账号>
- Configured at：YYYY-MM-DD HH:MM CST
- Sensitive log scan：未发现完整 DSN、账号、密码、token
```

【验收标准】
□ GitHub Actions hosted runner 已实际执行 `Backend PostgreSQL Hard Gate`。  
□ 已提供 workflow run URL。  
□ workflow run 成功。  
□ 已下载或核验 JUnit artifact。  
□ JUnit `tests=4`。  
□ JUnit `skipped=0`。  
□ JUnit `failures=0`。  
□ JUnit `errors=0`。  
□ workflow log 未泄露完整 DSN、账号、密码、token。  
□ artifact 未泄露完整 DSN、账号、密码、token。  
□ required check 已配置到主干分支保护或 ruleset。  
□ required check 名称记录为 GitHub 实际显示名称。  
□ `CI门禁证据/README.md` 已记录 run URL、artifact、JUnit 摘要和 required check 配置结果。  
□ 如无管理员权限，必须回报权限阻塞，不得写“完成”。  
□ 未修改外发结算业务逻辑。  
□ 未创建 TASK-006 对账单主表。  
□ 未调用 ERPNext 写接口。  

【回报格式】
管理员/工程师完成后按以下格式回报：

```text
TASK-002H7A Hosted Runner 与 Required Check 管理员闭环完成。

GitHub Actions：
- workflow：Backend PostgreSQL Hard Gate
- job/check：subcontract-postgresql-gate / <GitHub 实际名称>
- run URL：<GitHub Actions hosted runner run URL>
- runner：GitHub Actions hosted runner

JUnit artifact：
- artifact 名称：postgresql-gate-junit / <实际名称>
- tests：4
- skipped：0
- failures：0
- errors：0

Required check：
- 目标分支：main/master/<实际分支>
- required check 名称：Backend PostgreSQL Hard Gate / subcontract-postgresql-gate
- 配置方式：Branch protection / Ruleset
- 配置状态：已配置
- 配置人：<账号>
- 配置时间：YYYY-MM-DD HH:MM CST

安全检查：
- workflow log 敏感信息扫描：未发现完整 DSN、账号、密码、token
- artifact 敏感信息扫描：未发现完整 DSN、账号、密码、token

改动文件：
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/README.md
- [如补 workflow/README，列出路径]

风险/说明：
- [如无，写“无”]
```

【禁止事项】
- 禁止用本地 `.pytest-postgresql.xml` 替代 hosted runner artifact。
- 禁止只提供 workflow 成功截图，不提供 JUnit `tests=4/skipped=0` 摘要。
- 禁止未配置 required check 却回报完成。
- 禁止没有管理员权限时声称已完成 branch protection。
- 禁止连接生产、预发、开发共享库或 ERPNext 真实业务库。
- 禁止在日志、artifact、README 或回报中泄露完整 DSN、账号、密码、token。
- 禁止修改外发结算业务逻辑。
- 禁止进入 TASK-006 代码实现。
- 禁止创建加工厂对账单主表、Purchase Invoice、Payment Entry 或 GL。
- 禁止调用 ERPNext 写接口。

【前置依赖】
TASK-002H7 审计意见书第 58 份有条件通过。

【后置门禁】
TASK-002H7A 通过审计后，允许进入 TASK-006 加工厂对账单模块开发。

【预计工时】
0.25-0.5 天

════════════════════════════════════════════════════════════════════════════
