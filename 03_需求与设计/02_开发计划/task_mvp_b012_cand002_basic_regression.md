# TASK-MVP-B012-REGRESSION-CAND002

## SUMMARY
- head: `bacbc355e58b8f0fbf8a847f3775729927b9ad8c`
- branch: `codex/sprint4-seal`
- regression_only: `true`
- code_modified_in_this_task: `false`
- changed_files:
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue`
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
  - `07_后端/lingyi_service/app/local_dev.py`
- local_mvp_loop_complete: `true`
- data_classification: `test_data`
- next_task: `TASK-MVP-B013-LEDGER-CAND002`

## EVIDENCE
- routes:
  - `/sales-inventory/references` -> `HTTP 200`, final_path=`/sales-inventory/references`
  - `/foundation/warehouse` -> `HTTP 200`, final_path=`/warehouse?parity=foundation-warehouse`
  - `/warehouse` -> `HTTP 200`, final_path=`/warehouse`
- screenshots:
  - `03_需求与设计/02_开发计划/evidence/mvp_b012_cand002_basic_regression/mvp_b012_sales_inventory_references_1440x1200.png` (PNG 1440x1200)
  - `03_需求与设计/02_开发计划/evidence/mvp_b012_cand002_basic_regression/mvp_b012_foundation_warehouse_1440x1200.png` (PNG 1440x1200)
- dom_anchors_observed: `10/10`
  - mvp-basic-reference-tabs
  - mvp-basic-reference-query-filter
  - mvp-basic-customer-reference
  - mvp-basic-supplier-reference
  - mvp-basic-factory-reference
  - mvp-basic-material-reference
  - mvp-basic-warehouse-card
  - mvp-basic-local-draft
  - mvp-basic-local-save-cancel-readback
  - mvp-basic-rollback-zero-residual
- local_write_loop_evidence:
  - scenario_tag=`MVP-B012-BASIC-20260531-001`
  - save_success=`true`
  - draft_id_created=`true` (draft_id=3)
  - cancel_success=`true`
  - readback_success=`true`
  - rollback_success=`true`
  - zero_residual_success=`true`
  - residual_records_after_rollback=`0`
- data_boundary_evidence:
  - data_classification=`test_data`
  - test_data_used=`true`
  - seed_data_used=`false`
  - not_future_production_data=`true`
  - sqlite_not_formal_database=`true`
  - sqlite_direct_reuse_for_production_forbidden=`true`
  - future_seed_data_migration_required=`true`
  - seed_data_json_csv_export_available=`false`
  - real_inventory_finance_production_records_migrated=`false`
  - real_stock_in_out_records_migrated=`false`
- network_write_observation:
  - auth_401_on_local_sqlite_write_loop=`false`
  - auth_401_count=`0`
  - production_write_requests=`0`
  - erpnext_production_write_requests=`0`
  - erpnext_production_connected=`false`
  - real_production_account_used=`false`
  - write_requests_observed_count=`3`
  - write_requests_only_local_dev=`true`
- typecheck:
  - command=`npm run typecheck`
  - workdir=`06_前端/lingyi-pc`
  - exit_code=`0`
- dev_server_started: `true`
- dev_server_stopped: `true`
- local_dev_started: `true`
- local_dev_stopped: `true`

## SCOPE_GUARD
- authorized_changed_files_only: `true`
- local_dev_py_status: `governed_local_dev_sqlite_scenario_tag_support`
- forbidden_paths_touched: `[]`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`
- git_diff_check: `PASS`
- cached_empty: `true`

## RESIDUAL_RISK
- local_dev.py remains local-dev/sqlite/scenario_tag support only
- seed_data boundary must be carried into B013 ledger/stage
- remote_lifecycle_parked=true
- production_readback=false
- go_live=false
- project_completion=false

## NEXT_RECOMMENDED_TASK
- `TASK-MVP-B013-LEDGER-CAND002`
