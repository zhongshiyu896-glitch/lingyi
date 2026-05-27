# TASK-Z044B-36-REGRESSION-CAND005 回归复核报告

## scope confirmation

- task_id: `TASK-Z044B-36-REGRESSION-CAND005`
- role: `B Engineer`
- candidate_id: `Z044-CAND-005`
- source_task: `TASK-Z044B-35-IMPL`
- code_modified_in_this_task: `false`
- changed_files_observed:
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
- allowed_files_only: `true`
- api_subcontract_touched: `false`
- backend_api_added: `false`
- real_write_action_added: `false`
- read_only_boundary_preserved: `true`
- material_purchase_parity_recorded: `true`
- dirty_intersections: `[]`
- unknown_dirty: `[]`
- must_block_before_continue: `[]`
- stage_performed: `false`
- commit_performed: `false`
- remote_lifecycle_released: `false`

## evidence check

- route evidence:
  - `/subcontract/list`: HTTP `200`, final_path `/subcontract/list`
  - `/subcontract/detail`: HTTP `200`, final_path `/subcontract/detail`
  - `/materialPurchase/materialPurchaseProcess`: HTTP `200`, final_path `/subcontract/list?parity=material-purchase`
- screenshots:
  - `04_测试与验收/测试证据/z044_cand005_subcontract_list_detail_sync_lock_readback_regression/subcontract_list_regression_screenshot.png`, PNG `1440x1200`
  - `04_测试与验收/测试证据/z044_cand005_subcontract_list_detail_sync_lock_readback_regression/subcontract_detail_regression_screenshot.png`, PNG `1440x1200`
- runtime DOM anchors observed: `8/8`
  - `z044-subcontract-list-detail-diff`
  - `z044-subcontract-readback-consistency`
  - `z044-subcontract-sync-lock-reason`
  - `z044-subcontract-export-print-readonly`
  - `z044-subcontract-material-parity-readback`
  - `z044-subcontract-guarded-action-matrix`
  - `z044-subcontract-network-write-blocker`
  - `z044-subcontract-write-success-blocker`
- guarded readonly state:
  - guarded entries covered: 新建外发单、发料、回料、验货、结算预览、同步重试、导出、打印
  - `dataReadonlyBoundary=true`
  - `dataWriteRequestSuccessAllowed=false`
  - `dataRealWriteActionAdded=false`
- network/write observation:
  - `auth_401_count=4`
  - `runtime_readonly_fallback_risk=true`
  - `write_requests_observed_count=0`
  - `write_request_success_observed=false`
  - `write_request_success_allowed=false`
- typecheck:
  - command: `npm run typecheck`
  - workdir: `06_前端/lingyi-pc`
  - exit_code: `0`
- dev server:
  - started: `true`
  - url: `http://127.0.0.1:5174/`
  - stopped: `true`

## evidence files

- `04_测试与验收/测试证据/z044_cand005_subcontract_list_detail_sync_lock_readback_regression/route_evidence.json`
- `04_测试与验收/测试证据/z044_cand005_subcontract_list_detail_sync_lock_readback_regression/dom_anchors_evidence.json`
- `04_测试与验收/测试证据/z044_cand005_subcontract_list_detail_sync_lock_readback_regression/guarded_readonly_state_evidence.json`
- `04_测试与验收/测试证据/z044_cand005_subcontract_list_detail_sync_lock_readback_regression/network_write_request_observation.json`

## residual risk

- Z044-CAND-005 B35 `auth_401_count=3` readonly fallback risk preserved.
- Z044-CAND-005 B36 observed `auth_401_count=4` readonly fallback risk recorded.
- Z044-CAND-004 B27/B28 `auth_401_count=1/1` readonly fallback risk preserved.
- Z044-CAND-003 B19/B20 `auth_401_count=1/1` readonly fallback risk preserved.
- Z044-CAND-002 B11/B12 `auth_401_count=25/25` readonly fallback risk preserved.
- Z044-CAND-001 B03/B04 `auth_401_count=6/6` readonly fallback risk preserved.
- Z043 fallback risks preserved.
- prior non-allowlisted summary/metadata exclusion preserved.
- Z042-Z038 fallback risks preserved.
- `B28 shell_wrapper_anomaly` preserved.
- `Z033 skipped_only` preserved.
- `Z035 screenshot_missing_risk` preserved.
- `guarded_readonly_not_write_success=true`
- `remote_lifecycle_parked=true`
- `push_tag_pr_release=false`
- `production_readback=false`
- `go_live=false`
- `project_completion=false`
- `next_gate_blocked_pending_explicit_authorization=true`

## forbidden actions

- code modification in this task: `false`
- stage/commit: `false`
- push/tag/PR/release: `false`
- cleanup/reset/restore: `false`
- remote lifecycle released: `false`

## next

- next_task: `TASK-Z044B-37-LEDGER-CAND005`
