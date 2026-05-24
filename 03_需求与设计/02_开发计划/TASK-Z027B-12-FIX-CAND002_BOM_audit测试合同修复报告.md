# TASK-Z027B-12-FIX-CAND002 BOM audit 测试合同修复报告

## Fix

- candidate_id: Z027-CAND-002
- source_failure_task: TASK-Z027B-11-PREP-CAND002-FAILURE-DIAG
- classification: TEST_CONTRACT_UPDATE_ALLOWED
- fixed_file: 07_后端/lingyi_service/tests/test_bom_audit.py
- contract_fixed: added current BOM create schema and local gate carriers to the failing audit test payload.
- assertions_preserved: true
- skip_xfail_deleted_cases: false
- backend_app_changed: false
- frontend_changed: false
- unrelated_tests_changed: false

## Validation

- command: .venv/bin/python -m pytest tests/test_bom_audit.py -q
- workdir: /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
- command_run_count: 1
- exit_code: 0
- result: PASS
- pytest_summary: 2 passed, 1 warning in 1.02s
- stdout_log: 03_需求与设计/02_开发计划/task_z027b_12_cand002_fix_stdout.txt
- cached_empty: true
- git_diff_check: PASS

## Preserved Assertions

1. self.assertEqual(response.status_code, 500)
2. self.assertEqual(payload_json.get("code"), AUDIT_WRITE_FAILED)
3. self.assertIsNone(payload_json.get("data"))
4. self.assertEqual(self._count_bom_rows(), before_count)

## Scope Note

- This task changed only the allowed target test plus allowed B12 evidence artifacts.
- The repository has pre-existing dirty paths outside this task scope; they were not modified, staged, or cleaned by this task.

## Forbidden Actions

- stage/commit/push/tag/PR/release: NO
- other pytest/npm/browser/build/typecheck/verify: NO
- cleanup/reset/checkout/stash: NO
- production readback/go-live/project completion: NO
