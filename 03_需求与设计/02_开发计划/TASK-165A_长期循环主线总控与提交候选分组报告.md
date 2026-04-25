# TASK-165A 长期循环主线总控与提交候选分组报告

## CURRENT_CONTROL_PLANE

- 来源控制面（只读核对）：
  - `/Users/hh/Documents/Playground 2/LOOP_STATE.md`
  - `/Users/hh/Documents/Playground 2/TASK_BOARD.md`
  - `/Users/hh/Documents/Playground 2/HANDOVER_STATUS.md`
  - `/Users/hh/Desktop/领意服装管理系统/00_交接与日志/HANDOVER_STATUS.md`
- 当前一致状态：
  - `state=READY_FOR_BUILD`
  - `active_role=B Engineer`
  - `active_task_id=TASK-165A`
  - `dispatch_b_allowed=true`
  - `dispatch_c_allowed=false`
- 关键约束：
  - `TASK-164I` 已闭环并确认 `NO_REMAINING_UNOWNED_BUSINESS_DIFF_CLOSE_164_SERIES`，不得回放。
  - parked blockers 保持：
    - `TASK-152A` = `BLOCK_FOR_USER_ADMIN_APPROVAL_REL004_REL005`
    - `TASK-090I` = `EVIDENCE_CEILING_BLOCKED`
    - `TASK-110B` = `NO_LEGAL_TASK_110B`

## OVERALL_PROGRESS_SUMMARY

- 总体主线进度（只读汇总）：
  - `TASK-157A~163A`：CCC 自动接力治理链已完成并经审计闭环（执行日志、轮转、最近事件查询、阶段门禁、结构化审计结果、嵌套回声抑制、attribution、运行态激活）。
  - `TASK-164A~164I`：Lingyi dirty worktree 归口链已完成并在 164I 形成总账闭环。
- 当前仓库状态：
  - tracked diff 仍为脏工作区，不等于“新增未归口任务”。
  - untracked 面很大，需按任务/审计文档与业务代码分层处理，禁止一键纳入。
- 本报告定位：
  - 建立长期循环主线控制账与候选分组，不写业务代码，不触发提交动作。

## CLOSED_CHAINS

- 已关闭链路（按 A/C 日志与 164I 总账）：
  - `CCC治理链`：`TASK-157A~163A`
  - `dirty diff归口链`：`TASK-164A~164I`
  - `164I` 审计结论：`NO_REMAINING_UNOWNED_BUSINESS_DIFF_CLOSE_164_SERIES`
- 已归口模块（164B~164H）：
  - 开发配置：`.gitignore`、`vite.config.ts`
  - 前端 contract/request：`frontend-contract-engine.mjs`、`test-frontend-contract-engine.mjs`、`src/api/request.ts`
  - factory statement：API + 列表页 + 详情页
  - sales inventory：API + 销售订单列表页 + 库存流水页
  - warehouse：前后端白名单六文件
  - production：前后端与测试白名单七文件（经 164G + FIX1 + 164H 收口）
  - app shell / router / HomePage / quality blocker：由 `TASK-164H FIX1` 闭环

## PARKED_BLOCKERS

- 保持 parked（本任务不释放）：
  - `TASK-152A`：管理员审批/REL-004-005链路阻塞
  - `TASK-090I`：证据上限阻塞
  - `TASK-110B`：无合法放行任务
- 规则：
  - 仅在新审批事实或新正式任务单出现时由 A 重新判定，不因循环噪声自动释放。

## DIRTY_WORKTREE_LEDGER

- 当前只读账本（本轮命令）：
  - `git status --short --branch`：分支 `codex/sprint4-seal`，tracked dirty 持续存在。
  - `git diff --name-only | wc -l`：`41`
  - `git ls-files --others --exclude-standard | wc -l`：`80713`
  - `git diff --stat`：`41 files changed, 3605 insertions(+), 495 deletions(-)`
