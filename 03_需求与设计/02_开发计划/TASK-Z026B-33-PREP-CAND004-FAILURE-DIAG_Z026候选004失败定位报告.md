# TASK-Z026B-33-PREP-CAND004-FAILURE-DIAG

## Scope

- Role: B Engineer
- Selected candidate: Z026-CAND-004
- Source result task: TASK-Z026B-32-IMPL
- Failed command: `.venv/bin/python -m pytest tests/test_subcontract_exception_handling.py -q`
- Failed summary: `9 failed, 1 passed, 1 warning in 1.15s`
- Run this task: NO

## Readonly Evidence

- `03_需求与设计/02_开发计划/task_z026b_32_cand004_result.json`
- `03_需求与设计/02_开发计划/task_z026b_32_cand004_stdout.txt`
- `07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`
- `07_后端/lingyi_service/app/routers/subcontract.py`
- `07_后端/lingyi_service/app/schemas/subcontract.py`
- `07_后端/lingyi_service/app/services/subcontract_service.py`
- `07_后端/lingyi_service/app/models/subcontract.py`

## Failed Cases

1. `test_create_subcontract_blank_company_returns_company_required_envelope`: status `422`, then `KeyError: code` because the response did not use the old custom error envelope.
2. `test_create_subcontract_null_company_returns_company_required_envelope`: status `422`, then `KeyError: code` for the same envelope drift.
3. `test_database_write_failed_mapping`: actual `422`, expected `500`.
4. `test_inspect_database_write_failure_returns_database_write_failed`: actual `409`, expected `500`.
5. `test_receive_database_write_failure_returns_database_write_failed`: actual `409`, expected `500`.
6. `test_service_create_order_does_not_commit_in_service_layer`: Pydantic validation failed before service execution because `SubcontractCreateRequest` now requires common write carrier fields.
7. `test_subcontract_fail_closed_logs_are_sanitized`: no expected ERROR log was emitted because the request failed before the patched runtime-error path.
8. `test_subcontract_no_fake_stock_entry_name_after_task_002b1`: actual `409`, expected `200`.
9. `test_unknown_exception_returns_subcontract_internal_error`: actual `409`, expected `500`.

## Diagnosis

The failures are consistent with test contract and fixture drift. Current subcontract write schemas require `SubcontractWriteCarrierBase` fields including `request_id`, `idempotency_key`, `scenario_tag`, `source_ref`, `subcontract_ref`, `supplier_ref`, `work_order_ref`, `operation`, `quantity`, and `status_action`. The router also validates `X-Request-ID` and carrier consistency, and the local-dev write gate requires `APP_ENV=development` plus `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`.

The existing test setup and payloads still reflect the older contract. They miss the current carrier payload/header requirements and local gate environment, so several cases stop at FastAPI/Pydantic `422` or router `409` before reaching the exception branches the tests intend to assert. The seeded receive/inspect fixtures also need to align with the current receive/inspect preconditions.

## Classification

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`
- recommended_next_task: `TASK-Z026B-34-FIX-CAND004`

No backend app source boundary is recommended by this evidence. The next step should update only the target test contract/fixtures so the cases reach their original exception assertions without weakening business semantics.

## Validation

- current_head: `1f0e1d7bf322cecc7f4d51e93491a282653e6ead`
- cached area before report write: empty
- `git diff --check`: PASS
- pytest rerun: NO
- code/test edits: NO
- stage/commit/push: NO
