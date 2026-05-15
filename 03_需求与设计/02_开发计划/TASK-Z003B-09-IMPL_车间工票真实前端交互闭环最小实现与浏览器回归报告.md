# TASK-Z003B-09-IMPL 车间工票真实前端交互闭环最小实现与浏览器回归报告

## 1. 任务与范围
- TASK_ID: `TASK-Z003B-09-IMPL`
- 角色: `B Engineer`
- source_head: `4060768989ae08ee5e071c6d7b90e838dcac072c`
- route_scope:
  - `/workshop/tickets`
  - `/workshop/tickets/register`
  - `/workshop/tickets/batch`
- 本轮仅在 allowlist 7 文件内实现，未触碰只读上下文文件、tests、models、`app/core/request_id.py`、ERPNext adapter、worker、dist。

## 2. 代码改动
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`

## 3. 实现结果
- register / reversal / batch 三链路已形成真实前端闭环：
  - 输入/编辑/保存/取消
  - API 对接
  - 列表与 job-card summary 回读
  - 状态联动（summary 中 sync/outbox 状态可见）
- scenario_tag 口径统一到 `Z003-WORKSHOP-TICKET-{YYYYMMDD}-{NNN}`。
- request_id 生成与校验满足 `^[A-Za-z0-9_.-]{1,64}$`。
- register/reversal/batch 三条写接口均已加 carrier 一致性校验。
- non-local-dev gate 返回 409，并保持 no DB write。

## 4. 写入边界与计数
- allowed write endpoints:
  - `POST /api/workshop/tickets/register`
  - `POST /api/workshop/tickets/reversal`
  - `POST /api/workshop/tickets/batch`
- approved_write_request_count: `3`
- unexpected_write_request_count: `0`
- forbidden_sync_worker_request_count: `0`
- erpnext_write_count: `0`
- worker_sync_internal_job_request_count: `0`
- production_write_count: `0`
- upload_download_export_print_request_count: `0`

## 5. Fail-Closed 与 no DB write
- 下列失败门禁均为 `409`，且 `db_write_on_failed_gate_count=0`：
  - `missing_request_id`
  - `invalid_request_id_pattern`
  - `mismatched_request_id`
  - `missing_idempotency_key`
  - `mismatched_business_carrier`
  - `mismatched_ticket_key`（ticket_key 载体不一致）
  - `mismatched_operation`
  - `non_local_dev_gate`

## 6. 浏览器与回归证据
- browser JSON: `/tmp/task_z003b09_browser_result.json`
- regression API JSON: `/tmp/task_z003b09_regression_api.json`
- cleanup JSON: `/tmp/task_z003b09_cleanup.json`
- screenshots dir: `/tmp/task_z003b09_screenshots`
- screenshots_count: `4`
- 截图文件:
  - `01_workshop_tickets_list.png`
  - `02_register_and_reversal_result.png`
  - `03_batch_result.png`
  - `04_summary_readback.png`

## 7. rollback / zero_residual
- rollback_cleanup_executed: `true`
- zero_residual: `true`
- residual_counts_by_table（scenario-scoped）:
  - `ys_workshop_ticket`: 0
  - `ys_workshop_daily_wage`: 0
  - `ys_workshop_job_card_sync_outbox`: 0
  - `ys_workshop_job_card_sync_log`: 0
  - `ys_workshop_outbox_access_denial`: 0
  - `ly_operation_audit_log`: 0
  - `ly_security_audit_log`: 0

## 8. 交付物
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z003B-09-IMPL_车间工票真实前端交互闭环最小实现与浏览器回归报告.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z003b_09_workshop_ticket_frontend_interaction_write_closure_evidence.json`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`
- `/tmp/task_z003b09_browser_result.json`
- `/tmp/task_z003b09_regression_api.json`
- `/tmp/task_z003b09_cleanup.json`
- `/tmp/task_z003b09_screenshots/`
