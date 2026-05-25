# TASK-Z031B-20-PREP-CAND003-SECOND-FAILURE-DIAG 二次失败定位边界报告

## 只读核对

- task_id: TASK-Z031B-20-PREP-CAND003-SECOND-FAILURE-DIAG
- role: B Engineer
- source_task: TASK-Z031B-19-FIX-CAND003-FIX1
- candidate_id: Z031-CAND-003
- current_head: 23c9a5068daa6cca8a7071f4e4ce2def52bb6a7f
- cached_empty: true
- git_diff_check_pass: true
- B19 C audit: AUDIT_RESULT: FIX
- B19-FIX1 result: FAIL
- B19-FIX1 command_run_count: 1
- B19-FIX1 pytest_summary: 2 failed, 3 passed, 1 warning in 1.05s
- target_test: 07_后端/lingyi_service/tests/test_style_profit_api_errors.py
- current_target_dirty_diff_limited_to_allowed_file: true
- source_evidence_missing: []
- historical_dirty_forbidden_staged: []

## 剩余失败

| remaining_failed_case | observed | expected | status |
| --- | --- | --- | --- |
| tests/test_style_profit_api_errors.py::StyleProfitApiErrorTest::test_invalid_idempotency_key_returns_business_error | 500 | 400 | assertion restored to `STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY` |
| tests/test_style_profit_api_errors.py::StyleProfitApiErrorTest::test_blank_sales_order_returns_business_error | 500 | 400 | assertion restored to `STYLE_PROFIT_SALES_ORDER_REQUIRED` |

## 失败模式

FIX1 已把两个业务错误用例恢复为显式 `400` 与业务错误码断言，且不再接受 `409 STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。当前剩余失败为 observed `500` vs expected `400`。

只读源码证据显示，router 在 local write gate 之后会执行 `normalized_payload.update(gate_carriers)` 并立即读取 `gate_carriers["sales_order"]`。当前目标测试 dirty diff 中，两个业务错误用例将 `_validate_local_style_profit_write_gate` mock 为 `return_value={}`，mock carrier 形状不完整，仍会在目标业务校验前触发非预期 `500`。

该失败仍可在目标测试内通过 fixture/mock 调整推进到原 `400` 业务错误分支，无需修改 backend app。

## 边界冻结

- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: 07_后端/lingyi_service/tests/test_style_profit_api_errors.py
- next_task: TASK-Z031B-21-FIX-CAND003-SECOND
- run_this_task: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false

本轮未运行 pytest/npm/browser/build/typecheck/verify，未修改代码/测试/stdout/result/既有 evidence，未 stage/commit/push/tag/PR/release，未 cleanup/reset/checkout/stash。
