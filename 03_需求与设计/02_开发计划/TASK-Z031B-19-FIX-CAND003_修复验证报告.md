# TASK-Z031B-19-FIX-CAND003 修复验证报告

## 范围核对

- task_id: TASK-Z031B-19-FIX-CAND003
- role: B Engineer
- source_task: TASK-Z031B-18-PREP-CAND003-FAILURE-DIAG
- candidate_id: Z031-CAND-003
- current_head: 23c9a5068daa6cca8a7071f4e4ce2def52bb6a7f
- allowed_fix_file: 07_后端/lingyi_service/tests/test_style_profit_api_errors.py
- changed_files:
  - 07_后端/lingyi_service/tests/test_style_profit_api_errors.py
  - 03_需求与设计/02_开发计划/TASK-Z031B-19-FIX-CAND003_修复验证报告.md
  - 03_需求与设计/02_开发计划/task_z031b_19_cand003_fix_result.json
  - 03_需求与设计/02_开发计划/task_z031b_19_cand003_fix_result.tsv
  - 03_需求与设计/02_开发计划/task_z031b_19_cand003_fix_stdout.txt

本轮仅修改授权目标测试与 B19 证据产物，未修改 backend app、前端、共享日志、candidate pool、其他测试或历史 dirty 文件。

## 修复内容

- 在目标测试内补齐 style profit local write-gate 需要的 `X-Request-ID`、本地写入环境与 payload carrier。
- fixture payload 补齐 `scenario_tag`、`source_ref`、`status_action`，并使 `idempotency_key` 与 scenario tag 对齐。
- 保留 error 场景的显式状态码/错误码断言：
  - local write-gate 接管的 invalid idempotency 与 blank sales order 场景固定断言 `409` / `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
  - idempotency request mismatch 场景仍保留 first `200` 与 second `409` / `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
  - unknown error 场景仍保留 `500` / `STYLE_PROFIT_INTERNAL_ERROR`。
  - commit failure 场景仍保留 `500` / `DATABASE_WRITE_FAILED`。
- 未新增 skip/xfail，未删除失败用例，未改为任意 2xx/4xx/5xx 弱断言。

## 单次验证

- workdir: 07_后端/lingyi_service
- command: `.venv/bin/python -m pytest tests/test_style_profit_api_errors.py -q`
- command_run_count: 1
- exit_code: 0
- result: PASS
- pytest_summary: 5 passed, 1 warning in 1.05s
- stdout_path: 03_需求与设计/02_开发计划/task_z031b_19_cand003_fix_stdout.txt

## Gate 状态

- cached_empty: true
- git_diff_check_pass: true
- target_test_dirty_diff: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- backend_app_changed: false
- frontend_changed: false
- unrelated_tests_changed: false
- continued_after_fail: false
- rerun_performed: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false
