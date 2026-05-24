# TASK-Z022B-11-IMPL Z022-CAND-002 quality update baseline 证据采集报告

## 执行边界

- 角色：B Engineer
- 源任务：TASK-Z022B-10-PREP
- 候选：Z022-CAND-002
- 工作目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- 唯一执行命令：`.venv/bin/python -m pytest tests/test_quality_update_baseline.py -q`
- command_run_count：1

## 执行结果

- exit_code：1
- result：FAIL
- pytest_summary：`2 failed, 1 warning in 0.92s`
- stdout_log：`03_需求与设计/02_开发计划/task_z022b_11_quality_update_baseline_stdout.txt`

## 失败摘要

- `tests/test_quality_update_baseline.py::QualityUpdateBaselineTest::test_patch_confirmed_rejected_with_403_cancelled_rejected_with_409`
  - 断言：`self.assertEqual(confirmed_resp.status_code, 403)`
  - 实际：`422`
- `tests/test_quality_update_baseline.py::QualityUpdateBaselineTest::test_patch_draft_inspection_success`
  - 断言：`self.assertEqual(response.status_code, 200, response.text)`
  - 实际：`422`
  - 缺失字段：`request_id`、`idempotency_key`、`scenario_tag`、`source_ref`、`inspection_ref`、`source_type`、`item_code`、`operation`

## 禁止动作确认

- 未运行其他 pytest 或全量 pytest。
- 未运行 npm/browser/build/typecheck/verify。
- 未编辑任何源码、测试、依赖或配置文件。
- 未 stage/commit/push/PR/tag/release。
- 未 cleanup/kill 服务。
- 未释放 parked blockers。
- 未声明项目完成。
