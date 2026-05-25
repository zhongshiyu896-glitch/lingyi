# TASK-Z031B-39-PREP-CAND005-FAILURE-DIAG 失败定位边界报告

- task_id: TASK-Z031B-39-PREP-CAND005-FAILURE-DIAG
- role: B Engineer
- source_task: TASK-Z031B-38-IMPL
- candidate_id: Z031-CAND-005
- current_head: ed859b726057b3c5d8d7072dd60055f6954cb119
- cached_empty: true
- git_diff_check: PASS
- B38 result: FAIL
- B38 command_run_count: 1
- B38 pytest_summary: 10 failed, 2 passed, 1 warning in 1.08s

## 失败差异

- test_cancel_draft_success_and_outbox_cancelled: observed 422, expected create 201 before cancel branch
- test_company_scope_denied_returns_403_or_404: observed 422, expected 403 or 404
- test_create_draft_generates_in_pending_outbox: observed 422, expected 201
- test_create_draft_with_permission: observed 422, expected 201
- test_inventory_write_only_cannot_create_draft: observed 422, expected 403
- test_outbox_status_returns_correct_payload: observed create response lacks data after 422, expected created draft data
- test_qty_lte_zero_returns_400: observed 422, expected 400 business validation
- test_repeat_cancel_returns_409: observed create response lacks data after 422, expected create then repeat cancel 409
- test_warehouse_scope_denied_returns_403_or_404: observed 422, expected 403 or 404
- test_without_stock_entry_draft_permission_returns_403: observed 422, expected 403

## 失败模式

目标测试旧 `_payload` 缺少当前 `WarehouseStockEntryDraftCreateRequest` / `WarehouseStockEntryDraftCancelRequest` 必填 carrier 字段：`source_ref`、`warehouse`、`item_code`、`operation`、`quantity`、`business_date`、`status_action`、`scenario_tag`。因此请求在 schema validation 阶段提前返回 422，未进入原 201/400/403/404/409 业务分支。

## 边界冻结

- classification: TEST_CONTRACT_UPDATE_ALLOWED
- allowed_fix_file: 07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py
- next_task: TASK-Z031B-40-FIX-CAND005
- target_test: 07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py
- target_test_dirty_diff: false
- source_evidence_missing: []
- historical_dirty_forbidden_staged: []
- run_this_task: false

## Gate 状态

- stage: false
- commit: false
- push: false
- tag: false
- PR: false
- release: false
- remote_lifecycle_parked: true
- production_readback: false
- go_live: false
- project_completion: false
- B39 本轮 report/json/tsv 未 staged
