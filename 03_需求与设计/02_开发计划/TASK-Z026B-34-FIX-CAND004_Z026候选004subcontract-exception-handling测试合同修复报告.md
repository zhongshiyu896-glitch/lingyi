# TASK-Z026B-34-FIX-CAND004

## Scope

- Role: B Engineer
- Selected candidate: Z026-CAND-004
- Source task: TASK-Z026B-33-PREP-CAND004-FAILURE-DIAG
- Allowed fix file: `07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`
- Allowed command: `.venv/bin/python -m pytest tests/test_subcontract_exception_handling.py -q`

## Fix

Updated only `test_subcontract_exception_handling.py` to align the write-path tests with the current subcontract request contract:

- Added current write-carrier payload helpers.
- Added `X-Request-ID` carrier header generation.
- Set local development write-gate environment for this local SQLite test scope.
- Updated create, receive, inspect, and service-level payload construction so the tests reach the intended exception branches instead of stopping at schema validation or local gate checks.

No backend app source was edited. No frontend file was edited. No unrelated test file was edited. No skip, xfail, or failing case deletion was introduced.

## Validation

- Command run count: 1
- Command: `.venv/bin/python -m pytest tests/test_subcontract_exception_handling.py -q`
- Exit code: 1
- Result: FAIL
- Pytest summary: `1 failed, 9 passed, 7 warnings in 1.14s`
- Stdout log: `03_需求与设计/02_开发计划/task_z026b_34_cand004_fix_stdout.txt`

Remaining failure:

- `test_subcontract_no_fake_stock_entry_name_after_task_002b1`
- Assertion: expected `stock_entry_name` to be `None`
- Actual: `LOCAL-RECEIPT-SRB-51-20260524191707103052`

Per task instructions, no further fix attempt or rerun was performed after this FAIL result.

## Git Scope

- Changed test file: `07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`
- Cached area: empty
- `git diff --check`: PASS
- Stage/commit/push/tag/PR/release: NO
