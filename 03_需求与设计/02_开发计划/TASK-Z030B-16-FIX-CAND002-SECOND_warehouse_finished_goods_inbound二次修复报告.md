# TASK-Z030B-16-FIX-CAND002-SECOND warehouse_finished_goods_inbound 二次修复报告

## Scope

- Candidate: `Z030-CAND-002`
- Source task: `TASK-Z030B-15-PREP-CAND002-SECOND-FAILURE-DIAG`
- Allowed fix file: `07_后端/lingyi_service/tests/test_warehouse_finished_goods_inbound.py`
- Workdir: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- Command: `.venv/bin/python -m pytest tests/test_warehouse_finished_goods_inbound.py -q`
- Command run count: `1`

## Change

- Changed file: `07_后端/lingyi_service/tests/test_warehouse_finished_goods_inbound.py`
- The draft payload now carries the same `Z003-WAREHOUSE-20260525-001` scenario tag through `source_id`, `source_ref`, and `idempotency_key`.
- `source_ref` remains equal to `source_id`, matching the warehouse idempotency carrier contract.
- Explicit business status assertions remain `201` for successful draft creation and `400` for candidate-disabled fail-closed behavior.
- No `skip` or `xfail` was added. No test case was deleted. Assertions were not weakened to broad 2xx/4xx checks.

## Verification

- Exit code: `0`
- Result: `PASS`
- Pytest summary: `5 passed, 1 warning in 1.00s`
- Stdout: `03_需求与设计/02_开发计划/task_z030b_16_cand002_second_fix_stdout.txt`

## Gates

- `git diff --cached --name-only`: empty
- `git diff --check`: PASS
- Backend app changed: false
- Frontend changed: false
- Shared log changed: false
- Candidate pool changed: false
- Unrelated tests changed: false
- Stage/commit/push/tag/PR/release: false
- Remote lifecycle parked: true
- Production readback/go-live/project completion: false
