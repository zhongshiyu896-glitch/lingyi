# TASK-Z025B-35-PREP-CAND005-FAILURE-DIAG Z025-CAND-005 失败定位报告

## Scope

- Task ID: `TASK-Z025B-35-PREP-CAND005-FAILURE-DIAG`
- Role: `B Engineer`
- Selected candidate: `Z025-CAND-005`
- Source result task: `TASK-Z025B-34-IMPL`
- Current HEAD: `2b68102d35be30f12b8accadf2aec935d5b57bdc`
- Failed command: `.venv/bin/python -m pytest tests/test_bom_exception_handling.py -q`
- Failed summary: `14 failed, 1 passed, 1 warning in 1.16s`

## Readonly Evidence

- B34 result JSON: `03_需求与设计/02_开发计划/task_z025b_34_cand005_result.json`
- B34 stdout: `03_需求与设计/02_开发计划/task_z025b_34_cand005_stdout.txt`
- Target test: `07_后端/lingyi_service/tests/test_bom_exception_handling.py`
- BOM router: `07_后端/lingyi_service/app/routers/bom.py`
- BOM schema: `07_后端/lingyi_service/app/schemas/bom.py`
- BOM service: `07_后端/lingyi_service/app/services/bom_service.py`
- BOM model: `07_后端/lingyi_service/app/models/bom.py`

## Failed Cases

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

## Diagnosis

The remaining evidence supports `TEST_CONTRACT_UPDATE_ALLOWED`.

The observed failures are all HTTP `422`, so the requests fail validation before the intended BOM exception classification paths are reached. The target test helpers are still using older request contracts:

- `_headers()` omits `X-Request-ID`, which the local BOM write gate validates after request body parsing.
- `_create_payload()` omits `scenario_tag`, `idempotency_key`, and `source_ref`, all required by `BomCreateRequest`.
- `_update_payload()` omits `scenario_tag`, `idempotency_key`, `source_ref`, `bom_no`, and `item_code`, all required by `BomUpdateRequest`.
- `activate` and `set-default` test calls omit the JSON body required by `BomCarrierRequest`.
- `deactivate` sends only `reason`, while `BomDeactivateRequest` requires the carrier fields plus `reason`.

The router and service evidence indicates the business exception envelopes still exist behind the request validation and local carrier gate. No product semantics or backend app source decision is required for this boundary.

## Frozen Boundary

- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Allowed fix file: `07_后端/lingyi_service/tests/test_bom_exception_handling.py`
- Recommended next task: `TASK-Z025B-36-FIX-CAND005`
- Run this task: `NO`

## Forbidden Actions Observed

- Code/test edits: `NO`
- Pytest/npm/browser/build/typecheck/verify run: `NO`
- Stage/commit/push/tag/PR/release: `NO`
- Reset/checkout/stash/cleanup: `NO`
- Production readback/go-live/project completion: `NO`
