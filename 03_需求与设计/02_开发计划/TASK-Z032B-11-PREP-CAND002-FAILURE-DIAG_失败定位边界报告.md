# TASK-Z032B-11-PREP-CAND002-FAILURE-DIAG 失败定位边界报告

- source task：TASK-Z032B-10-IMPL
- candidate_id：Z032-CAND-002
- current_head：bbc298a8e2423ea51d82de66ed058835182bcade
- cached：empty
- `git diff --check`：PASS
- B10 result：FAIL
- B10 command_run_count：1
- B10 pytest summary：26 failed, 9 passed, 1 warning in 1.51s
- failed_cases_count：26
- target_test：`07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
- target_test_dirty_diff：false
- source_evidence_missing：[]

## Failure Pattern

26 个失败集中在 `settlement-preview`、`settlement-locks`、`settlement-locks/release` 的旧测试 payload 未携带当前 subcontract settlement carrier 字段，当前 router 在 `_validate_subcontract_settlement_gate` 处提前返回 422，阻断原 `200/409/500` 业务分支。`test_settlement_operation_record_is_append_only` 的 `0 != 2` 为同一 422 gate 导致 lock/release 操作未落表的后续差异。

## Boundary

- classification：TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file：`07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
- next_task：TASK-Z032B-12-FIX-CAND002
- run_this_task：false

## Gates

- stage：false
- commit：false
- push：false
- tag：false
- PR：false
- release：false
- remote_lifecycle_parked：true
- production_readback：false
- go_live：false
- project_completion：false
- B11 本轮产物 staged：false
