# TASK-002H7 GitHub Actions 实跑与 Required Check 固化工程任务单

- 任务编号：TASK-002H7
- 模块：外发加工管理
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-13 16:46 CST
- 作者：技术架构师
- 审计来源：TASK-002H6 审计意见书第 57 份通过，剩余风险为尚未在真实 GitHub Actions hosted runner 上确认 JUnit artifact 为 `tests=4, skipped=0`，且 `Backend PostgreSQL Hard Gate` 尚未明确设为 required check
- 架构裁决：`Backend PostgreSQL Hard Gate` 必须完成真实 GitHub Actions hosted runner 实跑，并纳入主干分支 required check；否则 TASK-006 不得进入主干
- 前置依赖：TASK-002H6 已通过审计意见书第 57 份；继续遵守外发模块 V1.25、ADR-053
- 任务边界：只做 GitHub Actions 实跑确认、artifact 归档、分支保护 required check 配置和说明文档；不得修改结算业务逻辑、不得创建 TASK-006 对账单主表、不得调用 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H7
模块：GitHub Actions 实跑与 Required Check 固化
优先级：P1（主干保护门禁）
════════════════════════════════════════════════════════════════════════════

【任务目标】
在真实 GitHub Actions hosted runner 上运行 `Backend PostgreSQL Hard Gate`，确认 JUnit artifact 显示 `tests=4, skipped=0`，并把该 check 配置为主干分支 required check。

【模块概述】
TASK-002H6 已经把 PostgreSQL marker 非 skip 校验写成 CI hard gate，并通过本地审计。剩余风险在 GitHub 平台层：workflow 是否能在 hosted runner 上真实启动 PostgreSQL service、是否能上传 JUnit artifact、以及主干分支是否强制要求该 check 通过。本任务只做平台门禁确认和固化，防止后续 PR 绕过 PostgreSQL 并发语义验证。

【涉及文件】
可能修改：
- /Users/hh/Desktop/领意服装管理系统/.github/workflows/backend-postgresql.yml（仅限补 `workflow_dispatch`、artifact 上传、job summary、稳定 check 名称）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md（补 required check 配置说明）
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/CI门禁证据/README.md（如需记录证据索引，可新建）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
- 任意 TASK-006 业务实现文件

【必须确认的 GitHub Actions 事项】
1. workflow 名称必须稳定为 `Backend PostgreSQL Hard Gate`。
2. job/check 名称必须稳定，建议为 `subcontract-postgresql-gate`。
3. workflow 必须支持 `workflow_dispatch` 手动触发。
4. workflow 必须在 GitHub Actions hosted runner 上执行，不得只用本地模拟结果替代。
5. workflow 必须启动 PostgreSQL service。
6. workflow 必须使用一次性测试库，库名命中白名单，例如 `lingyi_test_ci`。
7. workflow 必须设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
8. workflow 必须设置 `POSTGRES_TEST_DSN`，且日志不得泄露完整 DSN、账号、密码。
9. workflow 必须执行 `scripts/run_postgresql_ci_gate.sh`。
10. workflow 必须上传 `.pytest-postgresql.xml` artifact。
11. artifact 中 PostgreSQL marker 结果必须为 `tests=4, skipped=0, failures=0, errors=0`。
12. GitHub branch protection 必须将 `Backend PostgreSQL Hard Gate / subcontract-postgresql-gate` 或 GitHub 实际显示的等效 check 设为 required check。
13. 如果没有仓库管理员权限配置 branch protection，必须回报“权限阻塞”，并提供 exact required check 名称、workflow run URL、artifact 结果和需要管理员点击的配置项。

【执行步骤】
1. 检查 `.github/workflows/backend-postgresql.yml` 是否包含：
   - `workflow_dispatch`
   - PostgreSQL service
   - `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`
   - `POSTGRES_TEST_DSN` 指向一次性测试库
   - artifact upload
   - 稳定 workflow/job 名称
