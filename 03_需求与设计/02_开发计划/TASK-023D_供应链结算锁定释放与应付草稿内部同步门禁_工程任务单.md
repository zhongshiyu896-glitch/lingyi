# TASK-023D 供应链结算锁定释放与应付草稿内部同步门禁 工程任务单

## 1. 基本信息

- 任务编号：TASK-023D
- 任务名称：供应链结算锁定释放与应付草稿内部同步门禁
- 角色：架构师
- 优先级：P1
- 状态：审计通过（审计意见书第 243 份）
- 前置依赖：TASK-023A 审计通过（审计意见书第 215 份）；TASK-023B 任务单复核通过（审计意见书第 240 份）；TASK-023C 任务单复核通过（审计意见书第 241 份）

## 2. 任务目标

基于 `TASK-023A` 已冻结的供应链协同边界，以及 `TASK-023B`、`TASK-023C` 已通过的只读台账与对账单读侧任务单，输出供应链协同实现链第三张任务单，范围限定为“结算锁定 / 释放候选门禁 + 应付草稿 outbox / 内部 worker 同步门禁”收口：

1. 收口 `/api/subcontract/settlement-candidates`、`/settlement-preview`、`/settlement-locks`、`/settlement-locks/release` 的候选结算、锁定与释放边界，明确这些能力当前只允许保持受控门禁语义，不得被解释为真实外部系统写入已放行。
2. 收口 `POST /api/factory-statements/{statement_id}/payable-draft` 与 `POST /api/factory-statements/internal/payable-draft-sync/run-once` 的权限、主体、`dry_run`、状态迁移、审计和 Adapter/Outbox 边界，确保普通请求与内部 worker 的职责严格分离。
3. 收口 `FactoryStatementPayableOutboxService` 与 `FactoryStatementPayableWorker` 的 `claim_due / mark_succeeded / mark_failed / dead`、`event_key`、`idempotency_key`、租约与 ERPNext Purchase Invoice 草稿创建顺序，不得绕过 `TASK-008` / `TASK-009`。
4. 将当前普通前端仍保留的 `createFactoryStatementPayableDraft -> /api/factory-statements/{statement_id}/payable-draft` 直调纳入本任务最小闭合范围，只允许通过最小前端改动关闭该直调，不得借机重开读侧或新增其他普通前端写入口。
5. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-023A` 已于审计意见书第 215 份通过，允许进入供应链协同实现任务拆分。
2. `TASK-023B` 已于审计意见书第 240 份通过，外发台账、履约状态投影与普通前端去写化边界已完成正式任务单收口。
3. `TASK-023C` 已于审计意见书第 241 份通过，对账单列表 / 详情 / 打印 / 导出只读基线已完成正式任务单收口；但 `payable-draft` 普通前端直调残留不作为 `TASK-023C` 已闭合事实外推，需在 `TASK-023D` 中单独收口。
4. 当前 `build_release_allowed=no`，本任务仍需先交 C 复核边界、验收标准、允许 / 禁止范围；C 未 PASS 前不得进入 B 实现。
5. 即使 `TASK-023D` 任务单通过，也只表示供应链协同实现链任务单拆分完成；除非后续 Context Pack 明确 `build_release_allowed=yes`，否则仍不得放行 B。

## 2.2 已确认的现状基础

当前仓库中与 `TASK-023D` 直接相关的候选结算、应付草稿 outbox 与内部 worker 基础代码已存在，不得按“从零新建供应链结算平台或支付同步平台”口径重复立项：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable_worker.py`

已核实的当前真实现状：

1. `subcontract.py` 已存在 `GET /settlement-candidates`、`POST /settlement-preview`、`POST /settlement-locks`、`POST /settlement-locks/release`，当前通过 `subcontract_settlement` / `subcontract_settlement_line` 权限与资源范围做受控门禁。
2. `SubcontractSettlementService` 已存在 `unsettled / statement_locked / settled`、`lock / release`、幂等键、请求哈希、追加式操作记录与回滚语义。
3. `factory_statement.py` 已存在 `POST /{statement_id}/payable-draft` 与 `POST /internal/payable-draft-sync/run-once`，当前区分普通请求的候选 outbox 创建与内部 worker 的真实同步。
4. `FactoryStatementPayableOutboxService` 已存在 `find_active_by_statement`、`claim_due`、`mark_succeeded`、`mark_failed`、租约、重试和 dead 语义；`FactoryStatementPayableWorker` 已存在 `dry_run`、语句状态复核、ERPNext 发票草稿查重 / 创建与成功 / 失败日志写入。
5. `test_subcontract_settlement_export.py`、`test_subcontract_settlement_postgresql.py`、`test_factory_statement_payable_api.py`、`test_factory_statement_payable_worker.py` 已覆盖候选结算过滤、锁定 / 释放幂等、追加式操作记录、payable outbox 创建、内部 worker 权限、`dry_run`、成功 / 失败 / dead 等关键场景。
6. 普通前端当前未发现对 `/settlement-locks`、`/settlement-locks/release`、`/internal/payable-draft-sync/run-once` 的直调；但 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts` 与 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue` 仍保留 `createFactoryStatementPayableDraft -> /payable-draft` 直调。
7. `TASK-023D` 不重新打开列表 / 详情 / 打印 / 导出读侧范围，但会把上述 `payable-draft` 普通前端直调作为本任务必须闭合的最小前端残留处理，而不是把“前端已去写化”写成既成事实。

