# TASK-Z025B-26-FIX-CAND004 Z025候选004 production-plan 测试合同修复报告

## Scope

- selected_candidate: Z025-CAND-004
- source_task: TASK-Z025B-25-PREP-CAND004-FAILURE-DIAG
- fixed_file: `07_后端/lingyi_service/tests/test_production_plan.py`
- failure_classification: TEST_CONTRACT_UPDATE_ALLOWED

## Fix Attempt

已按 B25 定位只修改目标测试文件，补齐 production-plan 当前测试合同：

- local-dev write gate 环境：`APP_ENV=development`、`LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`
- 请求头增加 `X-Request-ID`，并包含对应 `scenario_tag`
- create-plan payload 增加 `scenario_tag`、`operation=create`、`sales_order_item`、`bom_id`、`company`
- idempotency key 改为包含 `scenario_tag`
- material-check 与 create-work-order 增加 detail scenario、plan/business carrier 与 request_id helper

未修改 backend app、前端或其他测试文件。未 skip、xfail 或删除用例。

## Validation

- command: `.venv/bin/python -m pytest tests/test_production_plan.py -q`
- workdir: `07_后端/lingyi_service`
- command_run_count: 1
- exit_code: 1
- result: FAIL
- pytest_summary: `4 failed, 13 passed, 18 warnings in 1.45s`
- stdout_log: `03_需求与设计/02_开发计划/task_z025b_26_cand004_fix_stdout.txt`

按任务要求，单次 pytest 失败后已停止；未继续修复、未重跑、未扩大范围。

## Remaining Failures

- `test_create_plan_rejects_missing_sales_order_item_carrier`: expected 409, actual 404.
- `test_material_check_and_create_work_order_creates_local_outbox_candidate`: `outbox_id` actual 0, old assertion expected greater than 0.
- `test_plan_detail_returns_work_order_link_fields`: manual insert hit `UNIQUE constraint failed: ly_production_work_order_link.plan_id`.
- `test_create_work_order_candidate_returns_unified_envelope`: `write_entry_frozen_reason` no longer contains `TASK-015E`.

## Forbidden Actions

- backend app edits: NO
- frontend edits: NO
- unrelated tests edits: NO
- tests/build/typecheck/npm/browser beyond allowed command: NO
- stage/commit/push/tag/pr/release: NO
- reset/checkout/stash/cleanup: NO
- production readback/go-live/project completion: NO
