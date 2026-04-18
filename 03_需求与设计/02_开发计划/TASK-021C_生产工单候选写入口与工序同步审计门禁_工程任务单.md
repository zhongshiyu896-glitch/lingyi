# TASK-021C 生产工单候选写入口与工序同步审计门禁 工程任务单

## 1. 基本信息

- 任务编号：TASK-021C
- 任务名称：生产工单候选写入口与工序同步审计门禁
- 角色：架构师
- 优先级：P1
- 状态：审计通过（审计意见书第 234 份）
- 前置依赖：TASK-021B 审计通过（审计意见书第 232 份）

## 2. 任务目标

基于 `TASK-021A` 已冻结的生产管理边界，以及 `TASK-021B` 已通过的“本地草稿 + 只读工单 / 工序投影”基线，输出第二张生产管理实现子任务，范围限定为“生产工单候选写入口 + 工序同步审计门禁”收口：

1. 收口 `create-work-order` 候选写入口的权限、幂等、审计和本地 outbox 语义。
2. 收口 `sync-job-cards` 同步入口的权限、资源映射、审计和本地只读投影更新语义。
3. 保持普通前端路径对真实 ERPNext 写链路默认冻结，不允许绕过 outbox / worker / adapter 边界。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-021A` 已正式通过，允许进入生产管理实现任务拆分。
2. `TASK-021B` 已于审计意见书第 232 份通过，生产管理实现链路可继续推进到 `TASK-021C`。
3. 审计意见书第 234 份已确认本任务单边界通过；当前仅完成任务单审计闭环，不构成对 B 的实现放行，`build_release_allowed=no` 仍保持不变。

## 2.2 已确认的现状基础

当前仓库中与 `TASK-021C` 直接相关的生产管理入口和基础代码已存在：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`

已核实的真实入口与现状：

1. 路由已存在 `POST /api/production/plans/{plan_id}/create-work-order`，当前走 `create_work_order_outbox` 本地 outbox 创建语义。
2. 路由已存在 `POST /api/production/work-orders/{work_order}/sync-job-cards`，当前走 `sync_job_cards` 本地投影同步语义。
3. 路由已存在 `/api/production/internal/work-order-sync/run-once`，且要求 `is_internal_worker_principal(current_user)`，属于内部 worker 入口，不应暴露给普通前端路径。
4. 前端 API 已存在 `createProductionWorkOrder` 和 `syncProductionJobCards`，但当前主线仍不得把它们解释为可直接放行真实生产写入。

因此本任务的核心是：

1. 按 `TASK-021A` 和 `TASK-021B` 把现有候选写入口收口到“受控入口 + 本地 outbox + 审计门禁”边界。
2. 保持 `sync-job-cards` 仅作为本地工序投影同步，不扩展为 Job Card 完工回写或 ERPNext 真实写入。
3. 保持普通前端路径对 worker、adapter、真实提交链路完全冻结。
4. 不触碰 ERPNext 真实写执行文件、Outbox 状态机公共语义和平台发布语义。

## 2.3 设计依据

1. `TASK-021A` 已明确：`Work Order` 草稿创建必须走 `TASK-008 Adapter + TASK-009 Outbox`，当前默认冻结。
2. `TASK-021A` 已明确：`Job Card` 完成数量同步必须 `after-commit + Outbox`，当前默认冻结真实写回。
3. `TASK-021A` 已明确：生产管理实现任务必须“单独设计、单独审计、单独放行”。
4. `TASK-021B` 已明确：`create-work-order`、`sync-job-cards` 在普通前端路径上仍为候选写入口，不得直接放开真实执行。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许修改以下后端文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
2. 允许修改以下前端文件：
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
   - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
3. 允许补充与生产工单候选写入口、工序同步门禁、权限审计相关的最小测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_job_card_sync.py`
4. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py` 的真实执行语义。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py`、`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py` 的公共 outbox 状态机语义。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_production_adapter.py`、`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py` 的真实外部调用语义。
4. 禁止修改 `06_前端/lingyi-pc/src/router/**`、`.github/**`、`02_源码/**`。
5. 禁止新增 ERPNext / Frappe `/api/resource` 直连。
6. 禁止在普通前端请求路径中直接调用 worker run-once、直接 create/submit Work Order、直接写回 Job Card completed_qty。
7. 禁止创建移动端/小程序独立工程、生产管理独立仓库、并行新模块。
8. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。

