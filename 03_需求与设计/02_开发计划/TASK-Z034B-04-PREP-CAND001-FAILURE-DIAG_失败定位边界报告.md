# TASK-Z034B-04-PREP-CAND001-FAILURE-DIAG 失败定位边界报告

## 只读核对

- 当前 HEAD: `6bc20b833e3780e2bd10549a2ce906ee860941cb`
- cached: empty
- `git diff --check`: PASS
- B03 result: FAIL
- B03 command_run_count: 1
- B03 pytest summary: `4 failed, 6 passed, 1 warning in 1.12s`
- target test: `07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
- target test dirty diff: false
- B02/B03 Z033 CAND003 skipped-only 风险: retained (`skipped_only_evidence=true`, `actual_passed_count=0`, `skipped_count=4`)

## 失败用例

| case | observed | expected | location |
| --- | --- | --- | --- |
| `test_create_collector_fail_closed_writes_operation_audit_failure` | HTTP 409 | HTTP 503 | `tests/test_style_profit_api_audit.py:165` |
| `test_create_failure_writes_operation_audit_failure` | HTTP 409 | HTTP 400 | `tests/test_style_profit_api_audit.py:199` |
| `test_create_rejected_client_source_rows_writes_operation_audit_failure` | HTTP 409 | HTTP 400 | `tests/test_style_profit_api_audit.py:131` |
| `test_create_success_writes_operation_audit` | HTTP 409 | HTTP 200 | `tests/test_style_profit_api_audit.py:42` |

## 模式判断

- failed_cases_count: 4
- failure_pattern_summary: all four create-endpoint audit tests stop at HTTP 409 before entering intended `200/400/503` audit branches.
- category: `test_contract_drift`
- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
- recommended_next_task: `TASK-Z034B-05-FIX-CAND001`

## 边界

- source_evidence_missing: []
- run_this_task: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false
