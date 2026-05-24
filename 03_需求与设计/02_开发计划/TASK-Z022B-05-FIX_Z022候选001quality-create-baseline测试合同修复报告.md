# TASK-Z022B-05-FIX Z022-CAND-001 quality-create-baseline 测试合同修复报告

- 任务：TASK-Z022B-05-FIX
- 角色：B Engineer
- 源任务：TASK-Z022B-04-PREP
- 候选：Z022-CAND-001
- failure_classification：TEST_CONTRACT_UPDATE_ALLOWED
- 唯一允许修改文件：`07_后端/lingyi_service/tests/test_quality_create_baseline.py`

## 修复内容

- 在 `QualityCreateBaselineTest` 内新增 `_create_payload()`，基于现有 `_payload()` 补齐当前 schema 必填字段：
  - `request_id`
  - `idempotency_key`
  - `scenario_tag`
  - `source_ref`
  - `inspection_ref`
  - `operation`
- 两个原失败用例均改为提交 `_create_payload()`。
- 未删除用例，未添加 skip/xfail，未弱化原断言：
  - 权限用例仍断言 `403` 与 `AUTH_FORBIDDEN`。
  - 创建用例仍断言 `201`、`code=0`、`status=draft` 与操作日志。

## 单文件回归

- workdir：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- command：`.venv/bin/python -m pytest tests/test_quality_create_baseline.py -q`
- command_run_count：1
- exit_code：1
- result：FAIL
- pytest_summary：`1 failed, 1 passed, 1 warning in 0.97s`
- stdout_log：`03_需求与设计/02_开发计划/task_z022b_05_quality_create_baseline_fix_stdout.txt`

## 结果说明

- B04 中的缺失字段问题已被补齐，权限用例从原先的 `422` 进入原合同语义并通过。
- 创建用例不再因缺失字段返回 `422`，但出现新的 `409 QUALITY_INVALID_SOURCE`，message 为 `LOCAL_GATE_FAIL_CLOSED:non_local_dev`。
- 按任务规则，补齐字段后出现新的业务路径失败时只记录并停止；本轮未扩大到 quality router/schema/service/model/crud 修复。

## 禁止动作

- 未修改 quality router/schema/service/model/crud、前端、依赖或配置文件。
- 未运行其他 pytest、全量 pytest、npm、browser、build、typecheck、verify。
- 未 stage/commit/push/PR/tag/release。
- 未 cleanup/kill 本地服务。
- 未释放 parked blockers，未声明项目完成。
