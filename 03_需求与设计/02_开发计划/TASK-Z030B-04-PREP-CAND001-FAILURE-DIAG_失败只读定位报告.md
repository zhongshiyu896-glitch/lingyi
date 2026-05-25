# TASK-Z030B-04-PREP-CAND001-FAILURE-DIAG 失败只读定位报告

- task_id: TASK-Z030B-04-PREP-CAND001-FAILURE-DIAG
- role: B Engineer
- source_task: TASK-Z030B-03-IMPL
- candidate_id: Z030-CAND-001
- current_head: 52d00a349ae810cb9cb5c3f1c44ad52122f6f812
- cached_empty: true
- git_diff_check: PASS
- b03_result: FAIL
- b03_command_run_count: 1
- b03_pytest_summary: 3 failed, 4 passed, 1 warning in 0.43s
- target_test_dirty_diff: false

## 失败摘要

- failed_cases_count: 3
- failed_cases:
  - `QualityAutoTriggerTest.test_auto_trigger_creates_draft_quality_inspection`
  - `QualityAutoTriggerTest.test_duplicate_event_is_idempotent`
  - `QualityAutoTriggerTest.test_source_validation_failure_does_not_create_draft`
- observed_failure: `pydantic_core._pydantic_core.ValidationError`
- missing_schema_fields: `request_id`, `idempotency_key`, `scenario_tag`, `source_ref`, `inspection_ref`, `operation`
- failure_site: `app/services/quality_purchase_receipt_listener.py:179`
- schema_contract_site: `app/schemas/quality.py:38`

## 分类

- classification: BLOCK_BACKEND_APP_SCHEMA_PAYLOAD_DRIFT_REQUIRES_APP_FIX_AUTHORIZATION
- allowed_fix_file: null
- recommended_next_task: null
- run_this_task: false

理由：B03 失败发生在 backend listener 内部构造 `QualityInspectionCreateRequest` 时，目标测试调用的是 `handle_purchase_receipt_event(...)`。缺失字段属于 backend app 内部 payload 构造与当前 schema 合同不一致；在仅允许修改 `test_quality_auto_trigger.py` 的前提下，无法通过 fixture/payload 调整补齐该内部构造字段而不改变测试语义。

## Readonly Source Evidence

- 07_后端/lingyi_service/tests/test_quality_auto_trigger.py
- 07_后端/lingyi_service/app/services/quality_purchase_receipt_listener.py
- 07_后端/lingyi_service/app/schemas/quality.py
- 07_后端/lingyi_service/app/services/quality_service.py
- 07_后端/lingyi_service/app/models/quality.py
- 07_后端/lingyi_service/app/models/quality_outbox.py
- source_evidence_missing: []

## 禁止动作

- pytest/npm/browser/build/typecheck/verify: not run
- files_modified_outside_evidence: false
- stage_performed: false
- commit_performed: false
- push_performed: false
- tag_performed: false
- pr_performed: false
- release_performed: false
- cleanup/reset/checkout/stash: false
- remote_lifecycle_parked: true
- production_readback_ready: false
- go_live_ready: false
- project_completion_claimed: false
