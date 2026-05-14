# TASK-Z002B-32-IMPL 实现报告

## 1. 任务结论
- 结果：`READY_FOR_REVIEW`
- 范围：仅在 allowlist 内实现并验证 `/warehouse` 与 `/sales-inventory/stock-ledger` 最小闭环。
- 本轮未执行：`git add/commit/push`、`PR/merge/tag/release/cleanup repo files`。

## 2. 代码改动（allowlist 内）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py`
  - 本地只读 fallback 使用的 schema import 补齐。
  - `GET /api/warehouse/stock-ledger` 与 `GET /api/warehouse/stock-summary` 在 ERPNext 不可用时可走 local-dev fallback。
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
  - `GET /api/sales-inventory/items/{item_code}/stock-summary`、`GET /api/sales-inventory/items/{item_code}/stock-ledger` 接入 local-dev fallback。
- 其余实现文件沿用既有改动：
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/warehouse.ts`
  - `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`

## 3. 写入闭环验证
- scenario_tag：`Z002-WAREHOUSE-STOCK-20260513-331`
- 允许写接口触发：
  - `POST /api/warehouse/stock-entry-drafts`（201）
  - `POST /api/warehouse/stock-entry-drafts/4/cancel`（200）
- `approved_write_request_count=2`
- `unexpected_write_request_count=0`
- `erpnext_write_count=0`
- `worker_sync_internal_job_request_count=0`
- `upload_download_export_print_request_count=0`
- `production_write_count=0`

## 4. fail-closed 验证
- `missing request_id` -> `409`
- `mismatched request_id` -> `409`
- `mismatched source_id` -> `409`
- `db_write_on_failed_gate_count=0`

## 5. 回读与台账计算
- `readback_get_after_create=true`
- `readback_get_after_cancel=true`
- `stock_ledger_compute_get_triggered=true`
- 关键 GET 在 local-dev fallback 下为 200：
  - `/api/warehouse/stock-ledger?...`
  - `/api/sales-inventory/items/{item_code}/stock-ledger?...`

## 6. rollback 与 zero_residual
- rollback 顺序执行：
  `ly_warehouse_stock_entry_outbox_event -> ly_warehouse_stock_entry_draft_item -> ly_warehouse_stock_entry_draft -> ly_operation_audit_log -> ly_security_audit_log -> ly_warehouse_inventory_count_item -> ly_warehouse_inventory_count`
- `rollback_cleanup_executed=true`
- `zero_residual=true`
- `residual_counts_by_table` 全部为 0（见 evidence JSON）。

## 7. 证据文件
- 结构化证据：
  - `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/task_z002b_32_warehouse_stock_write_closure_evidence.json`
- 浏览器证据：
  - `/tmp/task_z002b32_browser_result.json`
  - `/tmp/task_z002b32_screenshots`（`screenshots_count=3`）
- cleanup 证据：
  - `/tmp/task_z002b32_cleanup.json`

## 8. 验证命令结果摘要
- `python3 -m py_compile ...`：PASS
- `npm run precheck:dev-runtime`：PASS
- `npm run typecheck`：PASS
- `npm run verify`：PASS
- `python3 -m json.tool task_z002b_32_warehouse_stock_write_closure_evidence.json`：PASS
- `python3 -m json.tool /tmp/task_z002b32_browser_result.json`：PASS
- `python3 -m json.tool /tmp/task_z002b32_cleanup.json`：PASS
- `git diff --cached --name-only`：EMPTY
- `git diff --cached --check`：PASS
- `git diff --check`：PASS
