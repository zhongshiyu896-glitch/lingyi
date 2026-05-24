# TASK-Z026B-15-PREP-CAND002-SECOND-FAILURE-DIAG Z026候选002二次失败定位报告

## 范围

- 候选：`Z026-CAND-002`
- 来源结果任务：`TASK-Z026B-14-FIX-CAND002`
- 当前允许脏文件：`07_后端/lingyi_service/tests/test_quality_api.py`
- 本轮只读定位，不运行 pytest，不修改测试。

## B14 剩余失败

- 失败摘要：`1 failed, 6 passed, 2 warnings in 1.15s`
- 剩余失败用例：`tests/test_quality_api.py::QualityApiTest::test_cancelled_status_rejects_followup_writes`
- 实际响应：`409 QUALITY_INVALID_SOURCE`
- 错误消息：`LOCAL_GATE_FAIL_CLOSED:non_local_dev`
- 关键断言：`self.assertEqual(cancel.status_code, 200, cancel.text)`

## 只读证据

- `task_z026b_14_cand002_fix_result.json` 记录 B14 单次验证仍 FAIL。
- `task_z026b_14_cand002_fix_stdout.txt` 显示 cancel 请求在目标 cancelled-state 断言前被 local gate 拦截。
- `test_quality_api.py` 当前 dirty diff 已补齐 schema payload、request carrier、`X-Request-ID`，并为 create/confirm 包装 local gate env。
- `app/routers/quality.py` 中 `_validate_quality_gate_common()` 先调用 `_ensure_local_dev_write_gate()`；`_write_existing()` 在 confirm/cancel/update/defects 进入 service 前都会调用 `_validate_quality_existing_gate()`。
- `app/schemas/quality.py` 显示 confirm/cancel/update/defects 均要求 schema carrier 字段。
- `app/services/quality_service.py` 显示 confirm/cancel 的状态转换逻辑仍在业务 service 内，当前失败尚未到达该业务分支。

## 诊断

B14 已处理最初的 422 schema validation 漂移，并使 create 与 confirm 路径进入当前合同。但 `test_cancelled_status_rejects_followup_writes` 中 confirm 请求之后，cancel 请求离开了 `patch.dict("os.environ", self._local_gate_env())` 上下文；router 在进入 service 前执行 `_ensure_local_dev_write_gate()`，因此返回 `LOCAL_GATE_FAIL_CLOSED:non_local_dev`。

该剩余失败仍属于测试合同/fixture 环境边界更新，未指向后端 app 业务源码缺陷。

## 边界冻结

- classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- allowed fix file：`07_后端/lingyi_service/tests/test_quality_api.py`
- recommended next task：`TASK-Z026B-16-FIX-CAND002-SECOND`
- run_this_task：NO
