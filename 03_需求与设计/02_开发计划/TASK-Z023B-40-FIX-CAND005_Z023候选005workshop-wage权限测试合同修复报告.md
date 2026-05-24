# TASK-Z023B-40-FIX-CAND005

## Scope

- Role: B Engineer
- Candidate: Z023-CAND-005
- Source task: TASK-Z023B-39-PREP-CAND005-FAILURE-DIAG
- Fixed file: `07_后端/lingyi_service/tests/test_workshop_wage_permissions.py`

No product code, backend app code, frontend code, unrelated tests, shared engineer log, candidate pool, prior artifacts, stage, commit, push, tag, PR, release, cleanup, or production write was performed.

## Fix

The target test contract was updated to satisfy the current workshop wage write contract:

- Set the test module local write environment to the current development local DB gate contract.
- Added a legal `Z002-WORKSHOP-WAGE-20260524-005` scenario tag for wage-rate write requests.
- Added deterministic carrier helpers for `scenario_tag`, `idempotency_key`, `source_ref`, and matching `X-Request-ID`.
- Updated the five previously failing `POST /api/workshop/wage-rates` calls to use carrier-complete payloads and headers.

The original permission, company validation, audit, and no-create assertions were preserved. No tests were skipped, xfailed, deleted, or loosened to broad status ranges.

## Validation

- Workdir: `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- Command run once: `.venv/bin/python -m pytest tests/test_workshop_wage_permissions.py -q`
- Exit code: `0`
- Result: PASS
- Pytest summary: `13 passed, 1 warning in 0.96s`
- Stdout: `03_需求与设计/02_开发计划/task_z023b_40_cand005_fix_stdout.txt`
