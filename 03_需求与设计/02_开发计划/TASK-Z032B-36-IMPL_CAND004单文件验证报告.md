# TASK-Z032B-36-IMPL CAND004 单文件验证报告

## 基本信息

- task_id: TASK-Z032B-36-IMPL
- role: B Engineer
- source_task: TASK-Z032B-35-PREP
- candidate_id: Z032-CAND-004
- current_head: aedc2d39cca4d065a028ce42e325de17490d95b6

## 执行命令

- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_workshop_job_card_sync.py -q`
- command_run_count: 1
- exit_code: 1
- result: FAIL
- pytest_summary: `4 failed, 1 warning in 0.98s`
- stdout_path: `03_需求与设计/02_开发计划/task_z032b_36_cand004_stdout.txt`

## 边界核对

- B35 boundary candidate: Z032-CAND-004
- B35 frozen command matched: true
- target_test: `07_后端/lingyi_service/tests/test_workshop_job_card_sync.py`
- target_test_dirty_diff_before: false
- target_test_dirty_diff_after: false
- cached_empty_after_run: true
- git_diff_check_after_run: PASS

## 生命周期门禁

- fix_attempt: false
- rerun_performed: false
- stage: false
- commit: false
- push: false
- tag: false
- pr: false
- release: false
- remote_lifecycle_parked: true
- production_readback: false
- go_live: false
- project_completion: false

## 本轮产物状态

- B36 report/json/tsv/stdout 未暂存
- 未修复代码或测试
- 未重跑 pytest
- 未运行其他 pytest/npm/browser/build/typecheck/verify
- 未 stage/commit/push/tag/PR/release
