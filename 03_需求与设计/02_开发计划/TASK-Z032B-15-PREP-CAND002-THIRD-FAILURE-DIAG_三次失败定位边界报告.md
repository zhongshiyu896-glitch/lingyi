# TASK-Z032B-15-PREP-CAND002-THIRD-FAILURE-DIAG 三次失败定位边界报告

- task_id: TASK-Z032B-15-PREP-CAND002-THIRD-FAILURE-DIAG
- role: B Engineer
- source_task: TASK-Z032B-14-FIX-CAND002-SECOND
- candidate_id: Z032-CAND-002
- current_head: `bbc298a8e2423ea51d82de66ed058835182bcade`
- cached: empty
- git_diff_check: PASS
- B14 result: FAIL
- B14 command_run_count: 1
- B14 pytest_summary: `26 failed, 9 passed, 1 warning in 1.54s`
- previous_failed_cases_count: 27
- remaining_failed_cases_count: 26
- helper_type_error_resolved: true

## 只读核对

- target_test: `07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
- current_target_dirty_diff_limited_to_allowed_file: true
- current_target_dirty_diff_summary: `1 file changed, 129 insertions(+)`
- B14 business_assertions_preserved: true
- B14 assertions_weakened: false
- B14 skip_xfail_deleted_cases: false
- source_evidence_missing: []
- historical_dirty_forbidden_staged: []

## 剩余失败模式

B14 stdout 不再出现 `_settlement_request_id()` unexpected `quantity` TypeError。剩余 26 个失败均已发出 HTTP 请求，但响应仍停在 `409`，其中可见错误码为 `SUBCONTRACT_STOCK_OUTBOX_CONFLICT`，未进入原 settlement preview/lock/release 的 `200/409/500` 业务分支或对应业务错误码断言。

该模式仍指向目标测试内 settlement carrier/payload/helper 合同未完全对齐当前 router gate。未见 backend app 修改或后端缺陷证据，因此冻结为继续 test-contract 修复。

## 边界结论

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_settlement_export.py`
- next_task: `TASK-Z032B-16-FIX-CAND002-THIRD`
- run_this_task: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false

## 26 个失败差异摘要

1. `test_no_erpnext_write_called_by_settlement_export_or_lock`: observed 409; expected lock branch 200.
2. `test_settlement_duplicate_unique_conflict_different_hash_returns_conflict`: observed first lock 409; expected first lock 200.
3. `test_settlement_duplicate_unique_conflict_does_not_create_second_operation`: observed initial lock 409; expected initial lock 200.
4. `test_settlement_duplicate_unique_conflict_does_not_mutate_inspection_again`: observed initial lock 409; expected initial lock 200.
5. `test_settlement_first_lock_sets_idempotent_replay_false`: observed first lock 409; expected first lock 200.
6. `test_settlement_first_release_sets_idempotent_replay_false`: observed initial lock 409; expected initial lock 200.
7. `test_settlement_idempotency_key_accepts_128_chars`: observed lock 409; expected lock 200.
8. `test_settlement_lock_conflicts_for_other_statement`: observed code `SUBCONTRACT_STOCK_OUTBOX_CONFLICT`; expected `SUBCONTRACT_SETTLEMENT_ALREADY_LOCKED`.
9. `test_settlement_lock_duplicate_unique_conflict_replays_first_response`: observed first lock 409; expected first lock 200.
10. `test_settlement_lock_is_idempotent_for_same_statement`: observed first lock 409; expected first lock 200.
11. `test_settlement_lock_marks_inspections_statement_locked`: observed lock 409; expected lock 200.
12. `test_settlement_lock_release_then_old_lock_retry_does_not_relock`: observed first lock 409; expected first lock 200.
13. `test_settlement_lock_replay_sets_idempotent_replay_true`: observed initial lock 409; expected initial lock 200.
14. `test_settlement_lock_rolls_back_all_rows_on_failure`: observed code `SUBCONTRACT_STOCK_OUTBOX_CONFLICT`; expected `SUBCONTRACT_SETTLEMENT_ALREADY_LOCKED`.
15. `test_settlement_operation_record_is_append_only`: observed operation rows 0; expected 2.
16. `test_settlement_operation_write_failure_rolls_back_lock`: observed 409; expected 500.
17. `test_settlement_operation_write_failure_rolls_back_release`: observed initial lock 409; expected initial lock 200.
18. `test_settlement_preview_does_not_use_old_amount_formula`: observed preview 409; expected preview 200.
19. `test_settlement_preview_sums_inspection_amount_facts`: observed preview 409; expected preview 200.
20. `test_settlement_release_duplicate_unique_conflict_replays_first_response`: observed initial lock 409; expected initial lock 200.
21. `test_settlement_release_rejects_settled_rows`: observed code `SUBCONTRACT_STOCK_OUTBOX_CONFLICT`; expected `SUBCONTRACT_SETTLEMENT_STATUS_INVALID`.
22. `test_settlement_release_replay_sets_idempotent_replay_true`: observed initial lock 409; expected initial lock 200.
23. `test_settlement_release_retry_returns_first_result_without_mutation`: observed initial lock 409; expected initial lock 200.
24. `test_settlement_release_unlocks_statement_locked_rows`: observed lock 409; expected lock 200.
25. `test_settlement_request_id_is_not_used_as_idempotency_history`: observed first lock 409; expected first lock 200.
26. `test_settlement_same_idempotency_key_different_payload_conflicts`: observed first lock 409; expected first lock 200.
