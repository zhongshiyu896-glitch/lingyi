# TASK-Z022B-13-FIX Z022-CAND-002 quality update baseline 测试合同修复报告

## 修复边界

- 角色：B Engineer
- 源任务：TASK-Z022B-12-PREP
- 候选：Z022-CAND-002
- failure_classification：TEST_CONTRACT_UPDATE_ALLOWED
- 唯一允许修改文件：`07_后端/lingyi_service/tests/test_quality_update_baseline.py`
- 未修改 quality router/schema/service/model/crud、前端、依赖或配置文件。

## 修复摘要

- 在 `QualityUpdateBaselineTest` 中新增 `_required_update_fields(...)`。
- 仅补齐 B12 冻结的 update schema 必填字段：
  - `request_id`
  - `idempotency_key`
  - `scenario_tag`
  - `source_ref`
  - `inspection_ref`
  - `source_type`
  - `item_code`
  - `operation`
- 原有断言保持不变：
  - 确认态用例仍断言 403。
  - 草稿更新用例仍断言 200。
- 未删除用例，未添加 skip/xfail，未弱化为任意 2xx/4xx。

## 单文件 pytest 结果

- command：`.venv/bin/python -m pytest tests/test_quality_update_baseline.py -q`
- command_run_count：1
- exit_code：1
- result：FAIL
- pytest_summary：`2 failed, 1 warning in 1.04s`
- stdout_log：`03_需求与设计/02_开发计划/task_z022b_13_quality_update_baseline_fix_stdout.txt`

## 修复后失败摘要

- `test_patch_confirmed_rejected_with_403_cancelled_rejected_with_409`
  - 期望：403
  - 实际：409
- `test_patch_draft_inspection_success`
  - 期望：200
  - 实际：409
  - 错误：`QUALITY_INVALID_SOURCE / LOCAL_GATE_FAIL_CLOSED:non_local_dev`

按任务要求，补齐字段后出现新的断言失败，本轮已停止，未扩大到业务源码修复。

## 禁止动作确认

- 未运行其他 pytest、全量 pytest、npm/browser/build/typecheck/verify。
- 未修改除允许测试文件外的任何源码、测试、依赖或配置文件。
- 未 stage/commit/push/PR/tag/release。
- 未 cleanup/kill 服务。
- 未释放 parked blockers。
- 未声明项目完成。