2. 如果缺少以上项，只允许最小修改 workflow/README。
3. 推送或在当前分支触发 `workflow_dispatch`。
4. 等待 GitHub Actions hosted runner 完成。
5. 下载或查看 `.pytest-postgresql.xml` artifact。
6. 确认 JUnit 统计：`tests=4, skipped=0, failures=0, errors=0`。
7. 检查 workflow log，不得出现完整 DSN、账号、密码。
8. 配置 branch protection required check：
   - 目标分支：主干分支（如 `main` / `master`，按仓库实际为准）
   - required check：`Backend PostgreSQL Hard Gate / subcontract-postgresql-gate` 或 GitHub 实际显示名称
9. 如果仓库已启用 ruleset，必须在 ruleset 中加入同一 required check。
10. 回报 workflow run URL、artifact 名称、required check 名称和配置结果。

【验收标准】
□ GitHub Actions hosted runner 已实际执行 `Backend PostgreSQL Hard Gate`。  
□ workflow run URL 已提供。  
□ workflow run 成功。  
□ JUnit artifact 已上传。  
□ artifact 中 `tests=4`。  
□ artifact 中 `skipped=0`。  
□ artifact 中 `failures=0`。  
□ artifact 中 `errors=0`。  
□ workflow log 未泄露完整 DSN、账号、密码。  
□ PostgreSQL service 在 hosted runner 中启动成功。  
□ 测试库名命中白名单，例如 `lingyi_test_ci`。  
□ `Backend PostgreSQL Hard Gate` 已配置为主干分支 required check。  
□ 若无管理员权限，已提供权限阻塞说明、exact check 名称和管理员配置步骤。  
□ README 已记录 required check 名称和新增 PostgreSQL marker 用例时需要同步 expected-tests。  
□ 未修改结算业务逻辑。  
□ 未创建 TASK-006 对账单主表。  
□ 未调用 ERPNext 写接口。  

【建议命令】
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

# 本地先复核 workflow 入口仍可用
.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py

# 如使用 GitHub CLI，可触发 workflow_dispatch
cd /Users/hh/Desktop/领意服装管理系统
gh workflow run "Backend PostgreSQL Hard Gate"

gh run list --workflow "Backend PostgreSQL Hard Gate" --limit 5

# 下载 artifact 后，本地解析确认 tests/skipped
# 注意：不要输出完整 DSN
```

【回报格式】
工程师完成后按以下格式回报：

```text
TASK-002H7 GitHub Actions 实跑与 Required Check 固化完成。

GitHub Actions：
- workflow：Backend PostgreSQL Hard Gate
- job/check：subcontract-postgresql-gate
- run URL：<GitHub Actions run URL>
- runner：GitHub Actions hosted runner
- PostgreSQL 测试库：lingyi_test_ci（一次性测试库，命中白名单）

JUnit artifact：
- artifact 名称：<artifact name>
- tests：4
- skipped：0
- failures：0
- errors：0

Required check：
- 目标分支：main/master/<实际分支>
- required check 名称：Backend PostgreSQL Hard Gate / subcontract-postgresql-gate
- 配置状态：已配置 / 无管理员权限阻塞

验证结果：
- tests/test_ci_postgresql_gate.py：X passed
- GitHub Actions hard gate：4 passed, 0 skipped
- workflow log 敏感信息扫描：未发现完整 DSN、账号、密码

改动文件：
- [如无代码改动，写“无”]
- [如补 workflow/README，列出路径]

风险/说明：
- [如无，写“无”]
```

【禁止事项】
- 禁止用本地模拟结果替代 GitHub Actions hosted runner 结果。
- 禁止只看 workflow 成功，不检查 JUnit artifact 的 `tests=4, skipped=0`。
- 禁止把 check 配好但不设为 required。
- 禁止连接生产、预发、开发共享库或 ERPNext 真实业务库。
- 禁止在日志、artifact 或回报中泄露完整 DSN、账号、密码。
- 禁止修改外发结算业务逻辑。
- 禁止进入 TASK-006 代码实现。
- 禁止创建加工厂对账单主表、Purchase Invoice、Payment Entry 或 GL。
- 禁止调用 ERPNext 写接口。

【前置依赖】
TASK-002H6 审计意见书第 57 份通过。

【后置门禁】
TASK-002H7 通过审计后，允许进入 TASK-006 加工厂对账单模块开发。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
