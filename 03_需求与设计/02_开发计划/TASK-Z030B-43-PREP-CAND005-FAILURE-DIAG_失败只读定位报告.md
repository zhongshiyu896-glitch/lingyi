# TASK-Z030B-43-PREP-CAND005-FAILURE-DIAG 失败只读定位报告

## 核对结果

- 当前 HEAD: `d120175a8bd931bfe9e6f6d76a531364b48d778e`
- cached: 空
- `git diff --check`: PASS
- B42 result: FAIL
- B42 command_run_count: 1
- B42 pytest summary: `2 failed, 9 passed, 5 warnings in 1.04s`
- target_test_dirty_diff: false
- target test 当前无 dirty diff

## 失败摘要

failed_cases_count: 2

- `test_audit_failed_does_not_call_erp_and_rolls_back_outbox`: expected `500`, observed `422`, diff `422 != 500`
- `test_commit_failed_does_not_call_erp_and_rolls_back_outbox`: expected `500`, observed `422`, diff `422 != 500`

只读证据显示，目标测试 `_payload` 仍使用旧载体字段集合；当前 `WorkshopTicketRegisterRequest` 与 router local ticket write gate 需要 `scenario_tag`、`idempotency_key`、`batch_no` 等请求载体字段，导致请求在进入原 `500` 失败分支前被 schema/status gate 拦截为 `422`。

## 分类与边界

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed fix file: `07_后端/lingyi_service/tests/test_workshop_outbox.py`
- recommended next task: `TASK-Z030B-44-FIX-CAND005`
- run_this_task: false

## Readonly Source Evidence

- `03_需求与设计/02_开发计划/task_z030b_41_cand005_boundary.json`
- `03_需求与设计/02_开发计划/task_z030b_42_cand005_result.json`
- `03_需求与设计/02_开发计划/task_z030b_42_cand005_stdout.txt`
- `07_后端/lingyi_service/tests/test_workshop_outbox.py`
- `07_后端/lingyi_service/app/schemas/workshop.py`
- `07_后端/lingyi_service/app/routers/workshop.py`
- `07_后端/lingyi_service/app/services/workshop_outbox_service.py`
- `07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py`
- `07_后端/lingyi_service/app/models/workshop.py`
- `07_后端/lingyi_service/app/models/audit.py`

source_evidence_missing: []

## 禁止动作确认

- pytest/npm/browser/build/typecheck/verify: false
- stage/commit/push/tag/PR/release: false
- cleanup/reset/checkout/stash: false
- remote_lifecycle_parked: true
- production_readback_ready/go_live_ready/project_completion_claimed: false

本轮只做失败定位与修复边界冻结，未修改代码、测试、stdout、result、candidate pool 或既有归档产物。
