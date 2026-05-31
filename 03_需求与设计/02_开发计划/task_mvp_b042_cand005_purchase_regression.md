STATUS: DONE
TASK_ID: TASK-MVP-B042-REGRESSION-CAND005
ROLE: B Engineer

SUMMARY:
- head: 5d4220f04c909e9a6d8189b3491630d6e575e1d7
- branch: codex/sprint4-seal
- regression_only: true
- code_modified_in_this_task: false
- changed_files:
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue
  - 06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue
  - 07_后端/lingyi_service/app/local_dev.py
- local_mvp_loop_complete: true
- data_classification: test_data
- next_task: TASK-MVP-B043-LEDGER-CAND005

EVIDENCE:
- routes:
  - /materialPurchase/materialPurchaseProcess: HTTP 200, final_path=/subcontract/list?parity=material-purchase
  - /subcontract/list?parity=material-purchase: HTTP 200
  - /subcontract/detail: HTTP 200
- screenshots:
  - /subcontract/list?parity=material-purchase: 03_需求与设计/02_开发计划/evidence/mvp_b042_cand005_purchase_regression/subcontract_list_parity_1440x1200.png
  - /subcontract/detail: 03_需求与设计/02_开发计划/evidence/mvp_b042_cand005_purchase_regression/subcontract_detail_1440x1200.png
  - dimensions: 1440x1200
- redirect_parity_evidence:
  - /materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase
  - evidence_file: 03_需求与设计/02_开发计划/evidence/mvp_b042_cand005_purchase_regression/route_probe.json
- dom_anchors_observed: 12/12
- local_write_loop_evidence:
  - scenario_tag: MVP-CAND005-REG-1780216107714
  - save_success=true
  - draft_id_created=true
  - material_line_saved=true
  - issue_return_or_inspection_saved=true
  - cancel_success=true
  - readback_success=true
  - rollback_success=true
  - zero_residual_success=true
  - residual_records_after_rollback=0
- data_boundary_evidence:
  - data_classification=test_data
  - test_data_used=true
  - seed_data_used=false
  - not_future_production_data=true
  - sqlite_not_formal_database=true
  - sqlite_direct_reuse_for_production_forbidden=true
  - future_seed_data_migration_required=true
  - seed_data_json_csv_export_available=false
  - real_purchase_subcontract_inventory_finance_data_migration_forbidden=true
  - real_inventory_finance_production_records_migrated=false
  - real_stock_in_out_records_migrated=false
- network_write_observation:
  - auth_401_on_local_sqlite_write_loop=false
  - write_requests_observed_count=3（仅 local-dev purchase/subcontract endpoints）
  - production_write_requests=0
  - erpnext_production_write_requests=0
  - erpnext_production_connected=false
  - real_production_account_used=false
- typecheck:
  - command: npm run typecheck
  - workdir: 06_前端/lingyi-pc
  - exit_code: 0
- dev_server_started: true
- dev_server_stopped: true
- local_dev_started: true
- local_dev_stopped: true

SCOPE_GUARD:
- authorized_changed_files_only: true
- local_dev_py_status: tracked_modified_preexisting_not_touched_in_b042
- forbidden_paths_touched: []
- dirty_intersections: []
- unknown_dirty: []
- must_block_before_continue: []
- git_diff_check: PASS
- cached_empty: true

RESIDUAL_RISK:
- local_dev.py remains local-dev/sqlite/scenario_tag support only
- seed_data boundary must be carried into B043 ledger/stage
- remote_lifecycle_parked=true
- production_readback=false
- go_live=false
- project_completion=false

NEXT_RECOMMENDED_TASK:
- TASK-MVP-B043-LEDGER-CAND005
