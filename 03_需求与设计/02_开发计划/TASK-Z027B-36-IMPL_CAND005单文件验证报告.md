# TASK-Z027B-36-IMPL CAND005 单文件验证报告

## Command

- Workdir: `07_后端/lingyi_service`
- Command: `.venv/bin/python -m pytest tests/test_workshop_wage.py -q`
- Command run count: 1

## Result

- Exit code: 1
- Result: FAIL
- Pytest summary: `2 failed, 45 passed, 12 warnings in 1.18s`
- Stdout log: `03_需求与设计/02_开发计划/task_z027b_36_cand005_stdout.txt`

## Failed Cases

- `WorkshopWageApiTest::test_daily_wage_formula_and_snapshot_not_changed`: expected `200`, observed `422`.
- `WorkshopWageApiTest::test_wage_rate_overlap_returns_409`: expected `409`, observed `422`.

## Post-Run Validation

- `git diff --cached --name-only`: empty
- Target test dirty diff: []
- `git diff --check`: PASS

## Boundary

- Fix attempted: NO
- Rerun performed: NO
- Stage/commit/push/tag/PR/release: NO
- Remote lifecycle parked: YES
- Production readback/go-live/project completion: NO
