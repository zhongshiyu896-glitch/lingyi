# TASK-YISUAN-REALOBJ-B034-PREP-CAND005

- ROLE: B Engineer
- STATUS: PASS
- LANE: PREP/boundary-only

## Baseline

- HEAD: `db826b57fb11b00eb2400ea278bfcc45667230dc`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`
- git diff --check: `PASS`

## Selected Candidate

- selected_candidate: `REALOBJ-CAND-005`
- module_scope: `物料进销存库存流水与仓库本地真实对象闭环`
- routes:
  - `/sales-inventory/stock-ledger`
  - `/warehouse`
- route_source_locations:
  - `/sales-inventory/stock-ledger` -> `06_前端/lingyi-pc/src/router/index.ts:174-176`
  - `/warehouse` -> `06_前端/lingyi-pc/src/router/index.ts:186-188`

## Allowed Files Check

- frontend:
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryStockLedger.vue` (exists=true, clean=true)
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue` (exists=true, clean=true)
- backend support:
  - `07_后端/lingyi_service/app/local_dev.py` (exists=true, clean=true)
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## Frozen Local Object Model

- `local_stock_ledger_entry`
- `local_warehouse_stock_snapshot`
- `local_transfer_or_count_draft`

## Frozen Endpoint Plan (local-dev only)

- `GET /local-dev/stock-ledger?scenario_tag=<tag>`
- `POST /local-dev/stock-ledger/draft (test_data only)`
- `PATCH /local-dev/stock-ledger/draft/:id (test_data only)`
- `GET /local-dev/warehouse/snapshot?scenario_tag=<tag>`
- `POST /local-dev/stock-ledger/draft/:id/rollback`

## Frozen SQLite Plan

- `local_stock_ledger`
- `local_warehouse_snapshot`
- `local_stock_change_log`

## Frozen Write Loop Boundary (for B035)

- scenario_tag required: `true`
- flow: `create -> update -> readback -> cancel/rollback -> zero_residual`
- zero_residual required: `true`
- residual_records target: `0`
- test_data_used: `true` (仅实现/回归阶段)
- seed_data_used: `false` (默认)
- implementation_allowed: `true`
- forbidden scope:
  - 真实库存出入库写入
  - 真实库存/财务联动
  - 真实库存/财务/生产迁移
  - ERPNext production 连接
  - 真实生产账号使用
  - go-live / project completion / release 声明

## Frozen Evidence Requirement (for B035)

- routes HTTP 200:
  - `/sales-inventory/stock-ledger`
  - `/warehouse`
- screenshots: `2 x PNG (1440x1200)`
- local-dev-only write requests: `true`
- create/update/readback/cancel_or_rollback: `success`
- stock ledger readback success: `true`
- warehouse readback success: `true`
- scenario_tag_present: `true`
- zero_residual: `true`
- residual_records: `0`
- production_write_requests: `0`
- erpnext_production_write_requests: `0`
- real_production_account_used: `false`
- typecheck: `npm run typecheck` in `06_前端/lingyi-pc`, `exit_code=0`
- server lifecycle:
  - dev server started/stopped: `true`
  - local_dev server started/stopped: `true`
- git diff --check: `PASS`

## Dirty Classification

- tracked_dirty_count: `16`
- frontend_dirty_count: `3`
- backend_or_test_dirty_count: `10`
- log_control_dirty_count: `3`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## Data Boundary

- data_classification: `local_real_object_test_data_only`
- test_data_used: `only in later implementation/regression`
- scenario_tag_required: `true`
- rollback_required: `true`
- zero_residual_required: `true`
- seed_data_used: `false`
- sqlite_is_formal_db: `false`
- not_future_production_data: `true`
- production_readback: `false`
- go_live: `false`
- project_completion: `false`
- remote_lifecycle_parked: `true`

## Production Safety Boundary

- erpnext_production_connected: `false`
- production_write_requests: `0`
- erpnext_production_write_requests: `0`
- real_production_account_used: `false`
- real_inventory_finance_production_records_migrated: `false`
- real_stock_in_out_records_migrated: `false`

## Next Task

- recommended_next_task: `TASK-YISUAN-REALOBJ-B035-IMPL-CAND005`
- NEXT_ROLE: `C Auditor`
