# TASK-Z031B-18-PREP-CAND003-FAILURE-DIAG 失败定位边界报告

## 只读核对

- task_id: TASK-Z031B-18-PREP-CAND003-FAILURE-DIAG
- role: B Engineer
- current_head: 23c9a5068daa6cca8a7071f4e4ce2def52bb6a7f
- cached_empty: true
- git_diff_check_pass: true
- candidate_id: Z031-CAND-003
- source_task: TASK-Z031B-17-IMPL
- B17 result: FAIL
- B17 command_run_count: 1
- B17 pytest_summary: 5 failed, 1 warning in 1.08s
- target_test: 07_后端/lingyi_service/tests/test_style_profit_api_errors.py
- target_test_dirty_diff: false
- source_evidence_missing: []
- historical_dirty_forbidden_staged: []

## 失败用例与差异

| failed_case | observed | expected | summary |
| --- | --- | --- | --- |
| tests/test_style_profit_api_errors.py::StyleProfitApiErrorTest::test_blank_sales_order_returns_business_error | 409 | 400 | local write gate idempotency conflict returned before sales_order business validation |
| tests/test_style_profit_api_errors.py::StyleProfitApiErrorTest::test_commit_failure_returns_database_write_failed | 409 | 500 | local write gate idempotency conflict returned before DatabaseWriteFailed branch |
| tests/test_style_profit_api_errors.py::StyleProfitApiErrorTest::test_invalid_idempotency_key_returns_business_error | 409 | 400 | local write gate idempotency conflict returned before invalid idempotency validation branch |
| tests/test_style_profit_api_errors.py::StyleProfitApiErrorTest::test_same_idempotency_key_with_different_request_returns_conflict | 409 | 200 | first request was rejected before the expected successful setup for later idempotency conflict |
| tests/test_style_profit_api_errors.py::StyleProfitApiErrorTest::test_unknown_error_uses_unified_envelope_without_detail | 409 | 500 | local write gate idempotency conflict returned before unknown error envelope branch |

## 失败模式

B17 stdout 中 5 个失败均可追溯为断言状态码差异，observed 均为 409。target test 的 `_base_create_payload` 只包含 company、item_code、sales_order、from_date、to_date、revenue_mode、include_provisional_subcontract、formula_version、idempotency_key。当前 router 的 local style-profit write gate 在进入原业务分支前要求 request_id 与 payload carrier 对齐，并要求 payload 提供 scenario_tag、source_ref、status_action 等载体字段，同时要求 idempotency_key 与 scenario_tag 对齐。

因此失败模式是测试合同/fixture payload 未跟随当前本地写入 gate 的 carrier contract 漂移，导致所有用例在原 400/200/500 分支前统一被 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT` 拦截。

## 边界冻结

- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: 07_后端/lingyi_service/tests/test_style_profit_api_errors.py
- next_task: TASK-Z031B-19-FIX-CAND003
- run_this_task: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false

本轮未运行 pytest/npm/browser/build/typecheck/verify，未修改代码/测试/stdout/result/既有 evidence，未 stage/commit/push/tag/PR/release，未 cleanup/reset/checkout/stash。