因此本任务的核心是：

1. 把供应链结算候选、锁定、释放固定为“受控候选门禁”，避免被误读成已开放真实结算写入。
2. 把应付草稿创建与内部 worker 同步固定为“普通前端不得再直调 `payable-draft`、普通请求只负责受控候选入口、内部 worker 才能真实调用 Adapter”的闭环边界。
3. 保持 `event_key`、`idempotency_key`、追加式操作记录、租约 / 重试 / dead 语义和统一审计不被破坏。
4. 不触碰外发台账读侧、对账单读侧、打印导出、ERPNext Adapter 真实外部调用语义、公共 outbox 状态机语义和平台发布语义。

## 2.3 设计依据

1. `TASK-023A` 已明确：所有 ERPNext 交互统一经 `TASK-008 Adapter`，所有写入候选统一经 `TASK-009 Outbox`，未放行能力保持冻结。
2. `TASK-023A` 已明确：普通前端禁止暴露 `diagnostic / worker / internal / run-once` 类入口，写入候选必须单独任务、单独审计、单独放行。
3. `TASK-023B` 已完成外发台账与履约状态读侧收口，不再承接结算锁定 / 释放与应付草稿同步范围。
4. `TASK-023C` 已完成对账单列表 / 详情 / 打印 / 导出只读基线与普通前端去写化，不再承接 `payable-draft / internal worker` 真正的候选执行链说明。
5. `Sprint3_主执行计划.md` 明确供应链协同实现子任务顺序为 `023B -> 023C -> 023D`。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许修改以下后端文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_worker.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py`
2. 允许为关闭普通前端 `payable-draft` 直调而做最小前端改动，但仅限以下文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`
3. 允许补充与候选结算锁定 / 释放、payable outbox 创建、内部 worker 权限、`dry_run`、success / failure / dead 闭环相关的最小测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable_api.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable_worker.py`
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py` 的真实外部调用语义。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py` 的公共状态机语义。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py`、`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py` 中与 `TASK-023B`、`TASK-023C` 读侧已收口范围无关的普通列表 / 详情 / 打印 / 导出语义。
4. 禁止修改 `06_前端/lingyi-pc/src/views/subcontract/**`、`06_前端/lingyi-pc/src/router/**`、`06_前端/lingyi-pc/src/utils/factoryStatementExport.ts`，以及 `06_前端/lingyi-pc/src/views/factory_statement/**` 中除 `FactoryStatementDetail.vue` 之外的文件；`FactoryStatementDetail.vue` 的允许变更仅限关闭普通前端 `payable-draft` 直调，不得扩展列表 / 详情 / 打印 / 导出读侧语义。
5. 禁止新增或保留普通前端对 `/api/subcontract/settlement-locks`、`/settlement-locks/release`、`/api/factory-statements/{id}/payable-draft`、`/api/factory-statements/internal/payable-draft-sync/run-once` 的放行或直调；当前已识别的 `payable-draft` 直调必须在本任务范围内闭合。
6. 禁止新增 ERPNext / Frappe `/api/resource` 直连。
7. 禁止新增供应商门户、物流服务商、采购协同中台真实外部接入。
8. 禁止修改 `.github/**`、`02_源码/**`、新增并行供应链独立仓库或独立前端工程。
9. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. `settlement-candidates` 与 `settlement-preview` 继续保持只读候选事实视角，不得触发 ERPNext / 财务 / 应付真实写入。
2. `settlement-locks` 与 `settlement-locks/release` 必须继续保持基于 `idempotency_key`、请求哈希和追加式操作记录的受控门禁语义，只允许 `unsettled <-> statement_locked` 的受控状态迁移；已 settled 行不得被错误释放。
3. `POST /api/factory-statements/{statement_id}/payable-draft` 只允许在 `confirmed` 对账单上创建 payable outbox，不得直接创建 ERPNext Purchase Invoice，不得跳过 active outbox 冲突校验。
4. `/api/factory-statements/internal/payable-draft-sync/run-once` 必须继续同时受内部 worker 动作权限与服务账号主体约束；`dry_run=true` 不得调用 ERPNext、不得修改 outbox 状态。
5. `FactoryStatementPayableOutboxService` 的 `claim_due / mark_succeeded / mark_failed / dead`、租约、重试和 `event_key` 语义必须保持受控，不得旁路写状态。
6. `FactoryStatementPayableWorker` 只能在内部 worker 路径中通过 Adapter 查重 / 创建 ERPNext Purchase Invoice 草稿，并将 `statement_status` 从 `confirmed` 迁移到 `payable_draft_created`；普通请求不得承接该职责。
7. `06_前端/lingyi-pc/src/api/factory_statement.ts` 与 `FactoryStatementDetail.vue` 中当前已识别的 `createFactoryStatementPayableDraft -> /payable-draft` 直调必须被关闭或移除；普通前端不得继续保留 `生成应付草稿` 直调入口。
8. 普通前端读侧成果继续以 `TASK-023C` 为准，不得因本任务重新开放 `internal worker` 或任何候选结算写入口，也不得破坏列表 / 详情 / 打印 / 导出只读基线。
9. 统一审计、fail-closed、敏感信息脱敏和受控错误包络不得被破坏。

