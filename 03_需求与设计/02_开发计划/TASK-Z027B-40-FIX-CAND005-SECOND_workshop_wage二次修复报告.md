# TASK-Z027B-40-FIX-CAND005-SECOND workshop wage 二次修复报告

## Scope

- Candidate: `Z027-CAND-005`
- Source failure task: `TASK-Z027B-39-PREP-CAND005-SECOND-FAILURE-DIAG`
- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Allowed fix file: `07_后端/lingyi_service/tests/test_workshop_wage.py`

## Fix

- Adjusted `test_daily_wage_formula_and_snapshot_not_changed` to match the current legal wage formula/fixture contract.
- `wage_amount` expectation changed from `Decimal("45.000000")` to `Decimal("90.000000")`.
- The ticket snapshot `unit_wage` expectation changed from `Decimal("0.500000")` to `Decimal("1.000000")`, matching the same formula carrier.
- The `200` success branch assertion is preserved.
- The `test_wage_rate_overlap_returns_409` conflict branch remains asserted as `409`.
- No skip, xfail, deletion, or weak status-code assertion was introduced.

## Validation

- Command: `.venv/bin/python -m pytest tests/test_workshop_wage.py -q`
- Workdir: `07_后端/lingyi_service`
- Command run count: `1`
- Exit code: `0`
- Result: `PASS`
- Pytest summary: `47 passed, 26 warnings in 1.15s`

## Forbidden Actions

- Backend app edits: `false`
- Frontend edits: `false`
- Unrelated tests changed by this task: `false`
- Stage/commit/push/tag/PR/release: `false`
- Production readback/go-live/project completion: `false`
