# TASK-Z028B-13-PREP-CAND002-FAILURE-DIAG 失败定位报告

## Diagnosis

- Candidate: `Z028-CAND-002`
- Source boundary task: `TASK-Z028B-11-PREP`
- Source impl task: `TASK-Z028B-12-IMPL`
- Failed summary: `5 failed, 7 passed, 29 warnings in 1.18s`
- Expected statuses: `[200, 200, 200, 200, 200]`
- Observed statuses: `[409, 409, 409, 409, 409]`

## Failed Cases

- `FactoryStatementIdempotencyTest::test_cancel_same_key_different_payload_conflict`
- `FactoryStatementIdempotencyTest::test_cancel_same_key_same_hash_replays_same_operation`
- `FactoryStatementIdempotencyTest::test_confirm_concurrent_same_idempotency_key_replays_without_duplicate_operation`
- `FactoryStatementIdempotencyTest::test_confirm_same_key_different_payload_conflict`
- `FactoryStatementIdempotencyTest::test_confirm_same_key_same_hash_replays_same_operation`

## Readonly Evidence

- Target test operation payloads still pass only plain `idempotency_key` and `remark` or `reason` for confirm/cancel calls.
- `FactoryStatementConfirmRequest` and `FactoryStatementCancelRequest` support `scenario_tag`, `company`, `supplier`, and `statement_no`.
- The confirm router validates `scenario_carriers=[payload.idempotency_key, payload.scenario_tag]` before calling `FactoryStatementService.confirm_statement`.
- The cancel router validates `scenario_carriers=[payload.idempotency_key, payload.scenario_tag, payload.reason]` before calling `FactoryStatementService.cancel_statement`.
- Current `409` therefore occurs before the old service idempotency replay/conflict assertions can reach their expected `200` branch.

## Boundary

- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Allowed fix file: `07_后端/lingyi_service/tests/test_factory_statement_idempotency.py`
- Next task: `TASK-Z028B-14-FIX-CAND002`
- Source evidence missing: []
- Historical dirty forbidden staged: []
- Run this task: NO

## Gates

- Cached empty: YES
- `git diff --check`: PASS
- Pytest/build/typecheck/npm/browser: NO
- Stage/commit/push/tag/PR/release: NO
- Reset/checkout/stash/cleanup: NO
- Remote lifecycle parked: YES
- Production readback/go-live/project completion: NO