- 与 `TASK-164A baseline(40)` 对照口径：
  - 维持“新增 tracked 主要来自 `src/api/quality.ts`（164H FIX1）”的闭环判断；
  - 当前控制目标是避免把同一批已归口 diff 反复当作新任务，而不是清空脏工作区。
- 与 TASK-164 相关 untracked（只读计数）：
  - `TASK-164*` + `HomePage.vue`：`32`（开发计划 21、审计记录 10、HomePage 1）

## LONG_LOOP_PROTOCOL

- 循环主流程（A/B/C）：
  1. A 从控制面和新事实判断合法主线，派发单一 `TASK_ID`。
  2. B 仅按白名单执行并回交证据，不越权改控面。
  3. C 仅审计 B 回交，输出结构化结论。
  4. A 根据结构化结论与控制面继续派发或收口。
- 审计输出门禁：
  - C 必须使用 `AUDIT_RESULT: PASS/FIX/BLOCK` 结构化输出。
  - 禁止裸 `PASS` 作为关闭信号。
- 固定约束：
  - 只允许单任务推进；
  - 同一问题重复出现按协议进入 suppress/blocked，不得无限回放。

## NOISE_SUPPRESSION_RULES

- 静默停止（不入新循环）：
  - 重复 `PASS` 回声包、重复 `IDLE/A/NONE`、过期 relay wrapper 包、空包、已关闭 `TASK_ID` 回声、无文件变化且无新验证且无 blocker 变化。
- 可继续推进（必须有新事实）：
  - 新用户正式方向；
  - 新 `TASK_ID` 正式任务单；
  - 新审批结果；
  - 新 diff 或新失败验证；
  - blocker 状态变化。

## NEXT_FACT_TRIGGERS

- 允许 A 重新开队列的触发条件：
  - `TRIGGER-1`：用户给出新的正式主线任务单。
  - `TRIGGER-2`：控制面出现新的合法 `READY_FOR_BUILD` 任务。
  - `TRIGGER-3`：已归口链路出现新的验证失败/回归失败。
  - `TRIGGER-4`：`TASK-152A/090I/110B` 任一审批或证据状态改变。
  - `TRIGGER-5`：dirty ledger 出现非 baseline 的新增 business diff 并可归口。

## COMMIT_CANDIDATE_GROUPS

- 说明：仅分组，不 stage，不 commit。

### G1 控制/文档流
- tracked：
  - `00_交接与日志/HANDOVER_STATUS.md`
  - `03_需求与设计/01_架构设计/*.md`（含任务设计文档与架构师会话日志）
  - `03_需求与设计/02_开发计划/*.md`（含工程任务单与工程师会话日志）
  - `03_需求与设计/05_审计记录/审计官会话日志.md`
- untracked（文档类）：
  - `03_需求与设计/02_开发计划/TASK-157A~TASK-165A` 相关任务单/报告
  - `03_需求与设计/05_审计记录/TASK-157A~TASK-164I` 审计任务单

### G2 CCC工具链
- 代码归口来源在外部目录：`/Users/hh/Desktop/ccc/`（不在本仓 tracked diff 内）。
- 本仓仅保留 CCC 任务单/审计单文档证据，不直接纳入业务代码提交组。

### G3 开发配置
- `.gitignore`
- `06_前端/lingyi-pc/vite.config.ts`

### G4 前端 contract/request
- `06_前端/lingyi-pc/scripts/frontend-contract-engine.mjs`
- `06_前端/lingyi-pc/scripts/test-frontend-contract-engine.mjs`
- `06_前端/lingyi-pc/src/api/request.ts`

### G5 factory statement
- `06_前端/lingyi-pc/src/api/factory_statement.ts`
- `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
- `06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`

### G6 sales inventory
- `06_前端/lingyi-pc/src/api/sales_inventory.ts`
- `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
- `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue`

