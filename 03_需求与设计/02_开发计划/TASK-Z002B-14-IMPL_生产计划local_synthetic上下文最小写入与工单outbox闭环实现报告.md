# TASK-Z002B-14-IMPL 实现报告

## 1. 任务结论

- `TASK_ID`: `TASK-Z002B-14-IMPL`
- `ROLE`: `B Engineer`
- `CODE_CHANGED`: `YES`
- 结果：在 local-dev 边界内完成最小闭环：
  - `POST /api/production/plans`（local synthetic 上下文创建计划）
  - `POST /api/production/plans/{plan_id}/create-work-order`（outbox-only）
- 未触发 ERPNext adapter 写入、worker/sync-job-cards、material-check、跨模块写入、上传下载导出打印。

## 2. 改动文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`

## 3. 实现说明

### 3.1 local synthetic 上下文（后端）

- 在 `ProductionService` 增加 local synthetic fallback，仅在以下 gate 成立时可用：
  - `APP_ENV=development`
  - `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- 新增 `scenario_tag` 一致性校验，载体：
  - `idempotency_key`
  - `sales_order`
  - `sales_order_item`
- 当 ERPNext 不可用或 Sales Order 不存在时，且本地 gate 与 scenario_tag 校验通过，构造 synthetic `sales_order/item/company` 供 `create_plan` 闭环；否则维持 fail-closed。

### 3.2 前端最小写入闭环

- `ProductionPlanDetail.vue`：
  - `create-work-order` 从 guarded 提示切换为真实 API 调用（仍限定 outbox-only）。
  - 增加 `request_id` 输入与校验（scenario carrier）。
  - 增加 `creatingWorkOrder` 加载与防重入控制。
  - 保留并显式展示 local synthetic 模式提示锚点。
- `production.ts`：
  - `createProductionPlan`、`createProductionWorkOrder` 支持可选 `X-Request-ID` header。

### 3.3 未放开路径

- 未修改 `production_work_order_worker.py`。
- 未修改 `erpnext_production_adapter.py`。
- 未触发：
  - `POST /api/production/plans/{plan_id}/material-check`
  - `POST /api/production/work-orders/{work_order}/sync-job-cards`
  - `POST /api/production/internal/work-order-sync/run-once`

## 4. 测试数据与清理

- `scenario_tag`：`Z002-PRODUCTION-PLAN-LOCALCTX-20260513-017`
- 载体：
  - `sales_order=SO-Z002-PRODUCTION-PLAN-LOCALCTX-20260513-017`
  - `sales_order_item=SOI-Z002-PRODUCTION-PLAN-LOCALCTX-20260513-017`
  - `idempotency_key(plan)=Z002-PRODUCTION-PLAN-LOCALCTX-20260513-017`
  - `idempotency_key(work_order)=Z002-PRODUCTION-PLAN-LOCALCTX-20260513-017-WO`
  - `request_id(plan)=Z002-PRODUCTION-PLAN-LOCALCTX-20260513-017-REQ-PLAN`
  - `request_id(work_order)=Z002-PRODUCTION-PLAN-LOCALCTX-20260513-017-REQ-WO`
- rollback 顺序按冻结包执行：
  1. `ly_production_work_order_outbox`
  2. `ly_production_work_order_link`
  3. `ly_production_job_card_link`
  4. `ly_production_plan_material`
  5. `ly_production_status_log`
  6. `ly_production_plan`
- `zero_residual=true`，表级残留均为 0（见证据 JSON）。

## 5. 浏览器与数据库证据

- 浏览器结果：
  - `/tmp/task_z002b14_browser_result.json`
- 截图目录：
  - `/tmp/task_z002b14_screenshots`
  - `screenshots_count=3`
- setup 证据：
  - `/tmp/task_z002b14_setup.json`
- cleanup/残留证据：
  - `/tmp/task_z002b14_cleanup.json`
- 主证据包：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002b_14_impl_production_local_context_outbox_evidence.json`

## 6. 验证结果

- `python3 -m py_compile app/routers/production.py app/schemas/production.py app/services/production_service.py app/services/production_work_order_outbox_service.py`：PASS
- `npm run precheck:dev-runtime`：PASS
- `npm run typecheck`：PASS
- `npm run verify`：PASS
- `python3 -m json.tool task_z002b_14_impl_production_local_context_outbox_evidence.json`：PASS
- `git diff --cached --name-only`：EMPTY
- `git diff --name-only -- 06_前端 07_后端`：仅本任务 allowlist 产品文件
- `git diff --check`：PASS

## 7. 禁止动作核对

- `worker/ERPNext adapter edits`: `NO`
- `test code edits`: `NO`
- `control-plane/A-log/C-audit edits`: `NO`
- `production writes`: `NO`
- `ERPNext writes`: `NO`
- `material-check/sync-job-cards/internal-worker`: `NO`
- `upload/download/export/print`: `NO`
- `git add/commit/push`: `NO`
- `PR/merge/tag/release/cleanup`: `NO`
- `parked blockers released`: `NO`
