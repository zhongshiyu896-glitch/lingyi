# TASK-021D 生产工单内部Worker运行与Outbox闭环门禁 工程任务单

## 1. 基本信息

- 任务编号：TASK-021D
- 任务名称：生产工单内部Worker运行与Outbox闭环门禁
- 角色：架构师
- 优先级：P1
- 状态：审计通过（审计意见书第 235 份）
- 前置依赖：TASK-021A 审计通过（审计意见书第 212 份）；TASK-021B 审计通过（审计意见书第 232 份）；TASK-021C 审计通过（审计意见书第 234 份）

## 2. 任务目标

基于 `TASK-021A` 已冻结的生产管理边界，以及 `TASK-021B`、`TASK-021C` 已通过的只读投影与候选写入口任务单，输出第三张生产管理实现子任务，范围限定为“内部 worker 运行 + outbox 闭环门禁”收口：

1. 收口 `/api/production/internal/work-order-sync/run-once` 内部 worker 入口的权限、主体、`dry_run`、批处理和审计边界。
2. 收口 `ProductionWorkOrderWorker` 对生产工单候选执行链路的调用顺序与 side effect 边界，确保真实执行只能发生在内部 worker 路径。
3. 收口 `ProductionWorkOrderOutboxService` 的 `claim_due / mark_succeeded / mark_failed`、租约、幂等和 `event_key` 闭环语义，不得绕过 `TASK-009` 约束。
4. 本任务只形成可审计工程任务边界；在 `build_release_allowed=no` 条件下，不直接放行 B 实现。

## 2.1 当前门禁状态

1. `TASK-021A` 已正式通过，允许进入生产管理实现链路拆分。
2. `TASK-021B` 已于审计意见书第 232 份通过，`TASK-021C` 已于审计意见书第 234 份通过，生产管理实现链路可继续推进到 `TASK-021D`。
3. 审计意见书第 235 份已确认本文档边界通过；当前仅完成任务单审计闭环，不构成对 B 的实现放行。
4. `build_release_allowed=no` 仍保持不变；除非后续 Context Pack 明确 `build_release_allowed=yes`，否则仍不得放行 B。

## 2.2 已确认的现状基础

当前仓库中与 `TASK-021D` 直接相关的内部 worker 和 outbox 基础代码已存在：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/auth.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_work_order_outbox.py`

已核实的真实入口与现状：

1. 路由已存在 `POST /api/production/internal/work-order-sync/run-once`，当前使用 `PRODUCTION_WORK_ORDER_WORKER` 并要求 `is_internal_worker_principal(current_user)`。
2. `ProductionWorkOrderWorker` 已存在 `dry_run`、`claim_due`、`mark_succeeded`、`mark_failed` 等主流程逻辑。
3. `ProductionWorkOrderOutboxService` 已存在 `build_event_key`、`idempotency_key`、`claim_due`、`mark_succeeded`、`mark_failed` 等闭环基础语义。
4. 测试已覆盖普通角色不能调用内部 worker、worker claim 提交顺序、重复 claim 防重、租约恢复等关键场景。

因此本任务的核心是：

1. 把已有内部 worker 路径收口到“仅内部主体 + 可审计 dry_run + outbox 闭环”边界。
2. 保持普通前端 / 普通业务请求路径对真实 ERPNext 创建 / 提交完全冻结。
3. 保持 outbox 执行闭环只能通过 `ProductionWorkOrderOutboxService` 暴露的受控语义，不得出现旁路状态写入。
4. 不触碰 ERPNext adapter 真实外部调用语义、公共 outbox 状态机语义和平台发布语义。

## 2.3 设计依据

1. `TASK-021A` 已明确：`Work Order` 草稿创建必须走 `TASK-008 Adapter + TASK-009 Outbox`，真实执行默认冻结。
2. `TASK-021A` 已明确：生产管理实现必须“单独设计、单独审计、单独放行”。
3. `TASK-021B` 已明确：普通前端路径当前只允许本地草稿与只读工单 / 工序投影，不得暴露真实执行链路。
4. `TASK-021C` 已明确：`create-work-order` 和 `sync-job-cards` 在普通请求路径上仍只是候选写入口 / 本地投影同步门禁，worker / outbox 真实执行文件不在其允许范围内。
5. `Sprint3_主执行计划.md` 明确生产管理实现子任务顺序为 `021B -> 021C -> 021D`。

## 3. 允许范围

> 以下为后续 B 实现候选范围；本轮 A 仅输出任务单，不修改实现。

1. 允许修改以下后端文件：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
2. 允许补充与内部 worker 权限、`dry_run`、claim / success / failure 闭环相关的最小测试：
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py`
   - `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_work_order_outbox.py`
3. 允许同步更新当前任务单与 C 复核指令。

