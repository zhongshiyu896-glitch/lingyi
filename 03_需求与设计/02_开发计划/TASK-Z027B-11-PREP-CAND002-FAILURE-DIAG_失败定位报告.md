# TASK-Z027B-11-PREP-CAND002-FAILURE-DIAG 失败定位报告

## Diagnosis

- candidate_id: Z027-CAND-002
- source_boundary_task: TASK-Z027B-09-PREP
- source_impl_task: TASK-Z027B-10-IMPL
- failed_summary: 1 failed, 1 passed, 1 warning in 1.05s
- failed_case: tests/test_bom_audit.py::BomAuditBehaviorTest::test_operation_audit_failure_returns_audit_write_failed_and_rolls_back
- observed_status: 422
- expected_status: 500
- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: 07_后端/lingyi_service/tests/test_bom_audit.py
- next_task: TASK-Z027B-12-FIX-CAND002
- run_this_task: false

## Evidence

- B10 stdout shows `AssertionError: 422 != 500` at `self.assertEqual(response.status_code, 500)`.
- The failing test payload in `test_bom_audit.py` posts to `/api/bom/` without `scenario_tag`, `idempotency_key`, or `source_ref`.
- `app/schemas/bom.py` defines `BomCreateRequest` with required `scenario_tag`, `idempotency_key`, and `source_ref`.
- `app/routers/bom.py` binds `POST /api/bom/` to `BomCreateRequest` and then validates local request carriers before calling `BomService.create_bom` and audit handling.
- Therefore the request is rejected at schema validation with 422 before reaching the intended `AuditWriteFailed` 500 branch.

## Source Evidence

1. 03_需求与设计/02_开发计划/task_z027b_09_cand002_boundary.json
2. 03_需求与设计/02_开发计划/task_z027b_10_cand002_result.json
3. 03_需求与设计/02_开发计划/task_z027b_10_cand002_stdout.txt
4. 07_后端/lingyi_service/tests/test_bom_audit.py
5. 07_后端/lingyi_service/app/routers/bom.py
6. 07_后端/lingyi_service/app/schemas/bom.py
7. 07_后端/lingyi_service/app/services/bom_service.py
8. 07_后端/lingyi_service/app/services/audit_service.py
9. 07_后端/lingyi_service/app/models/bom.py
10. 07_后端/lingyi_service/app/core/error_codes.py

## Gates

- current_head: d924557791f94d151d805797b4a4be8ee298f0cb
- cached_empty: true
- target_test_dirty_diff: []
- source_evidence_missing: []
- git_diff_check: PASS
- pytest_run: false
- fix_attempt: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback_performed: false
- go_live_performed: false
- project_completion_claimed: false
