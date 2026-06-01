# TASK-YISUAN-REALOBJ-B018-PREP-CAND003

- TASK_ID: `TASK-YISUAN-REALOBJ-B018-PREP-CAND003`
- ROLE: `B Engineer`
- STATUS: `PASS`
- task_type: `PREP/boundary-only`

## HEAD / branch / cached_count / HEAD_tag_count

- HEAD: `556c7ac1212e5d7b728d710f9f906983cb29aa31`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`
- git_diff_check: `PASS`

## selected_candidate / module_scope

- selected_candidate: `REALOBJ-CAND-003`
- module_scope: `大货销售订单与生产计划本地真实对象闭环`
- covered_contract_ids: `["A002","A006"]`

## routes / route_source_locations

- routes:
  - `/sales-inventory/sales-orders`
  - `/sales-inventory/sales-orders/detail`
  - `/production/plans`
- route_source_locations:
  - `/sales-inventory/sales-orders` -> `06_前端/lingyi-pc/src/router/index.ts:162-164`
  - `/sales-inventory/sales-orders/detail` -> `06_前端/lingyi-pc/src/router/index.ts:168-170`
  - `/production/plans` -> `06_前端/lingyi-pc/src/router/index.ts:51-53`

## allowed_frontend_status

- allowed_frontend_files:
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderList.vue`
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventorySalesOrderDetail.vue`
  - `06_前端/lingyi-pc/src/views/production/ProductionPlanList.vue`
- allowed_frontend_files_exist: `true`
- allowed_frontend_files_clean: `true`

## allowed_backend_support_status

- allowed_backend_support_files:
  - `07_后端/lingyi_service/app/local_dev.py`
- allowed_backend_support_files_exist: `true`
- allowed_backend_support_files_clean: `true`

## local_object_model

- `local_sales_order_header`
- `local_sales_order_quantity_matrix`
- `local_production_plan_header`

## local_dev_endpoint_plan

- `GET /local-dev/sales-orders?scenario_tag=<tag>`
- `POST /local-dev/sales-orders (test_data only)`
- `PATCH /local-dev/sales-orders/:id (test_data only)`
- `GET /local-dev/production-plans?scenario_tag=<tag>`
- `POST /local-dev/production-plans/:id/rollback`

## sqlite_storage_plan

- `local_sales_order_header`
- `local_sales_order_line_matrix`
- `local_production_plan`

## frozen_write_loop_boundary

- scenario_tag required: `true`
- test_data_used: `true`
- seed_data_used: `false` (default)
- create/update object flow: `true`
- sales_order_draft_object_flow: `true`
- quantity_matrix_object_flow: `true`
- production_plan_draft_object_flow: `true`
- readback flow: `true`
- cancel_or_rollback_flow: `true`
- zero_residual_required: `true`
- forbidden_production_paths: `true`
- forbidden_real_account_boundary: `true`

## frozen_evidence_requirement

- routes HTTP 200:
  - `/sales-inventory/sales-orders`
  - `/sales-inventory/sales-orders/detail`
  - `/production/plans`
- PNG screenshots: `1440x1200`
- local-dev write only: `true`
- create/update success: `true`
- local_object_id_created: `true`
- sales_order_readback_success: `true`
- quantity_matrix_readback_success: `true`
- production_plan_readback_success: `true`
- cancel/rollback success: `true`
- zero_residual: `true`
- scenario_tag present: `true`
- production_write_requests: `0`
- erpnext_production_write_requests: `0`
- real_production_account_used: `false`
- sqlite_not_formal_database: `true`
- seed_data_used: `false`
- typecheck exit_code: `0`
- dev server started/stopped: `true`
- local_dev server started/stopped: `true`

## dirty_classification

- tracked_dirty_count: `16`
- frontend_dirty_count: `3`
- backend_or_test_dirty_count: `10`
- log_control_dirty_count: `3`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`

## data_boundary

- data_classification: `local_real_object_test_data_only`
- test_data_used in implementation: `true`
- scenario_tag_required: `true`
- rollback_required: `true`
- zero_residual_required: `true`
- seed_data_used: `false`（默认）
- seed_data if needed: `JSON/CSV export + future migration/import only`
- sqlite_not_formal_database: `true`
- sqlite_direct_reuse_for_production_forbidden: `true`
- real_inventory_finance_production_records_migrated: `false`
- real_stock_in_out_records_migrated: `false`

## production_safety_boundary

- erpnext_production_connected: `false`
- real_production_account_used: `false`
- production_readback: `false`
- go_live: `false`
- project_completion: `false`
- remote_lifecycle_parked: `true`

## prohibited_actions_confirmation

- code_modified: `false`
- browser/typecheck/pytest: `not run`
- sqlite_write: `false`
- business_object_created: `false`
- stage/commit/amend: `false`
- push/PR/tag/release: `false`
- reset/restore/clean/delete: `false`
- ERPNext production connect: `false`
- real production account: `false`

## next_task

- implementation_allowed: `true`
- next_task: `TASK-YISUAN-REALOBJ-B019-IMPL-CAND003`
- residual_risk: `仓库历史 dirty/untracked 噪声仍多，后续实现与暂存必须严格按后续 freeze 边界显式操作。`
- NEXT_ROLE: `C Auditor`
