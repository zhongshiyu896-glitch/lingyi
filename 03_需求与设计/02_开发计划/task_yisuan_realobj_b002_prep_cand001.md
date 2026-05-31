# TASK-YISUAN-REALOBJ-B002-PREP-CAND001

## 基线（只读）
- branch: `codex/sprint4-seal`
- HEAD: `87821f6429b5ebc4d4dd3512faa97a9eed7a3734`
- pool_source: `TASK-YISUAN-REALOBJ-B001-PREP-LOCAL-WRITE-POOL`
- selected_candidate: `REALOBJ-CAND-001`
- cached_count: `0`
- HEAD_tag_count: `0`
- git_diff_check: `PASS`

## 前序阶段回读
- source: `TASK-YISUAN-CONTRACT-B042-POST-FREEZE-REANCHOR`
- final_freeze_pass: `true`
- post_freeze_reanchor_pass: `true`
- covered_contract_ids_total: `["A001","A002","A003","A004","A005","A006"]`
- local_candidate_pool_status: `ZERO_REMAINING_CONTRACT_ACTIONABLE`

## selected_candidate / module_scope
- selected_candidate: `REALOBJ-CAND-001`
- module_scope: `基础资料本地真实对象与回读闭环`
- covered_contract_ids: `["A001","A003"]`
- covered_routes:
  - `/sales-inventory/references`
  - `/foundation/warehouse`
  - `/warehouse`

## routes / route_source_locations
- `/sales-inventory/references`
  - source: `06_前端/lingyi-pc/src/router/index.ts:180-182`
  - type: `direct`
  - target: `@/views/sales_inventory/SalesInventoryReferenceList.vue`
- `/foundation/warehouse`
  - source: `06_前端/lingyi-pc/src/router/index.ts:233-234`
  - type: `redirect`
  - target: `/warehouse?parity=foundation-warehouse`
- `/warehouse`
  - source: `06_前端/lingyi-pc/src/router/index.ts:186-188`
  - type: `direct`
  - target: `@/views/warehouse/WarehouseDashboard.vue`

## contract_sources_status
- A001 source: `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A001_evidence_coverage_matrix_20260520/evidence_coverage_matrix.json`
- A003 source: `04_测试与验收/测试证据/yisuan_business_shadow_capture/YISUAN_CAP_A003_ui_route_field_button_readonly_contract_20260520/ui_contract_development_input.json`
- contract_sources_exist: `true`

## allowed_frontend_status
- proposed_allowed_frontend_files:
  - `06_前端/lingyi-pc/src/views/sales_inventory/SalesInventoryReferenceList.vue`
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
- allowed_frontend_files_exist: `true`
- allowed_frontend_files_clean: `true`

## allowed_backend_support_status
- proposed_allowed_backend_support_files:
  - `07_后端/lingyi_service/app/local_dev.py`
- allowed_backend_support_files_exist: `true`
- allowed_backend_support_files_clean: `true`
- optional_support_status: `exists=true, clean=true, read_only_support_only=true`

## local_object_model / local_dev_endpoint_plan / sqlite_storage_plan
- local_object_model:
  - `foundation_reference_entity`
  - `foundation_warehouse_entity`
  - `foundation_readback_snapshot`
- local_dev_endpoint_plan:
  - `GET /local-dev/foundation/references?scenario_tag=<tag>`
  - `POST /local-dev/foundation/references (test_data only)`
  - `PATCH /local-dev/foundation/references/:id (test_data only)`
  - `POST /local-dev/foundation/references/:id/cancel (soft-cancel)`
  - `GET /local-dev/foundation/warehouses?scenario_tag=<tag>`
- sqlite_storage_plan:
  - `local_foundation_reference`
  - `local_foundation_warehouse`
  - `local_foundation_change_log`

## frozen_contract_boundary（B001 继承）
- scenario_tag_strategy: `all create/update/readback rows must carry scenario_tag; cleanup uses scenario_tag-scoped rollback`
- create_update_readback_cancel_or_rollback_flow: `create(test_data)->update(test_data)->readback->cancel/rollback->verify zero_residual`
- rollback_zero_residual_requirement: `mandatory`
- test_data_boundary: `enabled=true, scenario_tag_required=true, rollback_required=true, zero_residual_required=true`
- seed_data_boundary: `seed_data_used=false, if_needed_rule=JSON/CSV export + migration/import`
- forbidden_scope:
  - `production readback/go-live/release`
  - `real inventory/finance/production writes`
  - `cross-module linked calculation enablement`
- browser_evidence_plan:
  - `route HTTP 200: /sales-inventory/references`
  - `route HTTP 200: /foundation/warehouse -> /warehouse?parity=foundation-warehouse`
  - `route HTTP 200: /warehouse`
  - `screenshots 1440x1200`
  - `zero-write observation + request method evidence`
- typecheck_required: `true`

## frozen_write_loop_boundary（B003）
- scenario_tag_required: `true`
- test_data_used: `true`
- seed_data_used_default: `false`
- create/update flow: `create(test_data) -> update(test_data)`
- readback flow: `readback by scenario_tag from local-dev + sqlite snapshot`
- cancel/rollback flow: `cancel/rollback by scenario_tag scope`
- zero_residual_required: `true`
- sqlite_write_scope: `local sqlite only`

## frozen_evidence_requirement（B003）
- routes_http_200:
  - `/sales-inventory/references`
  - `/foundation/warehouse`
  - `/warehouse`
- screenshots_png_1440x1200: `true`
- local_dev_write_requests_only: `true`
- create_update_success: `true`
- local_object_id_generated: `true`
- readback_success: `true`
- cancel_rollback_success: `true`
- zero_residual: `true`
- scenario_tag_present: `true`
- production_write_requests: `0`
- erpnext_production_write_requests: `0`
- real_production_account_used: `false`
- sqlite_not_formal_database: `true`
- seed_data_used: `false`
- typecheck_exit_code: `0`
- dev_server_started_stopped: `true`
- local_dev_server_started_stopped: `true`

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
- test_data_used: `true`
- scenario_tag_required: `true`
- rollback_required: `true`
- zero_residual_required: `true`
- seed_data_used_default: `false`
- sqlite_not_formal_database: `true`
- sqlite_direct_reuse_for_production_forbidden: `true`
- erpnext_production_connected: `false`
- real_production_account_used: `false`
- production_readback: `false`
- go_live: `false`
- project_completion: `false`
- remote_lifecycle_parked: `true`

## production_safety_boundary
- ERPNext production: `forbidden`
- real production account: `forbidden`
- real business data migration: `forbidden`
- production readback: `forbidden`
- go-live: `forbidden`
- remote lifecycle release: `forbidden`

## 结论
- implementation_allowed: `true`
- next_task: `TASK-YISUAN-REALOBJ-B003-IMPL-CAND001`
- residual_risk: `low`
- NEXT_ROLE: `C Auditor`
