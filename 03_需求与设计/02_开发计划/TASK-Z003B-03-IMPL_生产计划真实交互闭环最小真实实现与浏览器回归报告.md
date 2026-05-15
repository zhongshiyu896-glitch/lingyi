# TASK-Z003B-03-IMPL 生产计划真实交互闭环最小真实实现与浏览器回归报告

## 1. 任务信息
- Task ID: `TASK-Z003B-03-IMPL`
- 主线: `TASK-Z003A-LOCAL-FRONTEND-INTERACTION-MAINLINE`
- 执行角色: `B Engineer`
- 执行时间: `2026-05-15`
- 远端生命周期: `PARKED`（未执行 `push / PR / tag / release / cleanup`）

## 2. 实现范围与改动文件
本轮仅在 allowlist 内完成实现，实际改动产品文件如下：
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/production.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/production/ProductionPlanDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py`

allowlist 内未改文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py`

## 3. 闭环实现结果
- 路由闭环: `/production/plans` 与 `/production/plans/detail` 可打开并完成交互。
- 写入闭环:
  - `POST /api/production/plans`
  - `POST /api/production/plans/{plan_id}/material-check`
  - `POST /api/production/plans/{plan_id}/create-work-order`
- 读回闭环:
  - `GET /api/production/plans`
  - `GET /api/production/plans/{plan_id}`
- 前端交互覆盖:
  - 创建表单输入、保存、取消/重置、反馈提示
  - 详情页物料检查与创建工单入口执行、状态回读
- create-work-order 走 local outbox 路径，未触发 ERPNext/worker/sync-job-cards。

## 4. 门禁与 fail-closed
- `request_id` 白名单: `^[A-Za-z0-9_.-]{1,64}$`。
- `scenario_tag` 前缀: `Z003-PROD-PLAN-{YYYYMMDD}-{NNN}`。
- carrier 规则按 create/material_check/create_work_order 分 operation 校验。
- fail-closed 用例均为 `409` 且无 DB 写入增量：
  - `missing_request_id`
  - `invalid_request_id_pattern`
  - `mismatched_request_id`
  - `missing_idempotency_key`
  - `mismatched_business_carrier`
  - `mismatched_plan_id`
  - `mismatched_operation`
  - `non_local_dev_gate`
- `db_write_on_failed_gate_count = 0`

## 5. 浏览器与 API 证据
- API 回归证据: `/tmp/task_z003b03_regression_api.json`
- 浏览器证据: `/tmp/task_z003b03_browser_result.json`
- 截图目录: `/tmp/task_z003b03_screenshots/`
- 截图数量: `3`
- 关键计数:
  - `approved_write_request_count = 3`
  - `unexpected_write_request_count = 0`
  - `forbidden_sync_job_cards_request_count = 0`
  - `erpnext_write_count = 0`
  - `worker_sync_internal_job_request_count = 0`
  - `production_write_count = 0`
  - `upload_download_export_print_request_count = 0`
  - `unexplained_console_errors_total = 0`
  - `unexplained_network_4xx_5xx_total = 0`

## 6. 回滚与 zero residual
- cleanup 证据: `/tmp/task_z003b03_cleanup.json`
- rollback 执行: `true`
- zero residual: `true`
- residual（8 表）均为 `0`:
  - `ly_production_work_order_outbox`
  - `ly_production_job_card_link`
  - `ly_production_work_order_link`
  - `ly_production_status_log`
  - `ly_production_plan_material`
  - `ly_production_plan`
  - `ly_operation_audit_log`
  - `ly_security_audit_log`

## 7. 验证结果
- `python3 -m py_compile app/routers/production.py app/schemas/production.py app/services/production_service.py app/services/production_work_order_outbox_service.py`：PASS
- `npm run precheck:dev-runtime`：PASS
- `npm run typecheck`：PASS
- `npm run verify`：PASS
- `python3 -m json.tool`（evidence/browser/regression/cleanup）：PASS
- `git diff --cached --name-only`：EMPTY
- `git diff --cached --check`：PASS
- `git diff --check`：PASS

## 8. 禁止项核对
本轮未执行以下动作：
- allowlist 外代码改动
- readonly context 文件改动
- `tests/**` 改动
- `app/core/request_id.py` 与 `models/**` 改动
- ERPNext/worker/sync-job-cards/production 写入
- `import / export / download / upload / print`
- `git add / commit / push`
- `PR / merge / close / tag / release / cleanup`
- `reset / restore / clean / delete`
- `rollback / revert / force push`
- 释放 parked blockers
