# TASK-Z028B-12-IMPL Z028-CAND-002 单文件验证报告

## Command

- Workdir: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- Command: `.venv/bin/python -m pytest tests/test_factory_statement_idempotency.py -q`
- Command run count: 1
- Exit code: 1
- Result: FAIL
- Pytest summary: `5 failed, 7 passed, 29 warnings in 1.18s`

## Failed Cases

- `FactoryStatementIdempotencyTest::test_cancel_same_key_different_payload_conflict`
- `FactoryStatementIdempotencyTest::test_cancel_same_key_same_hash_replays_same_operation`
- `FactoryStatementIdempotencyTest::test_confirm_concurrent_same_idempotency_key_replays_without_duplicate_operation`
- `FactoryStatementIdempotencyTest::test_confirm_same_key_different_payload_conflict`
- `FactoryStatementIdempotencyTest::test_confirm_same_key_same_hash_replays_same_operation`

## Scope

- Target test dirty diff: NO
- Cached empty: YES
- Historical dirty forbidden staged: []
- Fix attempt: NO
- Rerun performed: NO
- Stdout log: `03_需求与设计/02_开发计划/task_z028b_12_cand002_stdout.txt`

## Gates

- `git diff --check`: PASS
- Stage/commit/push/tag/PR/release: NO
- Remote lifecycle parked: YES
- Production readback/go-live/project completion: NO
