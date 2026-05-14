# TASK-Z002B-38-IMPL 实现报告

## 1. 任务结论
- 结果：`READY_FOR_REVIEW`
- 范围：仅在 allowlist 内实现并验证 `/sales-inventory/sales-orders` 与 `/sales-inventory/sales-orders/detail` 的最小真实写入闭环。
- 本轮未执行：`git add/commit/push`、`PR/merge/tag/release/cleanup`。

## 2. 代码改动（allowlist 内）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/sales_inventory.ts`
  - 新增本地写入 API：
    - `writeSalesOrderDraft(payload, { requestId })`
    - `voidSalesOrderDraft(draftId, reason, { requestId })`
  - 写请求强制支持 `X-Request-ID` 传递。
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
  - 增加本地写入入口按钮与 allowlist 标记。
  - 完成 create/cancel 后执行列表与详情回读。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
  - 新增并放开本地写入路由：
    - `POST /api/sales-inventory/sales-orders/drafts`
    - `POST /api/sales-inventory/sales-orders/drafts/{draft_id}/cancel`
  - 本地 gate：仅 `APP_ENV=development` + `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`。
  - scenario_tag 载体一致性 gate：`idempotency_key/source_order_ref/sales_order_no/reason/X-Request-ID(request_id)`。
  - fail-closed：缺失/非法/不一致统一 `409` 且禁止 DB 写入。
  - 修复响应序列化：`_ok(data)` 使用 `jsonable_encoder`，避免 `SalesOrderDraftData` 导致 500。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`
  - 新增 sales-order draft create/cancel/data schema。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`
  - 新增 local draft create/cancel/readback/fulfillment 聚合逻辑。
  - 写入时落地 outbox payload，用于后续审计与回读。

## 3. 写入闭环验证
- scenario_tag：`Z002-SALES-ORDER-20260514-381`
- 允许写接口触发：
  - `POST /api/sales-inventory/sales-orders/drafts`（201）
  - `POST /api/sales-inventory/sales-orders/drafts/1/cancel`（200）
- `approved_write_request_count=2`
- `unexpected_write_request_count=0`
- `erpnext_write_count=0`
- `worker_sync_internal_job_request_count=0`
- `upload_download_export_print_request_count=0`
- `production_write_count=0`

## 4. fail-closed 验证
- `missing request_id` -> `409`
- `mismatched request_id` -> `409`
- `mismatched source_ref` -> `409`
- `db_write_on_failed_gate_count=0`

## 5. 回读与履约计算
- `readback_get_after_create=true`
- `readback_get_after_cancel=true`
- `fulfillment_readback_triggered=true`（`GET /api/sales-inventory/sales-order-fulfillment`）
- 读回链路：
  - `GET /api/sales-inventory/sales-orders?order_no=<scenario_tag>`
  - `GET /api/sales-inventory/sales-orders/{name}`
  - `GET /api/sales-inventory/sales-order-fulfillment`

## 6. rollback 与 zero_residual
- rollback 顺序执行：
  `ly_sales_order_write_outbox_event -> ly_sales_order_write_draft_item -> ly_sales_order_write_draft -> ly_sales_order_fulfillment_snapshot -> ly_operation_audit_log -> ly_security_audit_log -> ly_sales_order_outbox_access_denial`
- `rollback_cleanup_executed=true`
- `zero_residual=true`
- `residual_counts_by_table` 全部为 0（见 evidence JSON）。
- 说明：本地模型实际落表为 `ly_warehouse_stock_entry_*`；`ly_sales_order_fulfillment_snapshot` 与 `ly_sales_order_outbox_access_denial` 在当前 sqlite 不存在，按冻结口径记为 `table_missing_treated_as_zero`。

## 7. 证据文件
- 结构化证据：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002b_38_sales_order_write_closure_evidence.json`
- 浏览器/接口证据：
  - `/tmp/task_z002b38_browser_result.json`
  - `/tmp/task_z002b38_ui_probe.json`
  - `/tmp/task_z002b38_screenshots`（`screenshots_count=3`）
- cleanup 证据：
  - `/tmp/task_z002b38_cleanup.json`

## 8. 验证命令结果摘要
- `python3 -m py_compile app/routers/sales_inventory.py app/schemas/sales_inventory.py app/services/sales_inventory_service.py`：PASS
- `npm run precheck:dev-runtime`：PASS
- `npm run typecheck`：PASS
- `npm run verify`：PASS
- `python3 -m json.tool task_z002b_38_sales_order_write_closure_evidence.json`：PASS
- `python3 -m json.tool /tmp/task_z002b38_browser_result.json`：PASS
- `python3 -m json.tool /tmp/task_z002b38_cleanup.json`：PASS
- `git diff --cached --name-only`：EMPTY
- `git diff --cached --check`：PASS
- `git diff --check`：PASS
