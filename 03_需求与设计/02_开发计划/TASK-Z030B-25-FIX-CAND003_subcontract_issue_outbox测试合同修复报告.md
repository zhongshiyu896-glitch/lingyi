# TASK-Z030B-25-FIX-CAND003 测试合同修复报告

- task_id: TASK-Z030B-25-FIX-CAND003
- role: B Engineer
- candidate_id: Z030-CAND-003
- source_task: TASK-Z030B-24-PREP-CAND003-FAILURE-DIAG
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_issue_outbox.py`

## 修改范围

- changed_files:
  - `07_后端/lingyi_service/tests/test_subcontract_issue_outbox.py`
  - `03_需求与设计/02_开发计划/TASK-Z030B-25-FIX-CAND003_subcontract_issue_outbox测试合同修复报告.md`
  - `03_需求与设计/02_开发计划/task_z030b_25_cand003_fix_result.json`
  - `03_需求与设计/02_开发计划/task_z030b_25_cand003_fix_result.tsv`
  - `03_需求与设计/02_开发计划/task_z030b_25_cand003_fix_stdout.txt`

目标测试补齐 subcontract issue-material 当前写入 carrier/schema payload 字段，并设置本地写入门禁所需测试环境。保留原 `200/400/409` 显式业务状态断言。

## 验证

- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_subcontract_issue_outbox.py -q`
- command_run_count: 1
- exit_code: 0
- result: PASS
- pytest_summary: `9 passed, 16 warnings in 1.10s`
- stdout_path: `03_需求与设计/02_开发计划/task_z030b_25_cand003_fix_stdout.txt`

## 断言与范围门禁

- schema_payload_contract_addressed: true
- business_status_assertions_preserved: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- backend_app_changed: false
- frontend_changed: false
- shared_log_changed: false
- candidate_pool_changed: false
- unrelated_tests_changed: false
- cached_empty: true
- git diff --check: PASS
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false
