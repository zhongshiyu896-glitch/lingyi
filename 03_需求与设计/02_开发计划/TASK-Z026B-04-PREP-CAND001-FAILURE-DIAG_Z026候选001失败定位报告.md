# TASK-Z026B-04-PREP-CAND001-FAILURE-DIAG Z026-CAND-001 失败定位报告

## 基本信息

- 角色: B Engineer
- 候选: Z026-CAND-001
- 来源结果任务: TASK-Z026B-03-IMPL
- 当前 HEAD: 7624199bcfaaf3ed80c185e1949fd82845c27c76
- 失败命令: `.venv/bin/python -m pytest tests/test_factory_statement_audit.py -q`
- 失败摘要: `4 failed, 4 passed, 15 warnings in 1.16s`

## 失败用例

- `FactoryStatementAuditTest::test_cancel_blocked_by_active_payable_outbox_writes_failure_audit`: confirm request expected 200 but returned 409 at `tests/test_factory_statement_audit.py:326`.
- `FactoryStatementAuditTest::test_confirm_and_cancel_success_audit_rows_exist`: confirm request expected 200 but returned 409 at `tests/test_factory_statement_audit.py:167`.
- `FactoryStatementAuditTest::test_payable_idempotency_conflict_writes_failure_audit`: confirm request expected 200 but returned 409 at `tests/test_factory_statement_audit.py:258`.
- `FactoryStatementAuditTest::test_payable_permission_denied_writes_failure_audit`: confirm request expected 200 but returned 409 at `tests/test_factory_statement_audit.py:214`.

## 只读定位

- B03 stdout 显示 4 个失败均发生在前置 confirm 请求，实际状态码为 409，尚未进入各用例后续 audit/payable/cancel 断言。
- `app/routers/factory_statement.py` 的 confirm 路径在调用 service 前执行 `_validate_local_factory_statement_write_gate`，并校验 `payload.idempotency_key`、`payload.scenario_tag`、`company`、`supplier`、`statement_no` 等链路载体。
- `tests/test_factory_statement_audit.py` 中失败用例的 confirm payload 仍只传 `idempotency_key` 与 `remark`，属于旧测试合同。
- `tests/test_factory_statement_api.py` 的 shared helper 已有 `_SCENARIO_TAG` 与 create payload 的 scenario_tag 模式，可作为目标测试文件内补齐 confirm/payable/cancel payload 合同的依据。
- service/model 只读核对未显示需要修改业务源码才能解释该 409；当前失败是测试 payload/fixture 与路由合同不匹配。

## 分类与边界

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed fix file: `07_后端/lingyi_service/tests/test_factory_statement_audit.py`
- recommended next task: `TASK-Z026B-05-FIX-CAND001`
- run_this_task: NO

## 范围声明

- 未修改 `06_前端`。
- 未修改任何 `07_后端` 文件。
- 未修改共享工程师日志。
- 未修改 Z026 candidate pool、B02 boundary、B03 result/stdout 或既有产物。
- 未运行 pytest、npm、browser、build、typecheck、verify。
- 未 stage、commit、push、tag、PR、release。
- 未 reset、checkout、stash、cleanup。
- 未进行 production readback、go-live 或项目完成声明。
