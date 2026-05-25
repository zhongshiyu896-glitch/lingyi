# TASK-Z032B-13-PREP-CAND002-SECOND-FAILURE-DIAG 二次失败定位边界报告

- task_id: TASK-Z032B-13-PREP-CAND002-SECOND-FAILURE-DIAG
- role: B Engineer
- source_task: TASK-Z032B-12-FIX-CAND002
- candidate_id: Z032-CAND-002
- current_head: `bbc298a8e2423ea51d82de66ed058835182bcade`
- cached: empty
- git_diff_check: PASS
- B12 result: FAIL
- B12 command_run_count: 1
- B12 pytest_summary: `27 failed, 8 passed, 1 warning in 1.63s`
- previous_failed_cases_count: 26
- remaining_failed_cases_count: 27

## 只读核对

- target_test: `07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
- current_target_dirty_diff_limited_to_allowed_file: true
- current_target_dirty_diff_summary: `1 file changed, 128 insertions(+)`
- B12 business_assertions_preserved: true
- B12 assertions_weakened: false
- B12 skip_xfail_deleted_cases: false
- source_evidence_missing: []
- historical_dirty_forbidden_staged: []

## 剩余失败模式

B12 stdout 中 27 个失败均可追溯，且均在测试侧 helper `_post_with_settlement_contract` 调用 `_settlement_request_id(**carrier)` 时触发同一异常：

`TypeError: SubcontractSettlementExportTest._settlement_request_id() got an unexpected keyword argument 'quantity'`

该失败发生在发出 HTTP 请求前，未进入 settlement preview/lock/release 的原业务分支，也未改变后端行为证据。证据支持继续在授权目标测试内修正 fixture/payload/mock/测试合同 helper，使原 `200/409/500/422` 业务断言重新到达后端分支。

## 边界结论

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
- next_task: `TASK-Z032B-14-FIX-CAND002-SECOND`
- run_this_task: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false

## 27 个失败差异摘要

1. `test_no_erpnext_write_called_by_settlement_export_or_lock`: observed TypeError before HTTP response; expected lock branch status 200.
2. `test_settlement_duplicate_unique_conflict_different_hash_returns_conflict`: observed TypeError before HTTP response; expected first lock status 200.
3. `test_settlement_duplicate_unique_conflict_does_not_create_second_operation`: observed TypeError before HTTP response; expected initial lock status 200.
4. `test_settlement_duplicate_unique_conflict_does_not_mutate_inspection_again`: observed TypeError before HTTP response; expected initial lock status 200.
5. `test_settlement_first_lock_sets_idempotent_replay_false`: observed TypeError before HTTP response; expected first lock status 200.
6. `test_settlement_first_release_sets_idempotent_replay_false`: observed TypeError before HTTP response; expected initial lock status 200.
7. `test_settlement_idempotency_key_accepts_128_chars`: observed TypeError before HTTP response; expected lock status 200.
8. `test_settlement_idempotency_key_rejects_over_128_chars`: observed TypeError before HTTP response; expected validation status 422.
9. `test_settlement_lock_conflicts_for_other_statement`: observed TypeError before HTTP response; expected second lock status 409.
10. `test_settlement_lock_duplicate_unique_conflict_replays_first_response`: observed TypeError before HTTP response; expected first lock status 200.
11. `test_settlement_lock_is_idempotent_for_same_statement`: observed TypeError before HTTP response; expected first and replay lock status 200.
12. `test_settlement_lock_marks_inspections_statement_locked`: observed TypeError before HTTP response; expected lock status 200.
13. `test_settlement_lock_release_then_old_lock_retry_does_not_relock`: observed TypeError before HTTP response; expected first lock status 200.
14. `test_settlement_lock_replay_sets_idempotent_replay_true`: observed TypeError before HTTP response; expected initial lock status 200.
15. `test_settlement_lock_rolls_back_all_rows_on_failure`: observed TypeError before HTTP response; expected lock status 409.
16. `test_settlement_operation_record_is_append_only`: observed TypeError before lock/release calls; expected two operation rows.
17. `test_settlement_operation_write_failure_rolls_back_lock`: observed TypeError before HTTP response; expected lock branch status 500.
18. `test_settlement_operation_write_failure_rolls_back_release`: observed TypeError before HTTP response; expected initial lock status 200.
19. `test_settlement_preview_does_not_use_old_amount_formula`: observed TypeError before HTTP response; expected preview status 200.
20. `test_settlement_preview_sums_inspection_amount_facts`: observed TypeError before HTTP response; expected preview status 200.
21. `test_settlement_release_duplicate_unique_conflict_replays_first_response`: observed TypeError before HTTP response; expected initial lock status 200.
22. `test_settlement_release_rejects_settled_rows`: observed TypeError before HTTP response; expected release status 409.
23. `test_settlement_release_replay_sets_idempotent_replay_true`: observed TypeError before HTTP response; expected initial lock status 200.
24. `test_settlement_release_retry_returns_first_result_without_mutation`: observed TypeError before HTTP response; expected release status 200.
25. `test_settlement_release_unlocks_statement_locked_rows`: observed TypeError before HTTP response; expected lock status 200.
26. `test_settlement_request_id_is_not_used_as_idempotency_history`: observed TypeError before HTTP response; expected first/replay lock status 200.
27. `test_settlement_same_idempotency_key_different_payload_conflicts`: observed TypeError before HTTP response; expected first lock status 200 and second lock status 409.
