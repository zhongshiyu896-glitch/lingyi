# TASK-Z045B-28-REGRESSION-CAND005 回归报告

## Scope Confirmation

- HEAD: `5ce8c37fed9ec46c31f4527142fe53da1ee429f8`
- branch: `codex/sprint4-seal`
- staged area: empty
- candidate: `Z045-CAND-005`
- code_modified_in_this_task: false
- changed files remain:
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
- `06_前端/lingyi-pc/src/api/subcontract.ts` touched: false
- backend API added: false
- real write action added: false
- read-only boundary preserved: true

## Evidence Check

- `/subcontract/list`: HTTP 200, final_path `/subcontract/list`
- `/subcontract/detail`: HTTP 200, final_path `/subcontract/detail`
- `/materialPurchase/materialPurchaseProcess`: HTTP 200, final_path `/subcontract/list?parity=material-purchase`
- screenshots:
  - `04_测试与验收/测试证据/z045_cand005_subcontract_sync_readback_regression/z045_cand005_regression_list_1440x1200.png`, PNG 1440x1200
  - `04_测试与验收/测试证据/z045_cand005_subcontract_sync_readback_regression/z045_cand005_regression_detail_1440x1200.png`, PNG 1440x1200
- DOM anchors observed: 8/8
- guarded readonly entries observed: 8/8
- guarded top-level fields:
  - `dataReadonlyBoundary=true`
  - `dataWriteRequestSuccessAllowed=false`
  - `dataRealWriteActionAdded=false`
- network/write:
  - auth_401_count=5, readonly fallback risk only
  - write_requests_observed_count=0
  - write_request_success_observed=false
  - write_request_success_allowed=false
- typecheck: `npm run typecheck`, workdir `06_前端/lingyi-pc`, exit_code=0
- dev server: started on `http://127.0.0.1:5174/` after 5173 was occupied, stopped=true

## Direction Compliance

- mainline_or_auxiliary=mainline
- user_visible_frontend_improvement=true
- interaction_experience_improvement=true
- one_to_one_ui_contract_focus=true
- readonly_guard_role=supporting
- candidate_direction_valid=true

## Residual Risk

- Z045-CAND-005 B27/B28 auth_401_count=5/5 readonly fallback risk
- Z045-CAND-004 auth_401_count=1/1 readonly fallback risk
- Z045-CAND-003 auth_401_count=1/1 readonly fallback risk
- Z045-CAND-002 auth_401_count=25/25 readonly fallback risk
- Z044/Z043/Z042-Z038 fallback risks retained
- prior non-allowlisted summary/metadata, Z034 residual, backend, runtime/cache, remote/prod-go-live remain excluded
- remote_lifecycle_parked=true
- push_tag_pr_release=false
- production_readback=false
- go_live=false
- project_completion=false

## Next Task

`TASK-Z045B-29-LEDGER-CAND005`
