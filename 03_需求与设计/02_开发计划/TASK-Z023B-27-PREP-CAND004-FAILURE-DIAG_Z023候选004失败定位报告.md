# TASK-Z023B-27-PREP-CAND004-FAILURE-DIAG Z023候选004失败定位报告

## 定位结论

- selected_candidate_id：Z023-CAND-004
- source_task_id：TASK-Z023B-26-IMPL
- b26_result：FAIL
- b26_pytest_summary：13 failed, 5 passed, 1 warning in 1.15s
- failed_case_count：13
- dominant_actual_status_codes：422、409
- dominant_error_codes：REQUEST_VALIDATION_422、SUBCONTRACT_STOCK_OUTBOX_CONFLICT
- failure_classification：TEST_CONTRACT_UPDATE_ALLOWED

## 失败来源

- create 路径使用 `SubcontractCreateRequest` 作为 endpoint body schema，缺失 carrier 字段时在权限分支前返回 422。
- receive / inspect 路径先 `_parse_receive_payload` / `_parse_inspect_payload`，再进入本地与 carrier gate；当前测试 payload 不满足 `ReceiveRequest` / `InspectRequest` 继承的 carrier 合同，实际返回 409 `SUBCONTRACT_STOCK_OUTBOX_CONFLICT`。
- `SubcontractWriteCarrierBase` 当前必填字段为：`request_id`、`idempotency_key`、`scenario_tag`、`source_ref`、`subcontract_ref`、`supplier_ref`、`work_order_ref`、`operation`、`item_code`、`quantity`、`status_action`。
- 当前 subcontract gate 要求 `scenario_tag` 匹配 `Z003-SUBCONTRACT-\d{8}-\d{3}`，并要求 `X-Request-ID` 与 payload carrier 一致。
- 本地写 gate 还要求 `APP_ENV=development` 且 `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`。

## 范围核对

- backend_app_dirty_for_candidate：NO
- target_test_dirty_before_task：NO
- 权限 service / adapter 断言语义未稳定进入；当前失败先落在 schema、payload、local gate 或 carrier gate。
- 业务源码无需在本边界内修改；下一步只允许修复目标测试合同。

## 下一步边界

- allowed_fix_files：07_后端/lingyi_service/tests/test_subcontract_permissions.py
- forbidden_files：06_前端；07_后端/lingyi_service/app；工程师共享日志；Z015-Z022 产物；Z023-CAND-001/002/003 产物；Z023 candidate pool / B24 / B25 / B26 产物；A/C 记录；GitHub/生产配置
- recommended_next_task_id：TASK-Z023B-28-FIX-CAND004
- recommended_next_command：.venv/bin/python -m pytest tests/test_subcontract_permissions.py -q
- run_pytest_this_task：NO
- allow_code_edit_next：YES，仅限 allowed_fix_files

## 禁止动作确认

- pytest/npm/browser/build/typecheck/verify：NO
- product/backend/test edits：NO
- existing artifact edits：NO
- engineer shared log edit：NO
- stage/commit/push：NO
- reset/checkout/cleanup：NO
- PR/tag/release：NO
- production account / ERPNext production / real business write：NO
- parked blockers released：NO
- project completion claimed：NO
