# TASK-Z025B-25-PREP-CAND004-FAILURE-DIAG Z025候选004失败定位报告

## Scope

- Role: B Engineer
- Candidate: Z025-CAND-004
- Source result task: TASK-Z025B-24-IMPL
- Failed command: `.venv/bin/python -m pytest tests/test_production_plan.py -q`
- Failed summary: `17 failed, 1 warning in 1.08s`
- Run this task: NO

## Diagnosis

- Failed cases count: 17
- Failure pattern: all create-plan dependent tests fail before the intended production branch.
- Dominant actual result: HTTP 409 with `PRODUCTION_IDEMPOTENCY_CONFLICT`.
- Downstream material/work-order/detail cases fail with missing `plan_id` because plan creation returned a conflict envelope.

## Readonly Evidence

- B24 result JSON and stdout were read.
- Target test was read: `07_后端/lingyi_service/tests/test_production_plan.py`.
- Production router/service/model/schema were read.
- Test helper currently sets `APP_ENV=test`, omits `LINGYI_DB_URL`, omits `X-Request-ID`, and create payload omits `scenario_tag`, `operation`, `bom_id`, and `sales_order_item`.
- Current production service requires local dev gate plus carriers: `APP_ENV=development`, `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`, scenario tag pattern, `operation=create`, `bom_id`, `sales_order_item`, idempotency key containing scenario tag, and request id containing scenario tag.

## Boundary

- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Allowed fix file: `07_后端/lingyi_service/tests/test_production_plan.py`
- Recommended next task: `TASK-Z025B-26-FIX-CAND004`
- Business source change required: NO

## Forbidden Actions

- No code or test edits.
- No tests, build, typecheck, npm, or browser run.
- No stage, commit, push, tag, PR, or release.
- No reset, checkout, stash, or cleanup.
- No production readback, go-live, or project completion claim.
