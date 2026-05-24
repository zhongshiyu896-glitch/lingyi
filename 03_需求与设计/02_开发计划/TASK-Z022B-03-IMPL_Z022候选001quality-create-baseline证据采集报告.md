# TASK-Z022B-03-IMPL Z022-CAND-001 quality-create-baseline 证据采集报告

## Result

- task_id: TASK-Z022B-03-IMPL
- source_task_id: TASK-Z022B-02-PREP
- selected_candidate_id: Z022-CAND-001
- workdir: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_quality_create_baseline.py -q`
- command_run_count: 1
- exit_code: 1
- result: FAIL
- pytest_summary: `2 failed, 1 warning in 0.95s`
- stdout_log: `03_需求与设计/02_开发计划/task_z022b_03_quality_create_baseline_stdout.txt`

## Failed Tests

- `tests/test_quality_create_baseline.py::QualityCreateBaselineTest::test_post_create_requires_permission`
  - expected: `403`
  - actual: `422`
- `tests/test_quality_create_baseline.py::QualityCreateBaselineTest::test_post_create_returns_201_and_draft`
  - expected: `201`
  - actual: `422`
  - response detail: request body missing `request_id`, `idempotency_key`, `scenario_tag`, `source_ref`, `inspection_ref`, `operation`

## Scope

- frontend_diff_unchanged: true
- backend_diff_unchanged: true
- staged_performed: false
- commit_performed: false
- push_performed: false
- service_cleanup_or_kill_run: false
- forbidden_actions_detected: false

## Forbidden Actions

- 本轮只执行一次允许的单文件 pytest。
- 本轮未运行其他 pytest/npm/browser/build/typecheck/verify。
- 本轮未修改源码、测试、依赖或配置文件。
- 本轮未 stage/commit/push/PR/tag/release。
- 本轮未 cleanup/kill 本地服务。
- 本轮未释放 parked blockers，未声明项目完成。
