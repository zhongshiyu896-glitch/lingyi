# TASK-Z031B-31-PREP-CAND004-FAILURE-DIAG 失败定位边界报告

## 只读核对

- 当前 HEAD: `0f783aa3b3f9a2cdc467c504840aa6caed55a56c`
- cached 状态: empty
- `git diff --check`: PASS
- B30 result: FAIL
- B30 command_run_count: 1
- B30 pytest summary: `19 failed, 5 passed, 1 warning in 1.24s`
- target test: `07_后端/lingyi_service/tests/test_subcontract_inspection.py`
- target test dirty diff: false
- source_evidence_missing: []
- historical dirty forbidden staged: []

## 失败摘要

B30 stdout 中 19 个失败用例均可追溯。主要模式为目标测试仍使用旧版 inspect payload 或直接构造旧版 `InspectRequest`，缺少 `SubcontractWriteCarrierBase` 继承来的写入 carrier 必填字段。路由 `_parse_inspect_payload` 在 `InspectRequest.model_validate(payload)` 阶段将该 schema 失败映射为 `409 SUBCONTRACT_STOCK_OUTBOX_CONFLICT`，导致原 `200/404/409` 业务分支无法进入。service-layer 用例直接构造 `InspectRequest` 时也出现同类必填字段 ValidationError。

## 19 个失败差异

1. `test_inspect_all_received_but_not_all_planned_sets_waiting_receive`: observed `409 SUBCONTRACT_STOCK_OUTBOX_CONFLICT`; expected `200` and waiting receive branch.
2. `test_inspect_creates_inspection_and_amounts`: observed `409 SUBCONTRACT_STOCK_OUTBOX_CONFLICT`; expected `200` success and amount assertions.
3. `test_inspect_does_not_call_erpnext_or_create_finance_docs`: observed `409 SUBCONTRACT_STOCK_OUTBOX_CONFLICT`; expected `200` success and no ERP/finance side effects.
4. `test_inspect_idempotent_different_payload_returns_conflict`: observed first inspect `409`; expected first inspect `200` before conflict branch.
5. `test_inspect_idempotent_retry_after_full_inspection_does_not_check_remaining_first`: observed `409`; expected `200` idempotent retry branch.
6. `test_inspect_idempotent_same_payload_returns_existing_result`: observed `409`; expected `200` existing result branch.
7. `test_inspect_partial_batch_keeps_waiting_inspection`: observed `409`; expected `200` partial inspection branch.
8. `test_inspect_rejects_deduction_amount_greater_than_gross_amount`: observed `409 SUBCONTRACT_STOCK_OUTBOX_CONFLICT`; expected `409 SUBCONTRACT_DEDUCTION_EXCEEDS_GROSS`.
9. `test_inspect_rejects_qty_exceeding_batch_remaining_qty`: observed setup inspect `409`; expected setup inspect `200` before over-quantity rejection.
10. `test_inspect_rejects_receipt_batch_from_other_order`: observed `409`; expected `404`.
11. `test_inspect_rejects_rejected_qty_greater_than_inspected_qty`: observed `409 SUBCONTRACT_STOCK_OUTBOX_CONFLICT`; expected `409 SUBCONTRACT_REJECTED_QTY_EXCEEDS_INSPECTED`.
12. `test_inspect_rejects_unsynced_receipt_batch`: observed `409 SUBCONTRACT_STOCK_OUTBOX_CONFLICT`; expected `409 SUBCONTRACT_RECEIPT_NOT_SYNCED`.
13. `test_inspect_same_key_different_receipt_batch_does_not_create_second_success_response`: observed setup inspect `409`; expected setup inspect `200`.
14. `test_inspect_same_key_different_receipt_batch_returns_conflict`: observed setup inspect `409`; expected setup inspect `200` before conflict branch.
15. `test_inspect_same_key_same_batch_decimal_equivalent_returns_existing_result`: observed `409`; expected `200` existing result branch.
16. `test_inspect_same_key_same_batch_different_deduction_rate_returns_conflict`: observed setup inspect `409`; expected setup inspect `200` before conflict branch.
17. `test_inspect_service_layer_prevents_overinspect_regression`: observed `InspectRequest` ValidationError for missing carrier fields; expected service-layer overinspect guard to run.
18. `test_subcontract_detail_inspection_amounts_use_inspection_table_not_receipt_legacy_fields`: observed setup inspect `409`; expected setup inspect `200` before detail amount assertions.
19. `test_subcontract_detail_returns_inspections`: observed setup inspect `409`; expected setup inspect `200` before detail inspection list assertions.

## 分类与下一步边界

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_inspection.py`
- next_task: `TASK-Z031B-32-FIX-CAND004`

该分类依据是失败集中于目标测试 fixture/payload/direct model construction 未携带当前 schema 必填 carrier 字段，证据支持在目标测试内调整 fixture/payload/mock，使原 `200/404/409` 业务分支恢复可达；未见需要修改 backend app 的证据。

## Gate

- run_this_task: false
- stage/commit/push/tag/PR/release: false
- remote_lifecycle_parked: true
- production_readback/go_live/project_completion: false
