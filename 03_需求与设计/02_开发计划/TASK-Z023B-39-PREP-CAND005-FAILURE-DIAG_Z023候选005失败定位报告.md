# TASK-Z023B-39-PREP-CAND005-FAILURE-DIAG

## Scope

- Role: B Engineer
- Candidate: Z023-CAND-005
- Source task: TASK-Z023B-38-IMPL-CAND005
- Current HEAD: `8ee67f9c24073a43530b0fd7ee95e4a88dcfb640`
- This task did not run pytest, edit code, edit the target test, stage, commit, push, tag, release, or clean the worktree.

## B38 Failure Readback

- Result: FAIL
- Pytest summary: `5 failed, 8 passed, 1 warning in 1.00s`
- Failed cases:
  - `test_company_only_user_cannot_create_item_wage_rate`: expected `403`, actual `422`, no application `code` observed from the failure evidence.
  - `test_item_allowed_but_company_forbidden_returns_403`: expected `403`, actual `422`, no application `code` observed from the failure evidence.
  - `test_wage_rate_create_rejects_empty_company_for_item_rate`: expected `422` with `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED`, actual `422` without `code`.
  - `test_wage_rate_create_rejects_whitespace_company_for_item_rate`: expected `422` with `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED`, actual `422` without `code`.
  - `test_wage_rate_create_requires_company_for_item_specific_rate`: expected `422` with `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED`, actual `422` without `code`.

## Readonly Diagnosis

The failed tests all call `POST /api/workshop/wage-rates`. The current target test payloads include wage-rate business fields such as `item_code`, `company`, `process_name`, `wage_rate`, `effective_from`, and `effective_to`, but omit the carrier fields now required by `OperationWageRateCreateRequest`: `scenario_tag`, `idempotency_key`, and `source_ref`.

Readonly source evidence shows the route binds `payload: OperationWageRateCreateRequest` before entering router permission and service branches. After schema binding, the router calls `_validate_local_wage_request_id_gate(...)`, which also expects `X-Request-ID` and carrier values to share a valid workshop wage scenario tag and business carrier codes. Because the target test payloads do not satisfy the schema carrier contract, the failing requests return FastAPI/Pydantic `422` before the intended permission, local gate, or `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED` service assertions can run.

The current dirty backend app paths are historical report-related files, not workshop wage router/schema/service files. The target test file was not dirty before this task.

## Boundary

- Failure classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Allowed fix file: `07_后端/lingyi_service/tests/test_workshop_wage_permissions.py`
- Recommended next task: `TASK-Z023B-40-FIX-CAND005`
- Recommended command for the next task only: `.venv/bin/python -m pytest tests/test_workshop_wage_permissions.py -q`
- This task did not run that command.

The next fix should keep the original permission, company validation, audit, and no-create semantics, while updating only the target test request payload/carrier helper to meet the current workshop wage schema and local gate contract.