### G7 warehouse
- `06_前端/lingyi-pc/src/api/warehouse.ts`
- `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- `07_后端/lingyi_service/app/routers/warehouse.py`
- `07_后端/lingyi_service/app/schemas/warehouse.py`
- `07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`
- `07_后端/lingyi_service/app/services/warehouse_service.py`

### G8 production
- `06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
- `06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
- `07_后端/lingyi_service/app/core/error_codes.py`
- `07_后端/lingyi_service/app/routers/production.py`
- `07_后端/lingyi_service/app/services/production_service.py`
- `07_后端/lingyi_service/tests/test_production_plan.py`

### G9 router/HomePage/quality
- tracked：
  - `06_前端/lingyi-pc/src/router/index.ts`
  - `06_前端/lingyi-pc/src/api/quality.ts`
- untracked：
  - `06_前端/lingyi-pc/src/views/HomePage.vue`

### G10 后端白名单（跨业务汇总）
- `07_后端/lingyi_service/app/core/error_codes.py`
- `07_后端/lingyi_service/app/routers/production.py`
- `07_后端/lingyi_service/app/routers/warehouse.py`
- `07_后端/lingyi_service/app/schemas/warehouse.py`
- `07_后端/lingyi_service/app/services/production_service.py`
- `07_后端/lingyi_service/app/services/warehouse_service.py`
- `07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`
- `07_后端/lingyi_service/tests/test_production_plan.py`

### G11 审计/任务报告
- `03_需求与设计/02_开发计划/TASK-16xx*`（任务单、报告）
- `03_需求与设计/05_审计记录/TASK-16xx*`（审计任务单）
- 默认仅作为证据文档组，不自动并入业务代码组。

## NEXT_QUEUE_CANDIDATES

- P0（推荐）：
  - `TASK165B_COMMIT_CANDIDATE_GROUP_AUDIT`（docs-only）
  - 目标：由 A 发起“候选分组审计任务”，逐组确认可提交边界、排除未授权路径、固化 staging 白名单模板。
- P1（次选）：
  - `TASK165B_RELEASE_PRECHECK_DOCS_ONLY`
  - 目标：只做发布前文档门禁核查，不做 stage/commit/push。
- P2（条件触发）：
  - 新业务任务，仅当出现新事实（新 `TASK_ID`、新审批、新失败验证、新增未归口 diff）。
- P3（外部审批触发）：
  - `TASK-152A` 管理员审批链；
  - `TASK-090I` 强证据补齐；
  - `TASK-110B` 合法放行条件出现前保持 parked。

## DEFAULT_NEXT_ACTION

- `ALLOW_A_TO_DISPATCH_TASK165B_COMMIT_CANDIDATE_GROUP_AUDIT`
- 理由：
  - 当前无新增未归口业务 diff；
  - 但仓库仍为大规模 dirty worktree，直接提交风险高；
  - 最稳妥下一步是先做“提交候选分组审计”，把可提交边界固定为可执行清单，再决定是否进入 stage/commit。

## VALIDATION

- 已执行命令与结果：
  - `git -C '/Users/hh/Desktop/领意服装管理系统' status --short --branch`：PASS（当前分支 `codex/sprint4-seal`，dirty 存在）
  - `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only | wc -l`：`41`
  - `git -C '/Users/hh/Desktop/领意服装管理系统' ls-files --others --exclude-standard | wc -l`：`80713`
  - `git -C '/Users/hh/Desktop/领意服装管理系统' diff --stat`：`41 files changed, 3605 insertions(+), 495 deletions(-)`
  - `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '03_需求与设计/02_开发计划/TASK-165A_长期循环主线总控与提交候选分组报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`：PASS（无输出）。

## RISK_NOTES

- 当前风险不在“是否有新业务改动”，而在“如何避免将同一批 dirty baseline 重复误判为新任务”。
- parked blockers 仍为硬门禁，不得因循环推进需求而越权释放。
- 当前结论不外推为：
  - 业务功能放行
  - stage/commit/push/PR 放行
  - REL-004/REL-005 放行
  - 生产联调或 ERPNext 生产写入放行
