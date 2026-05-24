# TASK-Z025B-36-FIX-CAND005 Z025-CAND-005 bom-exception-handling 测试合同修复报告

## Scope

- Task ID: `TASK-Z025B-36-FIX-CAND005`
- Role: `B Engineer`
- Selected candidate: `Z025-CAND-005`
- Source task: `TASK-Z025B-35-PREP-CAND005-FAILURE-DIAG`
- Fixed file: `07_后端/lingyi_service/tests/test_bom_exception_handling.py`
- Failure classification: `TEST_CONTRACT_UPDATE_ALLOWED`

## Fix

Only the allowed target test file was modified.

Contract changes:

- Added the local BOM scenario tag and request-id carrier helper used by the router local gate.
- Set `LINGYI_DB_URL` to the local allowed SQLite URL for the target test environment.
- Filled required `BomCreateRequest` and `BomUpdateRequest` fields so create/update requests no longer stop at HTTP `422`.
- Added required carrier request bodies for `activate`, `set-default`, and `deactivate` endpoints.
- Aligned the seeded BOM and mocked snapshot fixtures with the current `item_code` and `bom_no` carrier checks.

Assertions were not weakened. No test was skipped, xfailed, or deleted.

## Validation

- Command: `.venv/bin/python -m pytest tests/test_bom_exception_handling.py -q`
- Workdir: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- Command run count: `1`
- Exit code: `0`
- Result: `PASS`
- Pytest summary: `15 passed, 1 warning in 1.09s`
- Stdout log: `03_需求与设计/02_开发计划/task_z025b_36_cand005_fix_stdout.txt`

## Scope Guard

- Backend app edits: `NO`
- Frontend edits: `NO`
- Unrelated tests edits: `NO`
- Other tests/build/typecheck/npm/browser: `NO`
- Stage/commit/push/tag/PR/release: `NO`
- Reset/checkout/stash/cleanup: `NO`
- Production readback/go-live/project completion: `NO`
