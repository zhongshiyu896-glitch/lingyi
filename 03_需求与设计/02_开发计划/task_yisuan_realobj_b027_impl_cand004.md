# TASK-YISUAN-REALOBJ-B027-IMPL-CAND004

## HEAD / branch / cached_count / HEAD_tag_count
- HEAD: `33444051168fc8c2939e8c2241dd840fb53f0b4e`
- branch: `codex/sprint4-seal`
- cached_count: `0`
- HEAD_tag_count: `0`

## changed_files
- `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
- `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
- `07_后端/lingyi_service/app/local_dev.py`
- `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_cand004/*`
- `03_需求与设计/02_开发计划/task_yisuan_realobj_b027_impl_cand004.{json,md,tsv}`

## allowed_files_match
- `true`

## forbidden_paths_touched
- `[]`

## routes_evidence
- `/materialPurchase/materialPurchaseProcess` HTTP `200`, final_path=`/subcontract/list?parity=material-purchase`
- `/subcontract/list?parity=material-purchase` HTTP `200`
- `/subcontract/detail` HTTP `200`
- evidence: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_cand004/route_probe.json`

## screenshot_evidence
- PNG 数量: `3`
- 尺寸: `1440x1200` 全部通过
- files:
  - `route_material_purchase_redirect.png`
  - `route_subcontract_list.png`
  - `route_subcontract_detail.png`
- evidence: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_cand004/screenshot_evidence.json`

## local_dev_endpoint_evidence
- scenario_tag: `REALOBJ-CAND004-B027-20260601-001`
- create_request_observed: `true`
- update_request_observed: `true`
- settlement_preview_patch_request_observed: `true`
- rollback_request_observed: `true`
- all_local_dev_purchase_subcontract_write_statuses_success: `true`
- evidence: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_cand004/local_dev_endpoint_evidence.json`

## local_object_loop_evidence
- scenario_tag_present: `true`
- create_success: `true`
- update_success: `true`
- local_object_id_created: `true` (`object_id=5`)
- subcontract_or_purchase_readback_success: `true`
- material_line_readback_success: `true`
- issue_return_or_inspection_readback_success: `true`
- settlement_preview_created_or_updated: `true`
- settlement_preview_readback_success: `true`
- settlement_preview_status_observed: `true`
- settlement_preview_amount_or_summary_observed: `true`
- settlement_preview_real_finance_effect: `false`
- settlement_preview_real_payment_effect: `false`
- settlement_preview_real_inventory_effect: `false`
- cancel_or_rollback_success: `true`
- zero_residual: `true`
- residual_records: `0`

## rollback_zero_residual_evidence
- settlement_preview_included_in_rollback: `true`
- cancel_or_rollback_success: `true`
- zero_residual: `true`
- residual_records: `0`
- evidence: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_cand004/rollback_zero_residual_evidence.json`

## network_write_evidence
- write_requests_observed_count: `4`
- write_requests_only_local_dev_purchase_subcontract_endpoints: `true`
- production_write_requests: `0`
- erpnext_production_write_requests: `0`
- real_production_account_used: `false`
- write methods: `POST, POST, PATCH, POST`
- evidence: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_cand004/network_write_evidence.json`

## typecheck_evidence
- command: `npm run typecheck`
- workdir: `06_前端/lingyi-pc`
- exit_code: `0`
- evidence: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_cand004/typecheck_result.json`

## server_lifecycle_evidence
- dev server started/stopped: `true/true`
- local_dev server started/stopped: `true/true`
- evidence: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_cand004/server_lifecycle_evidence.json`

## data_boundary
- data_classification=`local_real_object_test_data_only`
- test_data_used=`true`
- seed_data_used=`false`
- not_future_production_data=`true`
- sqlite_is_formal_db=`false`
- sqlite_not_formal_database=`true`
- sqlite_direct_reuse_for_production_forbidden=`true`

## production_safety_boundary
- production_write_requests=`0`
- erpnext_production_write_requests=`0`
- real_production_account_used=`false`
- erpnext_production_connected=`false`
- real_settlement_or_finance_effect=`false`
- real_inventory_finance_production_records_migrated=`false`
- real_stock_in_out_records_migrated=`false`
- production_readback=`false`
- go_live=`false`
- project_completion=`false`
- remote_lifecycle_parked=`true`

## prohibited_actions_confirmation
- staged/committed/amended/pushed/tagged/released: `false`
- reset/restore/clean/delete: `false`
- router/API/非 local_dev 后端修改: `false`
- boundary_expanded: `false`

## dirty_intersections / unknown_dirty / must_block_before_continue
- `[] / [] / []`

## residual_risk
- 仓库存在大量历史 dirty/untracked 噪声，后续 ledger/stage 必须严格使用 CAND004 freeze YES 显式边界。
- 本任务仅证明 local-dev/sqlite/test_data 闭环，不代表 production readiness。

## NEXT_ROLE
- `C Auditor`
