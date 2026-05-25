# TASK-Z032B-12-FIX-CAND002 修复验证报告

- task_id: TASK-Z032B-12-FIX-CAND002
- role: B Engineer
- candidate_id: Z032-CAND-002
- source_task: TASK-Z032B-11-PREP-CAND002-FAILURE-DIAG
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
- current_head_before_run: `bbc298a8e2423ea51d82de66ed058835182bcade`
- cached_before_run: empty
- diff_check_before_run: PASS
- B11 classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- B11 allowed_fix_file: matched
- B10/B11 failed cases traced: 26

## 修改范围

- changed_files:
  - `07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
  - `03_需求与设计/02_开发计划/task_z032b_12_cand002_fix_stdout.txt`
  - `03_需求与设计/02_开发计划/TASK-Z032B-12-FIX-CAND002_修复验证报告.md`
  - `03_需求与设计/02_开发计划/task_z032b_12_cand002_fix_result.json`
  - `03_需求与设计/02_开发计划/task_z032b_12_cand002_fix_result.tsv`
- backend_app_changed: false
- frontend_changed: false
- unrelated_tests_changed: false
- stage/commit/push/tag/PR/release: false

## 单次验证

- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_subcontract_settlement_export.py -q`
- command_run_count: 1
- exit_code: 1
- result: FAIL
- pytest_summary: `27 failed, 8 passed, 1 warning in 1.63s`
- stdout_path: `03_需求与设计/02_开发计划/task_z032b_12_cand002_fix_stdout.txt`
- continued_after_fail: false
- rerun_performed: false

## 断言与门禁

- settlement_export_contract_addressed: true
- business_assertions_preserved: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- target_test_dirty_diff: true
- cached_after_run: empty
- diff_check_after_run: PASS
- B12 artifacts staged: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false

## FAIL Evidence

- 单次 pytest 已停止在 FAIL 状态。
- stdout 中记录的首个异常证据为 `TypeError: SubcontractSettlementExportTest._settlement_request_id() got an unexpected keyword argument 'quantity'`。
- 按任务约束，本轮 FAIL 后未继续修复、未诊断扩展、未重跑。
