# TASK-YISUAN-REALOBJ-B036-REGRESSION-CAND005

## ROLE
- B Engineer

## SCOPE_RESULT
- lane: `regression-only / no code changes`
- baseline_ok: `true`
- branch: `codex/sprint4-seal`
- HEAD: `db826b57fb11b00eb2400ea278bfcc45667230dc`
- cached_count: `0`
- HEAD_tag_count: `0`
- git_diff_check: `PASS`
- git_diff_cached_check: `PASS`
- forbidden_paths_touched: `[]`

## CODE_MODIFIED_IN_THIS_TASK
- `false`
- 代码哈希证据：`code_hash_evidence.json`（3 个实现文件 before/after 一致）

## EVIDENCE
- evidence_dir: `03_需求与设计/02_开发计划/evidence/yisuan_realobj_b036_cand005_regression`
- scenario_tag: `REALOBJ-CAND005-B036-REG-20260601-001`

- routes:
  - `/sales-inventory/stock-ledger` HTTP `200`
  - `/warehouse` HTTP `200`
  - file: `route_probe.json`

- screenshots:
  - 2 张 PNG，均为 `1440x1200`
  - file: `screenshot_evidence.json`

- network write（local-dev only）:
  - `POST /api/local-dev/stock-ledger/draft`
  - `PATCH /api/local-dev/stock-ledger/draft/:id`
  - `POST /api/local-dev/stock-ledger/draft/:id/rollback`
  - `write_requests_observed_count=3`
  - `production_write_requests=0`
  - `erpnext_production_write_requests=0`
  - `real_production_account_used=false`
  - files: `network_write_evidence.json`, `local_dev_endpoint_evidence.json`

- local object loop:
  - `scenario_tag_present=true`
  - `create_success=true`
  - `update_success=true`
  - `stock_ledger_readback_success=true`
  - `warehouse_readback_success=true`
  - `cancel_or_rollback_success=true`
  - `zero_residual=true`
  - `residual_records=0`
  - files:
    - `local_object_loop_evidence.json`
    - `stock_ledger_readback_evidence.json`
    - `warehouse_readback_evidence.json`
    - `rollback_zero_residual_evidence.json`

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
- `data_classification=local_real_object_test_data_only`
- `test_data_used=true`
- `seed_data_used=false`
- `sqlite_is_formal_db=false`
- `not_future_production_data=true`
- `production_readback=false`
- `go_live=false`
- `project_completion=false`
- `remote_lifecycle_parked=true`

## RESIDUAL_RISK
- 仓库历史 dirty/untracked 噪声较多，后续 gate 仍需严格按 CAND005 freeze YES 边界执行。
- 本回归结论仅覆盖 local-dev/sqlite/test_data 闭环，不代表生产可用。

## NEXT_ROLE
- C Auditor
