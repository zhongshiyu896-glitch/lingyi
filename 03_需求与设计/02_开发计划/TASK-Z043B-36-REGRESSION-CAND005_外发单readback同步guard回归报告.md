# TASK-Z043B-36-REGRESSION-CAND005 外发单 readback 同步 guard 回归报告

## Summary

- task_id: TASK-Z043B-36-REGRESSION-CAND005
- role: B Engineer
- code_modified_in_this_task: false
- changed_files_observed:
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
- allowed_files_only: true
- api_subcontract_touched: false
- read_only_boundary_preserved: true

## Route Evidence

- route evidence: `04_测试与验收/测试证据/z043_cand005_subcontract_readback_sync_guard_regression/route_evidence.json`
- `/subcontract/list`: HTTP 200, final_path `/subcontract/list`
- `/subcontract/detail`: HTTP 200, final_path `/subcontract/detail`
- `/materialPurchase/materialPurchaseProcess`: HTTP 200, parity redirect `/materialPurchase/materialPurchaseProcess -> /subcontract/list?parity=material-purchase`

## Screenshots And Anchors

- list screenshot: `04_测试与验收/测试证据/z043_cand005_subcontract_readback_sync_guard_regression/subcontract_list_z043_readback_sync_guard_regression.png`, PNG 1440x1200
- detail screenshot: `04_测试与验收/测试证据/z043_cand005_subcontract_readback_sync_guard_regression/subcontract_detail_z043_readback_sync_guard_regression.png`, PNG 1440x1200
- DOM anchors evidence: `04_测试与验收/测试证据/z043_cand005_subcontract_readback_sync_guard_regression/dom_anchors_evidence.json`
- anchors_observed_count: 8
- anchors_all_observed: true

## Guard And Network

- guarded readonly evidence: `04_测试与验收/测试证据/z043_cand005_subcontract_readback_sync_guard_regression/guarded_readonly_state_evidence.json`
- guarded entries covered: 新建外发单、发料、回料、验货、结算预览、同步重试、导出、打印
- dataReadonlyBoundary: true
- dataWriteRequestSuccessAllowed: false
- dataRealWriteActionAdded: false
- network observation: `04_测试与验收/测试证据/z043_cand005_subcontract_readback_sync_guard_regression/network_write_request_observation.json`
- auth_401_count: 4
- runtime_readonly_fallback_risk: true
- write_requests_observed_count: 0
- write_request_success_observed: false
- write_request_success_allowed: false

## Typecheck And Scope

- typecheck command: `npm run typecheck`
- typecheck workdir: `06_前端/lingyi-pc`
- typecheck exit_code: 0
- git diff --check: PASS
- cached_empty: true
- head_tag_empty: true
- dev_server_started: true
- dev_server_stopped: true
- backend_api_added: false
- real_write_action_added: false
- stage_performed: false
- commit_performed: false
- remote_lifecycle_released: false

## Risk Fields Preserved

- CAND005 B35 auth_401_count=4 readonly fallback risk
- CAND005 B36 observed auth_401_count=4 readonly fallback risk
- CAND004 B27/B28 auth_401_count=1/1 readonly fallback risk
- CAND003 B19/B20 auth_401_count=1/1 readonly fallback risk
- CAND002 B11/B12 auth_401_count=30/30 readonly fallback risk
- Z043-CAND-001 B03/B04 auth_401_count=2/2 readonly fallback risk
- prior non-allowlisted summary/metadata: continue excluded
- Z042/Z041/Z040/Z039/Z038 fallback risks preserved
- guarded_readonly_not_write_success: true
- B28 shell_wrapper_anomaly: preserved
- Z033 skipped_only: preserved
- Z035 screenshot_missing_risk: preserved
- remote_lifecycle_parked: true
- push_tag_pr_release: false
- production_readback: false
- go_live: false
- project_completion: false

## Next

- next_task: TASK-Z043B-37-LEDGER-CAND005