## 5. 必须输出

1. `create-work-order` 入口必须继续受 `PRODUCTION_WORK_ORDER_CREATE` 权限和资源范围约束；未授权路径只能隐藏、禁用或返回受控拒绝，不得产生真实 side effect。
2. `create-work-order` 请求路径只能形成或复用本地 outbox / 状态记录，返回 `outbox_id`、`event_key`、`sync_status` 等受控结果，不得在普通请求路径中直接驱动 worker 执行或直接调用 ERPNext 创建 / 提交。
3. `sync-job-cards` 入口必须继续受 `PRODUCTION_JOB_CARD_SYNC` 权限和本地 Work Order 映射约束；只能同步本地工序投影，不得扩展为 Job Card 完成数量回写。
4. 内部 worker 入口 `/internal/work-order-sync/run-once` 必须继续保持内部主体限制，不得通过普通前端路径暴露。
5. 审计日志、权限校验、统一错误包络、fail-closed、敏感信息脱敏不得被破坏。

## 6. 验收标准

1. 任务实现候选范围不包含 worker、outbox 公共状态机、adapter 真实写执行文件、`.github/**`、`02_源码/**`。
2. `create-work-order` 入口的语义被严格限定为“候选写入口 / 本地 outbox enqueue-or-reuse”，而不是普通前端直接真实写 ERPNext。
3. `sync-job-cards` 入口的语义被严格限定为“本地工序投影同步”，而不是 Job Card 完工回写。
4. 普通前端路径不存在对 `/internal/work-order-sync/run-once` 的直接调用，不存在绕过权限的真实写入口。
5. 不存在 ERPNext / Frappe `/api/resource` 直连，不存在敏感凭据本地持久化或日志泄露。
6. C 对本任务单出具正式复核结论前，不得放行 B。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "create_work_order_outbox|sync_job_cards|PRODUCTION_WORK_ORDER_CREATE|PRODUCTION_JOB_CARD_SYNC|run_work_order_sync_once|is_internal_worker_principal" \
  '07_后端/lingyi_service/app/routers/production.py' \
  '07_后端/lingyi_service/app/services/production_service.py' \
  '07_后端/lingyi_service/app/core/permissions.py'
rg -n "createProductionWorkOrder|syncProductionJobCards|create-work-order|sync-job-cards" \
  '06_前端/lingyi-pc/src/api/production.ts' \
  '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue'
rg -n "(/api/resource|run-once|submit_work_order|create_work_order\(|completed_qty.*writeback)" \
  '06_前端/lingyi-pc/src/api/production.ts' \
  '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue' \
  '07_后端/lingyi_service/app/routers/production.py' || true
pytest -q \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_job_card_sync.py'
npm --prefix '06_前端/lingyi-pc' run typecheck
git diff --name-only -- \
  '07_后端/lingyi_service/app/routers/production.py' \
  '07_后端/lingyi_service/app/services/production_service.py' \
  '07_后端/lingyi_service/app/schemas/production.py' \
  '06_前端/lingyi-pc/src/api/production.ts' \
  '06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue' \
  '07_后端/lingyi_service/app/services/production_work_order_worker.py' \
  '07_后端/lingyi_service/app/services/production_work_order_outbox_service.py' \
  '07_后端/lingyi_service/app/services/outbox_state_machine.py' \
  '07_后端/lingyi_service/app/services/erpnext_production_adapter.py' \
  '.github' '02_源码'
```

## 8. 完成回报

```text
TASK-021C 执行完成。
结论：审计通过（审计意见书第 234 份）
是否仍限定为候选写入口 + 本地工序投影同步门禁：是 / 否
是否直接调用 worker run-once：否
是否普通前端路径直接写 ERPNext Work Order / Job Card：否
是否修改 worker/outbox_state_machine/adapter 真实执行文件：否
是否修改 .github / 02_源码：否
是否 push/remote/PR：否
```
