# TASK-YISUAN-REALOBJ-B028-REGRESSION-CAND004

## ROLE
- B Engineer

## SCOPE_RESULT
- lane: `regression-only / no code changes`
- baseline_ok: `true`
- branch: `codex/sprint4-seal`
- HEAD: `33444051168fc8c2939e8c2241dd840fb53f0b4e`
- cached_count: `0`
- HEAD_tag_count: `0`
- forbidden_paths_touched: `[]`
- 代码文件回归前后 hash 证据：`code_hash_evidence.json`

## CODE_MODIFIED_IN_THIS_TASK
- `false`
- 未修改产品代码：
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderList.vue`
  - `06_前端/lingyi-pc/src/views/subcontract/SubcontractOrderDetail.vue`
  - `07_后端/lingyi_service/app/local_dev.py`

## EVIDENCE
- evidence_dir: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b028_cand004_regression`
- scenario_tag: `REALOBJ-CAND004-B028-REG-20260601-001`

- routes:
  - `/materialPurchase/materialPurchaseProcess` HTTP `200`
  - final_path=`/subcontract/list?parity=material-purchase`
  - `/subcontract/list?parity=material-purchase` HTTP `200`
  - `/subcontract/detail` HTTP `200`
  - file: `route_probe.json`

- screenshots:
  - 3 张 PNG，全部 `1440x1200`
  - file: `screenshot_evidence.json`

- network write（仅 local-dev subcontract）:
  - `POST /api/local-dev/subcontract/orders`
  - `PATCH /api/local-dev/subcontract/orders/:id`
  - `PATCH /api/local-dev/subcontract/orders/:id/settlement-preview`
  - `POST /api/local-dev/subcontract/orders/:id/rollback`
  - `write_requests_observed_count=4`
  - `production_write_requests=0`
  - `erpnext_production_write_requests=0`
  - `real_production_account_used=false`
  - files: `network_write_evidence.json`, `local_dev_endpoint_evidence.json`

- local object loop:
  - `scenario_tag_present=true`
  - `create_success=true`
  - `update_success=true`
  - `main_order_readback_success=true`
  - `readback_after_main_patch_success=true`
  - `settlement_preview_readback_success=true`
  - `settlement_preview_status_observed=true`
  - `settlement_preview_amount_or_summary_observed=true`
  - `settlement_preview_included_in_rollback=true`
  - `cancel_or_rollback_success=true`
  - `zero_residual=true`
  - `residual_records=0`
  - files: `local_object_loop_evidence.json`, `settlement_preview_readback_evidence.json`, `rollback_zero_residual_evidence.json`

- typecheck:
  - `npm run typecheck` in `06_前端/lingyi-pc`
  - `exit_code=0`
  - file: `typecheck_result.json`

- server lifecycle:
  - `dev_server_started/stopped=true/true`
  - `local_dev_server_started/stopped=true/true`
  - file: `server_lifecycle_evidence.json`

## GIT_STATE
- `git diff --check=PASS`
- `git diff --cached --check=PASS`
- cached_count: `0`
- HEAD_tag_count: `0`

## DATA_BOUNDARY
- `test_data_used=true`
- `seed_data_used=false`
- `sqlite_is_formal_db=false`
- `not_future_production_data=true`
- `production_readback=false`
- `go_live=false`
- `project_completion=false`
- `remote_lifecycle_parked=true`

## RESIDUAL_RISK
- 仓库历史 dirty/untracked 噪声较多，后续 gate 必须严格按 freeze YES 边界执行。
- 本回归结论仅覆盖 local-dev/sqlite/test_data 闭环，不代表生产可用。

## NEXT_ROLE
- C Auditor
