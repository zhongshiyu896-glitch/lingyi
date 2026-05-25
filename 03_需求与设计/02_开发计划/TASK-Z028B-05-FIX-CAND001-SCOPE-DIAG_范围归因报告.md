# TASK-Z028B-05-FIX-CAND001-SCOPE-DIAG 范围归因报告

## Scope

- Role: B Engineer
- Candidate: `Z028-CAND-001`
- Blocked audit task: `TASK-Z028B-05-FIX-CAND001`
- Current HEAD: `abe758cebfa5c3affde9e3632692402227ec80c0`
- This task is readonly scope attribution only.

## B05 Evidence

- B05 result: PASS.
- Command run count: 1.
- Exit code: 0.
- Pytest summary: `2 passed, 10 warnings in 1.10s`.
- Allowed B05 target test: `07_后端/lingyi_service/tests/test_factory_statement_confirm_cancel.py`.
- B05 evidence artifacts:
  - `03_需求与设计/02_开发计划/TASK-Z028B-05-FIX-CAND001_factory_statement_confirm_cancel修复报告.md`
  - `03_需求与设计/02_开发计划/task_z028b_05_cand001_fix_result.json`
  - `03_需求与设计/02_开发计划/task_z028b_05_cand001_fix_result.tsv`
  - `03_需求与设计/02_开发计划/task_z028b_05_cand001_fix_stdout.txt`

## Dirty Attribution

- Current tracked dirty count: 20.
- CAND001 allowed target test count: 1.
- Unrelated historical tracked dirty count: 19.
- B05 evidence artifact count: 4.
- Cached area: empty.

Forbidden dirty paths present but unstaged:
- Frontend: 6 paths.
- Backend app: 3 paths.
- Shared engineer logs: 2 paths.
- Unrelated tests: 7 paths.
- Other control/handover file: 1 path.

The unrelated historical dirty paths are not in cached and must not be included in any later CAND001 ledger YES set.

## Assertion Check

- Confirm `200` assertion remains present.
- Pending payable-outbox cancel `409` assertion remains present.
- `FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE` assertion remains present.
- Failed/dead payable-outbox cancel `200` assertion remains present.
- No `skip` or `xfail` was found in the target test.

## Classification

- classification: `B05_SCOPE_ISOLATED_WITH_PREEXISTING_DIRTY`
- allowed_next_task: `TASK-Z028B-06-LEDGER-CAND001`

## Validation

- `git diff --cached --name-only`: empty.
- `git diff --check`: PASS.
- No pytest/npm/browser/build/typecheck/verify was run.
- No code/test/frontend/backend app/shared log/candidate pool files were modified by this task.
- No stage/commit/push/tag/PR/release was performed.
