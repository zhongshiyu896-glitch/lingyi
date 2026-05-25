# TASK-Z028B-04-PREP-CAND001-FAILURE-DIAG 失败定位报告

## Scope

- Role: B Engineer
- Candidate: `Z028-CAND-001`
- Source boundary task: `TASK-Z028B-02-PREP`
- Source impl task: `TASK-Z028B-03-IMPL`
- Current HEAD: `abe758cebfa5c3affde9e3632692402227ec80c0`
- Run this task: `false`

## B03 Failure

- Failed summary: `2 failed, 5 warnings in 1.12s`
- Failed cases:
  - `FactoryStatementConfirmCancelTest::test_cancel_allowed_when_only_failed_or_dead_outbox_exists`
  - `FactoryStatementConfirmCancelTest::test_cancel_blocked_when_pending_payable_outbox_exists`
- Expected statuses: `[200, 200]`
- Observed statuses: `[409, 409]`
- Failure point: both cases fail in `_create_confirmed_statement` before reaching the cancel assertions.

## Readonly Diagnosis

- `FactoryStatementApiBase._create_payload` already normalizes create `idempotency_key` with `scenario_tag` and includes `scenario_tag`.
- `FactoryStatementConfirmCancelTest._create_confirmed_statement` posts confirm with only `idempotency_key` and `remark`.
- `factory_statement` router confirm endpoint validates local write gate with `payload.idempotency_key` and `payload.scenario_tag`.
- The same confirm endpoint requires `company`, `supplier`, and `statement_no` to match the persisted statement header.
- `FactoryStatementConfirmRequest` schema already has `scenario_tag`, `company`, `supplier`, and `statement_no`; this is test payload/fixture contract drift, not evidence for a backend app fix.

## Classification

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_factory_statement_confirm_cancel.py`
- recommended_next_task: `TASK-Z028B-05-FIX-CAND001`

## Validation

- Cached area: empty.
- Target test dirty diff: false.
- Source evidence missing: `[]`.
- `git diff --check`: PASS.
- No pytest/npm/browser/build/typecheck/verify was run in this task.
- No files outside B04 evidence artifacts were modified.
- No stage/commit/push/tag/PR/release was performed.
