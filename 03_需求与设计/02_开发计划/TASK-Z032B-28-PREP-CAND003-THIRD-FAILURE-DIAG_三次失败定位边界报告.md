# TASK-Z032B-28-PREP-CAND003-THIRD-FAILURE-DIAG 三次失败定位边界报告

- TASK_ID: TASK-Z032B-28-PREP-CAND003-THIRD-FAILURE-DIAG
- ROLE: B Engineer
- source_task: TASK-Z032B-27-FIX-CAND003-SECOND
- candidate_id: Z032-CAND-003
- target_test: `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`

## 只读核对

- HEAD: `f1ee52224ea1a4615db30f51cb234eba023b1fb8`
- cached: empty
- `git diff --check`: PASS
- B27 result: FAIL
- B27 command_run_count: 1
- B27 pytest_summary: `6 failed, 1 warning in 1.00s`
- B27 `idempotency_carrier_conflict_gate_addressed`: false
- B27 stdout: 6 个失败用例均可追溯
- 当前目标测试 dirty diff: limited to `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`
- historical dirty forbidden paths: not staged

## 剩余失败差异

- `test_audit_write_failed_returns_500_not_failed_items`: observed `409`, expected `500`
- `test_database_write_failed_returns_500_not_failed_items`: observed `409`, expected `500`
- `test_permission_source_unavailable_returns_503_not_failed_items`: observed `409`, expected `503`
- `test_row_business_error_can_enter_failed_items`: observed `409`, expected `200`
- `test_row_resource_forbidden_can_enter_failed_items_and_write_security_audit`: observed `409`, expected `200`
- `test_unknown_error_returns_500_not_failed_items`: observed `409`, expected `500`

## Source Evidence

- `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`: exists
- `07_后端/lingyi_service/app/routers/workshop.py`: exists
- `07_后端/lingyi_service/app/services/workshop_service.py`: exists
- `07_后端/lingyi_service/app/schemas/workshop.py`: exists
- `07_后端/lingyi_service/app/models/workshop.py`: exists
- `07_后端/lingyi_service/app/services/permission_service.py`: exists
- source_evidence_missing: []

## Failure Pattern

B25 已将旧 payload schema validation `422` 推进到 workshop local request/carrier gate。B27 后 6 个用例仍全部 observed `409`，阻断原 `500/503/200` 业务分支。只读 source evidence 显示该 gate 仍属于目标测试 fixture/payload/local-state/request carrier 合同问题，可继续在授权目标测试内调整以进入原业务分支。

## 冻结分类

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_workshop_batch_exceptions.py`
- next_task: `TASK-Z032B-29-FIX-CAND003-THIRD`
- run_this_task: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false
