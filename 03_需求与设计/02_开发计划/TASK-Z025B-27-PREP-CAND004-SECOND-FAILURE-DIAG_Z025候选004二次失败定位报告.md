# TASK-Z025B-27-PREP-CAND004-SECOND-FAILURE-DIAG Z025候选004二次失败定位报告

## Scope

- selected_candidate: Z025-CAND-004
- source_result_task: TASK-Z025B-26-FIX-CAND004
- failed_summary: `4 failed, 13 passed, 18 warnings in 1.45s`
- current_dirty_allowed_file: `07_后端/lingyi_service/tests/test_production_plan.py`

本轮只读定位，未运行 pytest，未修改测试或源码。

## Remaining Failures

1. `test_create_plan_rejects_missing_sales_order_item_carrier`
   - actual: HTTP 404
   - current assertion: HTTP 409
   - source evidence: `PRODUCTION_SO_ITEM_NOT_FOUND` 在 `app/core/error_codes.py` 映射为 404，router 使用 `status_of(code)`。

2. `test_material_check_and_create_work_order_creates_local_outbox_candidate`
   - actual: `outbox_id=0`
   - current assertion: `outbox_id > 0`
   - source evidence: `create_work_order_outbox` 在已有 `LyProductionWorkOrderLink` 且无匹配 outbox 时会返回 `outbox_id=0`；当前测试 `setUp` 未清理 `LyProductionWorkOrderLink`。

3. `test_plan_detail_returns_work_order_link_fields`
   - actual: `UNIQUE constraint failed: ly_production_work_order_link.plan_id`
   - source evidence: `LyProductionWorkOrderLink.plan_id` 是唯一关系，B26 dirty diff 中只清理了 material/outbox/plan，未清理 work-order-link。

4. `test_create_work_order_candidate_returns_unified_envelope`
   - actual: `write_entry_frozen_reason` 为当前受控写门禁文案
   - current assertion: 包含 `TASK-015E`
   - source evidence: `PRODUCTION_WRITE_ENTRY_FROZEN_REASON` 当前常量不包含 `TASK-015E`。

## Classification

- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: `07_后端/lingyi_service/tests/test_production_plan.py`
- recommended_next_task: TASK-Z025B-28-FIX-CAND004-SECOND
- backend_source_change_required: NO

## Forbidden Actions

- code/test edits: NO
- tests/build/typecheck/npm/browser: NO
- stage/commit/push/tag/pr/release: NO
- reset/checkout/stash/cleanup: NO
- production readback/go-live/project completion: NO
