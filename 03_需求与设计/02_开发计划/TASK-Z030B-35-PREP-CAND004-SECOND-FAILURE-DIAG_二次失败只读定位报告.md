# TASK-Z030B-35-PREP-CAND004-SECOND-FAILURE-DIAG 二次失败只读定位报告

## 输入核对

- current_head: `d892457a8612122c70ef96e851f72e418baa37b9`
- cached_empty: true
- git_diff_check: PASS
- source_task: `TASK-Z030B-34-FIX-CAND004`
- candidate_id: `Z030-CAND-004`
- B34 result: FAIL
- B34 command_run_count: 1
- B34 pytest_summary: `2 failed, 13 passed, 41 warnings in 1.15s`
- B34 assertions_weakened: false
- B34 skip_xfail_deleted_cases: false

## 剩余失败

- remaining_failed_cases_count: 2
- `test_receive_creates_receipt_rows_and_pending_outbox`
  - expected: `data["sync_status"] == "pending"` and `stock_entry_name is None`
  - observed: `data["sync_status"] == "succeeded"`
- `test_receive_returns_outbox_without_fake_stock_entry_name`
  - expected: `payload["stock_entry_name"] is None`
  - observed: `LOCAL-RECEIPT-SRB-1-20260525121250222151`

## 二次定位

- B34 目标测试 diff 仅限授权目标测试的 payload/carrier 合同补齐范围。
- 当前 `SubcontractService.receive` 在 local development + sqlite local DB 条件下启用 local-dev sync substitute。
- 该分支将 receipt/outbox `sync_status` 设为 `succeeded`，并写入 `LOCAL-RECEIPT-{receipt_batch_no}` 形式的 `stock_entry_name`。
- 因此 B34 剩余失败不是 payload/carrier gate 阻断，而是目标测试仍断言旧的 `pending`/`None` outbox 合同。

## 结论

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_receive_outbox.py`
- recommended_next_task: `TASK-Z030B-36-FIX-CAND004-SECOND`
- source_evidence_missing: []
- run_this_task: false
- 未运行 pytest/npm/browser/build/typecheck/verify。
- 未修改代码、测试、stdout/result。
- 未 stage/commit/push/tag/PR/release。
