# TASK-Z032B-27-FIX-CAND003-SECOND 二次修复验证报告

- TASK_ID: TASK-Z032B-27-FIX-CAND003-SECOND
- ROLE: B Engineer
- candidate_id: Z032-CAND-003
- source_task: TASK-Z032B-26-PREP-CAND003-SECOND-FAILURE-DIAG
- allowed_fix_file: `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`
- changed_files:
  - `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`
  - `03_需求与设计/02_开发计划/task_z032b_27_cand003_second_fix_stdout.txt`
  - `03_需求与设计/02_开发计划/TASK-Z032B-27-FIX-CAND003-SECOND_二次修复验证报告.md`
  - `03_需求与设计/02_开发计划/task_z032b_27_cand003_second_fix_result.json`
  - `03_需求与设计/02_开发计划/task_z032b_27_cand003_second_fix_result.tsv`

## 前置核对

- HEAD: `f1ee52224ea1a4615db30f51cb234eba023b1fb8`
- cached: empty
- `git diff --check`: PASS
- B26 classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- B26 allowed_fix_file: `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`
- B26 remaining_failed_cases_count: 6
- 当前目标测试 dirty diff: limited to allowed target test before this task

## 修复内容

- 仅修改授权目标测试中的 local carrier helper。
- 将测试内 `_carrier_code()` 从 upper-case normalized hash 调整为仅 `strip()` 后 hash，以匹配后端 carrier 计算合同。
- 未接受 `409` 为期望结果。
- 保留原 `500/503/200` 显式业务状态断言。
- 未新增 skip/xfail，未删除用例，未弱化为任意状态码或任意错误码断言。

## 单次验证

- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_workshop_batch_exceptions.py -q`
- command_run_count: 1
- exit_code: 1
- result: FAIL
- pytest_summary: `6 failed, 1 warning in 1.00s`
- stdout_path: `03_需求与设计/02_开发计划/task_z032b_27_cand003_second_fix_stdout.txt`

## FAIL Evidence

- `test_audit_write_failed_returns_500_not_failed_items`: observed `409`, expected `500`
- `test_database_write_failed_returns_500_not_failed_items`: observed `409`, expected `500`
- `test_permission_source_unavailable_returns_503_not_failed_items`: observed `409`, expected `503`
- `test_row_business_error_can_enter_failed_items`: observed `409`, expected `200`
- `test_row_resource_forbidden_can_enter_failed_items_and_write_security_audit`: observed `409`, expected `200`
- `test_unknown_error_returns_500_not_failed_items`: observed `409`, expected `500`

## 约束状态

- carrier_contract_remains_addressed: true
- idempotency_carrier_conflict_gate_addressed: false
- business_status_assertions_preserved: true
- no_409_conflict_acceptance: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- backend_app_changed: false
- frontend_changed: false
- unrelated_tests_changed: false
- continued_after_fail: false
- rerun_performed: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false
