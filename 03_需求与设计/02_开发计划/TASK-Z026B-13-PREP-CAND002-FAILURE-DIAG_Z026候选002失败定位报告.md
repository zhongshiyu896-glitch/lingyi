# TASK-Z026B-13-PREP-CAND002-FAILURE-DIAG Z026候选002失败定位报告

## Scope

- Role: B Engineer
- Selected candidate: Z026-CAND-002
- Source result task: TASK-Z026B-12-IMPL
- Current HEAD: `f57cffd1983e958ecfaed4731174756398b19655`
- Failed command: `.venv/bin/python -m pytest tests/test_quality_api.py -q`
- Failed summary: `3 failed, 4 passed, 1 warning in 1.12s`
- Run this task: NO

## Diagnosis

- Failed cases count: 3
- Failure pattern: `TEST_PAYLOAD_CONTRACT_DRIFT_TO_CURRENT_QUALITY_SCHEMA_GATE`
- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Allowed fix file: `07_后端/lingyi_service/tests/test_quality_api.py`
- Recommended next task: `TASK-Z026B-14-FIX-CAND002`

## Failed Cases

- `test_create_endpoint_returns_201_with_draft`: actual 422 before create branch; missing `request_id`, `idempotency_key`, `scenario_tag`, `source_ref`, `inspection_ref`, `operation`.
- `test_cancelled_status_rejects_followup_writes`: confirm setup actual 422 before confirm branch; missing `request_id`, `idempotency_key`, `scenario_tag`, `source_ref`, `inspection_ref`, `source_type`, `item_code`, `operation`, `result`.
- `test_action_permission_denied_before_frozen_response`: actual 422 before expected 403 permission assertion because create payload is still the legacy payload.

## Readonly Source Evidence

- `03_需求与设计/02_开发计划/task_z026b_12_cand002_result.json`
- `03_需求与设计/02_开发计划/task_z026b_12_cand002_stdout.txt`
- `07_后端/lingyi_service/tests/test_quality_api.py`
- `07_后端/lingyi_service/app/routers/quality.py`
- `07_后端/lingyi_service/app/schemas/quality.py`
- `07_后端/lingyi_service/app/services/quality_service.py`
- `07_后端/lingyi_service/app/models/quality.py`

## Rationale

The current quality schemas require request and idempotency fields before the router write branches execute. The failing tests still send legacy create/action payloads, so FastAPI returns 422 before the original permission, create, confirm, cancel, and invalid-status assertions can be reached. The evidence supports a test contract update only; no business source change is indicated.

## Validation

- Cached area: empty
- `git diff --check`: PASS

## Forbidden Actions

- Code/test edits: NO
- Tests/build/typecheck/npm/browser run: NO
- Stage/commit/push/tag/PR/release: NO
- Reset/checkout/stash/cleanup: NO
- Production readback/go-live/project completion: NO