## 6. 验收标准

1. 任务实现候选范围仅限候选结算锁定 / 释放、payable outbox / 内部 worker 闭环门禁，以及关闭普通前端 `payable-draft` 直调所需的最小前端改动；不包含普通前端读侧扩展、打印导出改造、外部系统真实接入、`.github/**`、`02_源码/**`。
2. `settlement-candidates / settlement-preview / settlement-locks / settlement-locks/release` 的真实代码锚点、幂等和追加式操作语义存在且可验证。
3. `payable-draft` 与 `internal/payable-draft-sync/run-once` 的真实代码锚点、权限 / 主体 / `dry_run` / success / failure / dead 语义存在且可验证。
4. 不存在普通前端对 `/payable-draft`、`/internal/payable-draft-sync/run-once`、`/settlement-locks`、`/settlement-locks/release` 的直接调用；当前已识别的 `createFactoryStatementPayableDraft / FactoryStatementDetail.vue` 直调已被闭合。
5. 不存在 ERPNext / Frappe `/api/resource` 直连，不存在绕过 Adapter / Outbox 的真实写执行。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "settlement-candidates|settlement-preview|settlement-locks|statement_locked|unsettled|settled|operation_type|idempotency_key|request_hash|release_locks|lock_inspections" \
  '07_后端/lingyi_service/app/routers/subcontract.py' \
  '07_后端/lingyi_service/app/services/subcontract_settlement_service.py' \
  '07_后端/lingyi_service/app/schemas/subcontract.py' \
  '07_后端/lingyi_service/tests/test_subcontract_settlement_export.py' \
  '07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py'
rg -n "/payable-draft|/internal/payable-draft-sync/run-once|FactoryStatementPayableOutboxService|FactoryStatementPayableWorker|claim_due|mark_succeeded|mark_failed|dead|payable_draft_create|factory_statement:payable_draft_worker|purchase_invoice_name|dry_run" \
  '07_后端/lingyi_service/app/routers/factory_statement.py' \
  '07_后端/lingyi_service/app/services/factory_statement_service.py' \
  '07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py' \
  '07_后端/lingyi_service/app/services/factory_statement_payable_worker.py' \
  '07_后端/lingyi_service/app/schemas/factory_statement.py' \
  '07_后端/lingyi_service/tests/test_factory_statement_payable_api.py' \
  '07_后端/lingyi_service/tests/test_factory_statement_payable_worker.py'
! rg -n "createFactoryStatementPayableDraft|/payable-draft" \
  '06_前端/lingyi-pc/src/api/factory_statement.ts' \
  '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue'
! rg -n "/internal/payable-draft-sync/run-once|/settlement-locks|/settlement-locks/release" \
  '06_前端/lingyi-pc/src'
pytest -q \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_export.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable_api.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable_worker.py'
git diff --name-only -- \
  '07_后端/lingyi_service/app/routers/subcontract.py' \
  '07_后端/lingyi_service/app/services/subcontract_settlement_service.py' \
  '07_后端/lingyi_service/app/schemas/subcontract.py' \
  '07_后端/lingyi_service/app/routers/factory_statement.py' \
  '07_后端/lingyi_service/app/services/factory_statement_service.py' \
  '07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py' \
  '07_后端/lingyi_service/app/services/factory_statement_payable_worker.py' \
  '07_后端/lingyi_service/app/schemas/factory_statement.py' \
  '07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py' \
  '07_后端/lingyi_service/app/services/outbox_state_machine.py' \
  '06_前端/lingyi-pc/src/api/factory_statement.ts' \
  '06_前端/lingyi-pc/src/views/subcontract' \
  '06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue' \
  '06_前端/lingyi-pc/src/router' \
  '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-023D 执行完成。
结论：待审计
是否仍限定为结算锁定释放与应付草稿内部同步门禁：是 / 否
是否把 settlement-candidates / preview 保持为只读候选事实：是 / 否
是否关闭普通前端 createFactoryStatementPayableDraft 直调：是 / 否
是否放开 settlement-locks / release 给普通前端：否
是否把 payable-draft 直接升级为 ERPNext 发票真实写入：否
是否放开 internal/payable-draft-sync/run-once 给普通前端或非服务账号：否
是否修改 ERPNext Purchase Invoice Adapter / outbox_state_machine / 普通前端读侧 / .github / 02_源码：否
是否 push/remote/PR：否
```