## 4. 禁止范围

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py` 的普通业务请求路径语义。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/outbox_state_machine.py` 的公共状态机语义。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_production_adapter.py`、`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py` 的真实外部调用语义。
4. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/auth.py` 的全局认证主体识别规则。
5. 禁止修改 `06_前端/lingyi-pc/src/api/production.ts`、`06_前端/lingyi-pc/src/views/production/**`、`06_前端/lingyi-pc/src/router/**`、`.github/**`、`02_源码/**`。
6. 禁止新增普通前端对 `/internal/work-order-sync/run-once` 的直接调用。
7. 禁止新增 ERPNext / Frappe `/api/resource` 直连。
8. 禁止在普通请求路径中直接调用 ERPNext `create_work_order / submit_work_order` 或直接篡改 outbox 状态。
9. 禁止设置 `build_release_allowed=yes`、禁止放行 B、禁止 push / remote / PR / 生产发布。
10. 当前工作区继承 `TASK-021C` 已审计通过但尚未提交的历史基线脏改动共 6 个文件。其中 `production.py`、`schemas/production.py`、`test_production_plan.py` 虽位于 `TASK-021D` 的通用允许范围内，但本轮 `TASK-021D` 已完成的真实交付不再继续修改它们；这 6 个文件在 `TASK-021D` 当前审计轮次中必须全部保持以下 SHA-256 不变：
    - `production.py`: `2ad6b2e2f58934a1fe2e28e75a7822ce7c707b159018da8cae551d9059814074`
    - `schemas/production.py`: `585f4f80c980cfa9e8d3c3e828e3ec45c18ac1d4f0b3a960ce902422ce18bc0e`
    - `test_production_plan.py`: `419a4f281bf9fbbd61939615781ac68e1b47a6e14be6687146cef89cf76e22eb`
    - `production_service.py`: `000a510efe44958cebf2f48661aeb709ac35f9a5680a1a85cc1a174049e7a9cd`
    - `production.ts`: `671f245744c6c8ed0d13651380a6b6c4db1d36241bc71162cc38dfb9fb8daebc`
    - `ProductionPlanDetail.vue`: `53bd203cbbef29fd9d665311ed64319c8bfedc9dcc4ae2d522ef6aea16525f66`

## 5. 必须输出

1. `/internal/work-order-sync/run-once` 入口必须继续同时受 `PRODUCTION_WORK_ORDER_WORKER` 和 `is_internal_worker_principal(current_user)` 约束；未授权路径必须 fail-closed 并保留审计。
2. `dry_run=true` 只能返回受控预演结果，不得调用 ERPNext 创建 / 提交，不得修改 outbox 状态或租约字段。
3. 非 `dry_run` 路径只能通过 `ProductionWorkOrderOutboxService.claim_due(...)` 领取 due outbox，再由 worker 顺序完成真实执行和闭环，不得出现普通请求路径直接驱动执行。
4. `mark_succeeded / mark_failed`、`event_key`、`idempotency_key`、租约恢复和防重复 claim 语义必须保留，不得旁路写状态。
5. 普通前端路径仍只能停留在 `TASK-021C` 定义的候选写入口 / 本地投影同步语义，不得因为本任务而升级为真实写执行。
6. 审计日志、权限校验、统一错误包络、fail-closed 和敏感信息脱敏不得被破坏。

## 6. 验收标准

1. 任务实现候选范围仅限 `run-once` 路由、worker、生产工单 outbox service、相关 schema / permission 和最小测试。
2. `/internal/work-order-sync/run-once` 明确保持“内部主体专用”，不存在普通前端直调或普通角色绕过。
3. `dry_run=true` 明确无 outbox / ERPNext side effect；非 `dry_run` 也只能在内部 worker 路径中执行。
4. `claim_due`、租约恢复、防重复 claim、`mark_succeeded / mark_failed` 等闭环语义通过现有 worker / outbox service 受控完成，不得直接改写 row 状态。
5. 不存在 ERPNext / Frappe `/api/resource` 直连，不存在普通请求路径直接调用 `create_work_order / submit_work_order`。
6. C 对本任务单出具正式复核结论前，不得放行 B。
7. 继承自 `TASK-021C` 的 6 个历史基线脏文件 SHA-256 必须保持不变，不得把历史已审计改动误计入 `TASK-021D` 本轮范围。
8. `TASK-021D` 当前审计轮次的真实交付只允许新增命中 `production_work_order_worker.py`、`test_production_permissions.py`、`test_production_work_order_outbox.py` 与工程师会话日志；不得再把 `production.py`、`schemas/production.py`、`test_production_plan.py` 作为新增交付扩改。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
rg -n "PRODUCTION_WORK_ORDER_WORKER|is_internal_worker_principal|run_work_order_sync_once|ProductionWorkerRunOnceRequest|ProductionWorkerRunOnceData|dry_run" \
  '07_后端/lingyi_service/app/routers/production.py' \
  '07_后端/lingyi_service/app/core/permissions.py' \
  '07_后端/lingyi_service/app/core/auth.py' \
  '07_后端/lingyi_service/app/schemas/production.py'
rg -n "ProductionWorkOrderWorker|claim_due|mark_succeeded|mark_failed|dry_run|event_key|idempotency_key" \
  '07_后端/lingyi_service/app/services/production_work_order_worker.py' \
  '07_后端/lingyi_service/app/services/production_work_order_outbox_service.py'
rg -n "/internal/work-order-sync/run-once|create-work-order|sync-job-cards" \
  '06_前端/lingyi-pc/src' || true
pytest -q \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_work_order_outbox.py'
git diff --name-only -- \
  '07_后端/lingyi_service/app/services/production_work_order_worker.py' \
  '07_后端/lingyi_service/tests/test_production_permissions.py' \
  '07_后端/lingyi_service/tests/test_production_work_order_outbox.py'
git diff --name-only -- \
  '07_后端/lingyi_service/app/services/outbox_state_machine.py' \
  '07_后端/lingyi_service/app/services/erpnext_production_adapter.py' \
  '07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py' \
  '.github' '02_源码'
shasum -a 256 \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py' \
  '/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py' \
  '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts' \
  '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue'
```

## 8. 完成回报

```text
TASK-021D 执行完成。
结论：审计通过（审计意见书第 235 份）
是否仍限定为内部 worker 运行与 outbox 闭环门禁：是 / 否
是否普通前端路径直接调用 /internal/work-order-sync/run-once：否
是否 dry_run 产生 outbox/ERPNext side effect：否
是否普通请求路径直接写 ERPNext Work Order：否
是否修改 production_service/outbox_state_machine/adapter/core/auth 受禁文件：否
是否修改 .github / 02_源码：否
是否 push/remote/PR：否
```
