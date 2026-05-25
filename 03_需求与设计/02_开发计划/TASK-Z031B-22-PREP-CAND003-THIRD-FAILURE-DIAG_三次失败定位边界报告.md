# TASK-Z031B-22-PREP-CAND003-THIRD-FAILURE-DIAG 三次失败定位边界报告

## 只读核对

- task_id: TASK-Z031B-22-PREP-CAND003-THIRD-FAILURE-DIAG
- role: B Engineer
- source_task: TASK-Z031B-21-FIX-CAND003-SECOND
- candidate_id: Z031-CAND-003
- current_head: 23c9a5068daa6cca8a7071f4e4ce2def52bb6a7f
- cached_empty: true
- git_diff_check_pass: true
- B21 result: FAIL
- B21 command_run_count: 1
- B21 pytest_summary: 1 failed, 4 passed, 1 warning in 1.07s
- target_test: 07_后端/lingyi_service/tests/test_style_profit_api_errors.py
- current_target_dirty_diff_limited_to_allowed_file: true
- source_evidence_missing: []
- historical_dirty_forbidden_staged: []

## 剩余失败

| remaining_failed_case | observed | expected | status |
| --- | --- | --- | --- |
| test_blank_sales_order_returns_business_error | 500 | 400 | still explicitly asserts `STYLE_PROFIT_SALES_ORDER_REQUIRED` |

## 失败模式

B21 后唯一剩余失败为 blank sales order 业务错误用例，当前断言仍是显式 `400` 与 `STYLE_PROFIT_SALES_ORDER_REQUIRED`，不接受 `409` 或 `500`。

只读 diff 显示，当前目标测试的 gate carrier helper 直接把 `payload["sales_order"]` 转为字符串回填。blank 用例把 payload 改为 `"   "` 后，helper 将该空白字符串写回 `gate_carriers["sales_order"]`。只读 router 证据显示，路由会先 strip normalized payload，但随后 `normalized_payload.update(gate_carriers)` 会以 gate carrier 覆盖前置 strip 结果，因此空白 sales_order 未进入原 Pydantic `400` 分支。

该问题仍可在授权目标测试内通过 fixture/payload/mock 调整，使 blank sales order 进入原 `400` 业务错误分支，无需修改 backend app。

## 边界冻结

- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: 07_后端/lingyi_service/tests/test_style_profit_api_errors.py
- next_task: TASK-Z031B-23-FIX-CAND003-THIRD
- run_this_task: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false

本轮未运行 pytest/npm/browser/build/typecheck/verify，未修改代码/测试/stdout/result/既有 evidence，未 stage/commit/push/tag/PR/release，未 cleanup/reset/checkout/stash。
