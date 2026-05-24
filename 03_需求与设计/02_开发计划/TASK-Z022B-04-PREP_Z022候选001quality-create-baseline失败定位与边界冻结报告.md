# TASK-Z022B-04-PREP Z022-CAND-001 quality-create-baseline 失败定位与边界冻结报告

## Failure Evidence

- selected_candidate_id: Z022-CAND-001
- command: `.venv/bin/python -m pytest tests/test_quality_create_baseline.py -q`
- result: FAIL
- exit_code: 1
- pytest_summary: `2 failed, 1 warning in 0.95s`
- failed_tests:
  - `QualityCreateBaselineTest.test_post_create_requires_permission`: expected `403`, actual `422`
  - `QualityCreateBaselineTest.test_post_create_returns_201_and_draft`: expected `201`, actual `422`
- missing_fields: `request_id`, `idempotency_key`, `scenario_tag`, `source_ref`, `inspection_ref`, `operation`

## Readonly Localization

- `tests/test_quality_create_baseline.py:24-35` and `:46-57` call `self._payload()` without the current create request carrier fields, then assert business status codes.
- `app/schemas/quality.py:38-47` defines `QualityInspectionCreateRequest` and makes `request_id`, `idempotency_key`, `scenario_tag`, `source_ref`, `inspection_ref`, and `operation` required.
- `app/routers/quality.py:590-625` binds the endpoint body to `QualityInspectionCreateRequest` before permission/service execution.
- `app/services/quality_service.py:182-220` create logic receives an already validated `QualityInspectionCreateRequest`; the observed 422 prevents this service path from being reached.

## Conclusion

- failure_classification: TEST_CONTRACT_UPDATE_ALLOWED
- reason: The test contract payload is stale relative to the current required request schema. The failure is not enough evidence for a product implementation defect because request validation rejects the body before router permission checks or service creation logic run.
- allowed_fix_files:
  - `07_后端/lingyi_service/tests/test_quality_create_baseline.py`
- recommended_next_task_id: TASK-Z022B-05-FIX
- single_regression_command: `.venv/bin/python -m pytest tests/test_quality_create_baseline.py -q`
- run_this_task: false

## Gate State

- stage_allowed: false
- commit_allowed: false
- push_allowed: false
- project_completion_claimed: false

## Forbidden Actions

- 本轮未运行 pytest/npm/browser/build/typecheck/verify。
- 本轮未修改源码、测试、依赖或配置文件。
- 本轮未 stage/commit/push/PR/tag/release。
- 本轮未 cleanup/kill 本地服务。
- 本轮未释放 parked blockers，未声明项目完成。
