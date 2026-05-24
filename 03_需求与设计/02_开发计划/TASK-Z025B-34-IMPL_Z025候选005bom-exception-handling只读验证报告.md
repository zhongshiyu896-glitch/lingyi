# TASK-Z025B-34-IMPL Z025-CAND-005 bom-exception-handling 只读验证报告

## Scope

- Task ID: `TASK-Z025B-34-IMPL`
- Role: `B Engineer`
- Selected candidate: `Z025-CAND-005`
- Source boundary: `TASK-Z025B-33-PREP`
- Current HEAD: `2b68102d35be30f12b8accadf2aec935d5b57bdc`
- Workdir: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- Frozen command: `.venv/bin/python -m pytest tests/test_bom_exception_handling.py -q`
- Command run count: `1`

## Result

- Exit code: `1`
- Result: `FAIL`
- Pytest summary: `14 failed, 1 passed, 1 warning in 1.16s`
- Stdout log: `03_需求与设计/02_开发计划/task_z025b_34_cand005_stdout.txt`

## Failure Summary

The single allowed readonly pytest command failed. The recurring failure pattern is that requests returned HTTP `422` before the intended BOM exception envelope assertions for expected `500` or `409` cases.

Failed cases:

| Case | Expected | Actual | Key failure |
| --- | ---: | ---: | --- |
| `test_activate_bom_returns_database_write_failed_when_commit_raises` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_commit_failure_rollback_failure_does_not_override_database_write_failed` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_create_bom_returns_audit_write_failed_when_operation_audit_fails` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_create_bom_returns_database_write_failed_when_business_write_fails` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_create_bom_returns_database_write_failed_when_commit_raises` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_create_bom_returns_internal_error_when_unknown_runtime_error_occurs` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_deactivate_bom_returns_database_write_failed_when_commit_raises` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_set_default_conflict_returns_bom_default_conflict` | 409 | 422 | `AssertionError: 422 != 409` |
| `test_set_default_returns_database_write_failed_when_commit_raises` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_set_default_returns_default_conflict_when_commit_integrity_hits_partial_unique_index` | 409 | 422 | `AssertionError: 422 != 409` |
| `test_snapshot_resource_database_read_failed_returns_database_read_failed` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_snapshot_resource_unknown_error_returns_internal_error` | 500 | 422 | `AssertionError: 422 != 500` |
| `test_update_active_bom_returns_published_locked` | 409 | 422 | `AssertionError: 422 != 409` |
| `test_update_bom_returns_database_write_failed_when_commit_raises` | 500 | 422 | `AssertionError: 422 != 500` |

## Scope Guard

- Code/test edits: `NO`
- Fix attempt: `NO`
- Other tests/build/typecheck/npm/browser: `NO`
- Stage/commit/push/tag/PR/release: `NO`
- Reset/checkout/stash/cleanup: `NO`
- Production readback/go-live/project completion: `NO`
