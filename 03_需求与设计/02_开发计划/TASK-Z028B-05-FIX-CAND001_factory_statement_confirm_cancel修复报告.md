# TASK-Z028B-05-FIX-CAND001 factory_statement_confirm_cancel 修复报告

## Scope

- Role: B Engineer
- Candidate: `Z028-CAND-001`
- Source failure task: `TASK-Z028B-04-PREP-CAND001-FAILURE-DIAG`
- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Fixed file: `07_后端/lingyi_service/tests/test_factory_statement_confirm_cancel.py`

## Fix

- Added scoped idempotency helper for current factory-statement `scenario_tag`.
- Added statement scope helper to carry `scenario_tag`, `company`, `supplier`, `statement_no`, and `source_type`.
- Updated confirm payload to include current scenario/idempotency and chain fields.
- Updated payable-draft payload to include current scenario/idempotency, `source_ref`, `source_type`, and `status_action`.
- Updated cancel payloads to include current scenario/idempotency and chain fields while retaining the original branch assertions.

## Validation

- Command: `.venv/bin/python -m pytest tests/test_factory_statement_confirm_cancel.py -q`
- Workdir: `07_后端/lingyi_service`
- Command run count: 1
- Exit code: 0
- Result: PASS
- Pytest summary: `2 passed, 10 warnings in 1.10s`
- Stdout log: `03_需求与设计/02_开发计划/task_z028b_05_cand001_fix_stdout.txt`

## Assertion And Scope Checks

- Confirm status remains asserted as `200`.
- Pending payable outbox cancel remains asserted as `409` with `FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE`.
- Failed payable outbox cancel remains asserted as `200` with response code `0`.
- No skip/xfail was added.
- No test case was deleted.
- No backend app, frontend, or unrelated test file was changed.
- Cached area remained empty.
- `git diff --check`: PASS.
- No stage/commit/push/tag/PR/release was performed.
