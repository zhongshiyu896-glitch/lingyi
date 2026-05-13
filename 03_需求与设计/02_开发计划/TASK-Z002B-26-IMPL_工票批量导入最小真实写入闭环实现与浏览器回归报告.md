# TASK-Z002B-26-IMPL 工票批量导入最小真实写入闭环实现与浏览器回归报告

## 1. 任务结论

- 任务状态：`READY_FOR_REVIEW`
- 任务编号：`TASK-Z002B-26-IMPL`
- 角色：`B Engineer`
- 范围结论：仅修改 allowlist 内 5 个产品文件，未触碰 allowlist 外产品/后端/测试代码。
- 闭环结论：`POST /api/workshop/tickets/batch` 本地最小写入闭环成立；scenario_tag 与 request_id gate 生效；rollback 后 `zero_residual=true`。

## 2. 代码改动（allowlist 内）

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue`
2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue`
3. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/workshop.ts`
4. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
5. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`

## 3. 实现要点

### 3.1 前端批量页从 guarded 切换到 local allowlist 写入

- 提交按钮标记改为：
  - `data-write-guard="allowed:workshop-ticket-batch-local-only"`
  - `data-write-allowlist="workshop-ticket-batch"`
- `submitBatch` 改为真实调用 `POST /api/workshop/tickets/batch`，并回显：
  - `success_count`
  - `failed_count`
  - `failed_items`
- 成功后自动触发 `GET /api/workshop/tickets` 回读。

### 3.2 API 层补齐 `X-Request-ID` 透传

- `batchWorkshopTickets` 新增 `meta.requestId` 参数。
- 请求头携带 `X-Request-ID`，用于后端 scenario gate 校验。

### 3.3 后端 batch gate 与 local synthetic 写入边界

- 新增 batch gate（local-dev only）：
  - 必须 `APP_ENV=development`
  - 必须 `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- scenario_tag 前缀：`Z002-WORKSHOP-BATCH-{YYYYMMDD}-{NNN}`
- carrier 一致性强校验：
  - `payload.ticket_key`
  - `payload.source_ref`
  - `header.X-Request-ID/request_id`
- carrier 缺失或不一致时 fail-closed（`409 WORKSHOP_IDEMPOTENCY_CONFLICT`），且核心业务写表无增量。
- batch 行处理透传 `local_scenario_tag`，确保 local synthetic 资源解析与计薪路径可用，不依赖 ERPNext 写路径。

## 4. 回归证据摘要

- scenario_tag：`Z002-WORKSHOP-BATCH-20260513-026`
- 浏览器回归：
  - route_open=`true`
  - first_screen_visible=`true`
  - batch_json_parse_preview=`true`
  - batch_post_triggered=`true`
  - batch_post_status=`200`
  - batch_success_receipt_visible=`true`
  - batch_failed_items_visible=`true`
  - list_get_after_batch=`true`（status=`200`）
  - screenshots_count=`3`
- fail-closed：
  - missing `X-Request-ID` -> `409`
  - mismatched `X-Request-ID` -> `409`
  - missing `source_ref` -> `409`
  - mismatched `source_ref` -> `409`
  - `db_write_on_failed_gate_count=0`（核心业务写表）
- 写请求审计：
  - approved_write_request_count=`1`（仅 `POST /api/workshop/tickets/batch`）
  - allowed_batch_import_write_count=`1`
  - unexpected_write_request_count=`0`
  - forbidden_batch_sync_worker_request_count=`0`
  - upload_download_export_print_request_count=`0`
  - erpnext_write_count=`0`
  - production_write_count=`0`
  - 说明：开发态资源 `@id/__x00__plugin-vue:export-helper` 已从 side-effect 计数口径排除，不计入 upload/download/export/print。

## 5. rollback 与 zero_residual

- rollback 顺序执行：
  1) `ys_workshop_job_card_sync_outbox`
  2) `ys_workshop_job_card_sync_log`
  3) `ys_workshop_daily_wage`
  4) `ys_workshop_ticket`
  5) `ly_operation_audit_log`
  6) `ly_security_audit_log`
  7) `ys_workshop_outbox_access_denial`
- 清理后残留计数均为 `0`：
  - `ys_workshop_ticket`
  - `ys_workshop_daily_wage`
  - `ys_workshop_job_card_sync_outbox`
  - `ys_workshop_job_card_sync_log`
  - `ys_workshop_outbox_access_denial`
  - `ly_operation_audit_log`
  - `ly_security_audit_log`

## 6. 产物路径

- 报告：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-Z002B-26-IMPL_工票批量导入最小真实写入闭环实现与浏览器回归报告.md`
- evidence JSON：`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002b_26_workshop_ticket_batch_write_closure_evidence.json`
- 浏览器证据：`/tmp/task_z002b26_browser_result.json`
- API fail-closed 证据：`/tmp/task_z002b26_fail_probe.json`
- cleanup 证据：`/tmp/task_z002b26_cleanup.json`
- 截图目录：`/tmp/task_z002b26_screenshots`

## 7. 禁止动作核对

- 未执行 `git add / commit / push`
- 未执行 `PR / merge / tag / release`
- 未执行 repo `cleanup / reset / restore / clean / delete`
- 未触发生产写入
- 未触发 ERPNext 写入
