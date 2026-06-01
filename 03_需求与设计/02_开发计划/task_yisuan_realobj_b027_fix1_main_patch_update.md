# TASK-YISUAN-REALOBJ-B027-FIX1-MAIN-PATCH-UPDATE

## ROLE
- B Engineer

## SCOPE_RESULT
- baseline_ok: `true`
- branch: `codex/sprint4-seal`
- HEAD: `33444051168fc8c2939e8c2241dd840fb53f0b4e`
- cached_count: `0`
- HEAD_tag_count: `0`
- allowed_files_match: `true`
- forbidden_paths_touched: `[]`

## CHANGED_FILES
- `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
- `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
- `07_后端/lingyi_service/app/local_dev.py`
- `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_fix1_main_patch_update/*`
- `03_需求与设计/02_开发计划/task_yisuan_realobj_b027_fix1_main_patch_update.{json,md,tsv}`

## FIX_SUMMARY
- 主单 update 已固定为真实 PATCH：`PATCH /api/local-dev/subcontract/orders/:id`
- 已观测到主单 PATCH，且不再以第二次 POST 代替主单 update。
- 结算预览 PATCH 保留：`PATCH /api/local-dev/subcontract/orders/:id/settlement-preview`
- `readback_after_main_patch_success=true`
- rollback 覆盖主单、物料明细、结算预览，`zero_residual=true`

## EVIDENCE
- scenario_tag: `REALOBJ-CAND004-B027-FIX1-20260601-002`
- routes HTTP 200:
  - `/materialPurchase/materialPurchaseProcess`（final_path=`/subcontract/list?parity=material-purchase`）
  - `/subcontract/list?parity=material-purchase`
  - `/subcontract/detail`
- route evidence: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_fix1_main_patch_update/route_probe.json`
- screenshots: `3` 张 PNG，全部 `1440x1200`
- screenshot evidence: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b027_fix1_main_patch_update/screenshot_evidence.json`
- local-dev endpoint evidence:
  - `create_request_observed=true`
  - `main_patch_request_observed=true`
  - `settlement_preview_patch_request_observed=true`
  - `rollback_request_observed=true`
  - `all_local_dev_purchase_subcontract_write_statuses_success=true`
- network write evidence:
  - `POST /api/local-dev/subcontract/orders`
  - `PATCH /api/local-dev/subcontract/orders/:id`
  - `PATCH /api/local-dev/subcontract/orders/:id/settlement-preview`
  - `POST /api/local-dev/subcontract/orders/:id/rollback`
  - `write_requests_only_local_dev_purchase_subcontract_endpoints=true`
  - `production_write_requests=0`
  - `erpnext_production_write_requests=0`
  - `real_production_account_used=false`
- local object loop evidence:
  - `scenario_tag_present=true`
  - `create_success=true`
  - `update_success=true`
  - `local_object_id_created=true`
  - `readback_after_main_patch_success=true`
  - `subcontract_or_purchase_readback_success=true`
  - `material_line_readback_success=true`
  - `issue_return_or_inspection_readback_success=true`
  - `settlement_preview_readback_success=true`
  - `settlement_preview_status_observed=true`
  - `settlement_preview_amount_or_summary_observed=true`
  - `cancel_or_rollback_success=true`
  - `settlement_preview_included_in_rollback=true`
  - `zero_residual=true`
  - `residual_records=0`
- typecheck:
  - command: `npm run typecheck`
  - workdir: `06_前端/lingyi-pc`
  - exit_code: `0`
- server lifecycle:
  - `dev_server_started/stopped=true/true`
  - `local_dev_server_started/stopped=true/true`

## GIT_STATE
- `git diff --check`: `PASS`
- `git diff --cached --check`: `PASS`
- cached_count: `0`
- HEAD_tag_count: `0`

## DATA_BOUNDARY
- `data_classification=local_real_object_test_data_only`
- `test_data_used=true`
- `seed_data_used=false`
- `scenario_tag_required=true`
- `rollback_required=true`
- `zero_residual_required=true`
- `sqlite_is_formal_db=false`
- `not_future_production_data=true`
- `production_readback=false`
- `go_live=false`
- `project_completion=false`
- `remote_lifecycle_parked=true`

## RESIDUAL_RISK
- 仓库历史 dirty/untracked 噪声较多，后续 ledger/stage 需严格按本候选 freeze YES 显式边界执行。
- 本任务结论仅限 local-dev/sqlite/test_data 写入闭环，不代表生产可用。

## NEXT_ROLE
- C Auditor
