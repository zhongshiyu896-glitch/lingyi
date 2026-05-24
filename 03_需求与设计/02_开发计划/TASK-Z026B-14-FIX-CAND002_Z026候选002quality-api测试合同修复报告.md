# TASK-Z026B-14-FIX-CAND002 Z026候选002quality-api测试合同修复报告

## 范围

- 候选：`Z026-CAND-002`
- 来源任务：`TASK-Z026B-13-PREP-CAND002-FAILURE-DIAG`
- 允许修改文件：`07_后端/lingyi_service/tests/test_quality_api.py`
- 允许命令：`.venv/bin/python -m pytest tests/test_quality_api.py -q`

## 修复内容

- 为 quality API 测试 payload 补齐当前 schema/local gate 所需字段：`request_id`、`idempotency_key`、`scenario_tag`、`source_ref`、`inspection_ref`、`source_doc`、`operation`。
- 增加 request carrier 生成逻辑与 `X-Request-ID` 头，保持测试进入现有业务合同分支。
- 为 create、confirm、cancel、update、defects、permission denied 路径补齐结构化 payload。
- 未弱化原业务断言，未改为任意 2xx/4xx。
- 未 skip、xfail 或删除用例。

## 单次验证结果

- 命令：`.venv/bin/python -m pytest tests/test_quality_api.py -q`
- workdir：`07_后端/lingyi_service`
- 运行次数：1
- exit code：1
- 结果：FAIL
- pytest 摘要：`1 failed, 6 passed, 2 warnings in 1.15s`
- stdout：`03_需求与设计/02_开发计划/task_z026b_14_cand002_fix_stdout.txt`

## 剩余失败

- 失败用例：`tests/test_quality_api.py::QualityApiTest::test_cancelled_status_rejects_followup_writes`
- 失败模式：cancel action 返回 `409 QUALITY_INVALID_SOURCE`，消息为 `LOCAL_GATE_FAIL_CLOSED:non_local_dev`，仍早于目标 cancelled-state 断言分支。

## 停止原因

B14 任务只允许修改目标测试并运行单文件 pytest 一次。该唯一验证命令已执行且仍 FAIL，因此按任务要求停止，不继续修复、不重跑、不扩大范围。
