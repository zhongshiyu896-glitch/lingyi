# TASK-Z027B-20-PREP-CAND003-FAILURE-DIAG 失败定位报告

## Input Evidence

- Candidate: `Z027-CAND-003`
- Source boundary task: `TASK-Z027B-18-PREP`
- Source impl task: `TASK-Z027B-19-IMPL`
- Current HEAD: `c46b8f5a74166eedf5cfac8c75bad232359a1f87`
- B19 result: FAIL
- Failed summary: `2 failed, 3 passed, 1 warning in 1.17s`
- `git diff --cached --name-only`: empty
- Target test dirty diff: []
- `git diff --check`: PASS

## Failed Cases

- `test_resource_level_forbidden_writes_resource_context`
  - Expected: 403
  - Observed: 422
  - Assertion: `self.assertEqual(explode_resp.status_code, 403)`
  - Test payload only sends `order_qty` and `size_ratio`.
  - Current `BomExplodeRequest` requires `scenario_tag`, `idempotency_key`, `source_ref`, `bom_no`, `item_code`, and `order_qty`.
- `test_workshop_resource_forbidden_writes_security_audit`
  - Expected: 403
  - Observed: 422
  - Assertion: `self.assertEqual(response.status_code, 403)`
  - Test payload omits current carrier fields.
  - Current `WorkshopTicketRegisterRequest` requires `scenario_tag`, `idempotency_key`, and `source_ref`.

## Diagnosis

The failures occur before the intended 403 security-audit assertions. Both requests are rejected by current schema/local gate contracts with 422 because the test fixture payloads are stale.

- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Allowed fix file: `07_后端/lingyi_service/tests/test_security_audit.py`
- Next task: `TASK-Z027B-21-FIX-CAND003`
- Run this task: NO

## Source Evidence

- `07_后端/lingyi_service/tests/test_security_audit.py`
- `07_后端/lingyi_service/app/services/permission_service.py`
- `07_后端/lingyi_service/app/services/audit_service.py`
- `07_后端/lingyi_service/app/routers/bom.py`
- `07_后端/lingyi_service/app/routers/workshop.py`
- `07_后端/lingyi_service/app/models/audit.py`
- `07_后端/lingyi_service/app/schemas/bom.py`
- `07_后端/lingyi_service/app/schemas/workshop.py`
- Source evidence missing: []

## Forbidden Actions

- Pytest/npm/browser/build/typecheck/verify: NO
- Code/test edits: NO
- Stage/commit/push/tag/PR/release: NO
- Cleanup/reset/checkout/stash: NO
- Production readback/go-live/project completion: NO
