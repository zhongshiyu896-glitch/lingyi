# TASK-Z034B-05-FIX-CAND001 修复验证报告

## 前置核对

- current_head: `6bc20b833e3780e2bd10549a2ce906ee860941cb`
- cached: empty
- git diff --check: PASS
- B03 result: FAIL, `4 failed, 6 passed, 1 warning in 1.12s`
- B04 classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- B04 allowed_fix_file: `07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
- B05-DIRTY-ATTRIBUTION: C PASS；`unknown_dirty=[]`、`must_block_before_continue=[]`、`blocked=false`
- 16 个 product/test dirty: 全部为 `historical_dirty_forbidden` 且 `allowed_in_next_ledger=false`
- target test before fix: no dirty diff
- previous cycle note: Z033-CAND-003 skipped-only risk preserved, `actual_passed_count=0`、`skipped_count=4`

## 修复范围

- changed_files:
  - `07_后端/lingyi_service/tests/test_style_profit_api_audit.py`

未修改 backend app、frontend、candidate pool、共享日志、历史 dirty forbidden 文件或其他测试。

## 修复内容

- 在目标测试内补齐 style-profit create 写入 gate 当前要求的本地环境、`X-Request-ID`、`scenario_tag`、`source_ref`、`status_action` 与带 scenario 前缀的 `idempotency_key`。
- 保留原 create endpoint audit 业务分支断言：`200` 成功审计、`400` 客户端来源字段禁止、`503` 来源不可用 fail-closed、`400` 非法公式版本。
- 未接受 `409 STYLE_PROFIT_IDEMPOTENCY_CONFLICT` 作为期望结果。
- 未新增 skip/xfail，未删除失败用例，未弱化为任意 2xx/4xx/5xx。

## 单次验证

- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_style_profit_api_audit.py -q`
- command_run_count: 1
- exit_code: 0
- result: PASS
- pytest_summary: `10 passed, 1 warning in 1.22s`
- stdout_path: `03_需求与设计/02_开发计划/task_z034b_05_cand001_fix_stdout.txt`

## 收口状态

- target_test_dirty_diff: true
- only_allowed_fix_file_changed: true
- historical_dirty_forbidden_preserved: true
- backend_app_changed: false
- frontend_changed: false
- candidate_pool_changed: false
- unrelated_tests_changed: false
- no_409_conflict_acceptance: true
- business_status_assertions_preserved: true
- assertions_weakened: false
- skip_xfail_deleted_cases: false
- rerun_performed: false
- continued_after_fail: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false
