# TASK-Z034B-13-PREP-CAND002-FAILURE-DIAG 失败定位边界报告

## 基本信息

- cycle_id: Z034
- candidate_id: Z034-CAND-002
- source_task: TASK-Z034B-12-IMPL
- current_head: `a9768a57aceffedde0b2004cacaf498c2fe7c953`
- cached_empty: true
- git diff --check: PASS
- B12 result: FAIL
- B12 command_run_count: 1
- B12 pytest_summary: `2 failed, 10 passed, 1 warning in 1.14s`

## 失败用例

| failed_case | observed | expected | assertion |
| --- | --- | --- | --- |
| `StyleProfitApiPermissionTest.test_forbidden_create_takes_precedence_over_client_source_forbidden` | `response.status_code == 409` | `response.status_code == 403` | `tests/test_style_profit_api_permissions.py:146` |
| `StyleProfitApiPermissionTest.test_forbidden_create_takes_precedence_over_invalid_idempotency` | `response.status_code == 409` | `response.status_code == 403` | `tests/test_style_profit_api_permissions.py:166` |

## 失败模式摘要

- failed_cases_count: 2
- 两个失败均发生在 create endpoint permission precedence 用例。
- B12 stdout 显示 observed `409` vs expected `403`，阻断了后续 `AUTH_FORBIDDEN` code 断言。
- 目标测试中两个失败 payload 分别使用固定 idempotency key 或 invalid idempotency key 场景，当前结果先进入 idempotency conflict gate。
- 该失败模式符合目标测试内 stale test contract / local fixture / idempotency payload isolation drift，可在目标测试内修复，不需要修改 backend app。

## 分类与下一步边界

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_style_profit_api_permissions.py`
- recommended_next_task: `TASK-Z034B-14-FIX-CAND002`
- target_test_dirty_diff: false
- source_evidence_missing: []
- historical_dirty_forbidden_staged: []
- log_control_dirty_staged: []
- Z033 CAND003 skipped-only risk preserved: true (`skipped_only_evidence=true`, `actual_passed_count=0`, `skipped_count=4`)

## 生命周期

- run_this_task: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false
- B14 generated: false
- CAND003 started: false
