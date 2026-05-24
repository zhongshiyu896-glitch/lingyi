# TASK-Z023B-04-PREP-CAND001-FAILURE-DIAG Z023-CAND-001 失败定位报告

## 范围

- 任务角色：B Engineer
- 来源任务：TASK-Z023B-03-IMPL
- 选定候选：Z023-CAND-001
- 当前 HEAD：`ba1b3f6c8105af836c3bde132a692d626b708025`
- 本轮仅只读定位失败并冻结下一步边界；未运行 pytest/npm/browser/build/typecheck/verify，未修改源码/测试/配置，未 stage/commit/push。

## B03 失败确认

- result：FAIL
- pytest summary：`1 failed, 7 passed, 13 warnings in 1.03s`
- failed case：`tests/test_factory_statement_permissions.py::FactoryStatementPermissionTest::test_no_payable_draft_permission_returns_403_and_no_outbox`
- expected status：`200`
- actual status：`409`

B03 stdout 只捕获了状态断言，没有打印响应体。结合当前路由源码，`409` 对应 confirm 路由中 local gate 抛出的 `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。

## 只读定位

失败用例在 `07_后端/lingyi_service/tests/test_factory_statement_permissions.py:215-229` 中：

- 先用 `_create_payload()` 创建 draft，创建 helper 在 `tests/test_factory_statement_api.py:124-137` 中会补齐合法 `scenario_tag` 并把 scenario tag 拼入 create idempotency key。
- 随后 confirm 预置步骤直接发送 `json={"idempotency_key": "idem-no-payable-confirm", "remark": "ok"}`。
- 该 confirm payload 缺少 `scenario_tag`、`company`、`supplier`、`statement_no`，且 `idempotency_key` 不包含合法 `Z003-FACTORY-STMT-\d{8}-\d{3}` scenario tag。

当前 confirm 路由在 `app/routers/factory_statement.py:460-524` 中的顺序是：

- `permission_service.require_action(...)`
- header lookup
- `_validate_local_factory_statement_write_gate(...)`
- `_ensure_chain_match(...)`
- `ensure_factory_statement_resource_permission(...)`
- `service.confirm_statement(...)`

local gate 定义在 `app/routers/factory_statement.py:186-223`，会检查 `X-Request-ID` 与 `payload.idempotency_key`、`payload.scenario_tag` 这些 carrier 的 scenario tag 是否一致。当前 confirm payload 第一个 carrier 即 `idem-no-payable-confirm`，无法匹配合法 scenario tag，先于资源权限、状态分支和 payable-draft 权限断言触发 409 fail-closed。

## 边界冻结

- failure_classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_files：`07_后端/lingyi_service/tests/test_factory_statement_permissions.py`
- recommended_next_task_id：`TASK-Z023B-05-FIX-CAND001`
- recommended_next_command：`.venv/bin/python -m pytest tests/test_factory_statement_permissions.py -q`
- run_pytest_this_task：NO
- allow_code_edit_next：YES，仅限 allowed fix file

## Dirty Diff 核对

- `test_factory_statement_permissions.py` 当前不在 dirty diff 中。
- CAND001 相关 backend app 文件当前无 dirty diff。
- `07_后端/lingyi_service/app` 下存在历史 dirty diff：`app/schemas/report.py`、`app/services/report_catalog_service.py`、`app/services/system_config_catalog_service.py`，与本候选 factory_statement 路径无关，本轮未修改。

## Forbidden Actions

- pytest/npm/browser/build/typecheck/verify：NO
- product/backend app/test edits：NO
- existing artifact edits：NO
- engineer shared log edit：NO
- stage/commit/push：NO
- reset/checkout/cleanup：NO
- PR/tag/release：NO
- production account / ERPNext production / real business write：NO
- parked blockers released：NO
- project completion claimed：NO
