# TASK-Z022B-27-IMPL-CAND003-REVALIDATE 单文件重验证报告

## 执行结果

- selected_candidate_id: Z022-CAND-003
- source_task_id: TASK-Z022B-26-PREP-CAND003-DIRTY-DIFF-REVIEW
- workdir: /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
- command: `.venv/bin/python -m pytest tests/test_quality_defect_baseline.py -q`
- command_run_count: 1
- exit_code: 1
- result: FAIL
- pytest_summary: 2 failed, 1 warning in 1.20s
- stdout_log: 03_需求与设计/02_开发计划/task_z022b_27_cand003_revalidate_stdout.txt

## 失败摘要

- `test_add_defect_to_draft_returns_201`: 期望 `201`，实际 `409 QUALITY_INVALID_SOURCE / LOCAL_GATE_FAIL_CLOSED:invalid_scenario_tag`
- `test_add_defect_to_non_draft_rejected_with_403`: 期望 `403`，实际 `409 QUALITY_INVALID_SOURCE / LOCAL_GATE_FAIL_CLOSED:invalid_scenario_tag`

## Diff 稳定性

- pre_test_diff_hash_or_summary: c1a680de26e31dd81131b38ff133e39b75d3dc670038c1a8e854c8c7df3b4d58; 1 file changed, 61 insertions(+), 28 deletions(-)
- post_test_diff_hash_or_summary: c1a680de26e31dd81131b38ff133e39b75d3dc670038c1a8e854c8c7df3b4d58; 1 file changed, 61 insertions(+), 28 deletions(-)
- test_diff_unchanged_by_this_task: YES

## 禁止动作确认

- code edits: NO
- test edits: NO
- backend app edits: NO
- frontend edits: NO
- existing artifact edits: NO
- engineer shared log edit: NO
- other pytest/full pytest: NO
- npm/browser/build/typecheck/verify: NO
- stage/commit/push: NO
- reset/checkout/cleanup: NO
- PR/tag/release: NO
- historical B20-B25 reused as PASS: NO
- production account / ERPNext production / real business write: NO
- parked blockers released: NO
- project completion claimed: NO

## 采集说明

pytest 命令仅执行一次，stdout/stderr 已写入 evidence 文件。用于打印退出码的 shell 包装在 pytest 完成后触发 zsh 只读变量名 `status` 问题；pytest 输出本身明确为 `2 failed, 1 warning in 1.20s`，因此本结果记录 `exit_code=1`，未重跑命令。
