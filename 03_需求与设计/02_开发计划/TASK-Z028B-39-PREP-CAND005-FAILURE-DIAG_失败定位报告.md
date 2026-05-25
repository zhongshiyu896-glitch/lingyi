# TASK-Z028B-39-PREP-CAND005-FAILURE-DIAG

## Failure Evidence

- Candidate: Z028-CAND-005
- Current HEAD: `c8b8a5b53a91af33c9c1856312bc2af1935dbc38`
- B38 summary: `5 failed, 1 warning in 1.04s`
- Observed statuses: `[422, 422, 422, 422, 422]`
- Expected statuses: `[201, 201, 201, 201, 201]`
- Missing schema fields: `source_ref`, `warehouse`, `item_code`, `operation`, `quantity`, `business_date`, `status_action`, `scenario_tag`

Failed cases:

- `WarehouseStockEntryWorkerTest::test_cancelled_outbox_or_draft_not_processed`
- `WarehouseStockEntryWorkerTest::test_worker_default_batch_size_is_10`
- `WarehouseStockEntryWorkerTest::test_worker_dry_run_does_not_modify_outbox`
- `WarehouseStockEntryWorkerTest::test_worker_failure_retries_then_dead`
- `WarehouseStockEntryWorkerTest::test_worker_success_transitions_to_succeeded`

## Read-only Source Evidence

- `07_后端/lingyi_service/tests/test_warehouse_stock_entry_worker.py`
- `07_后端/lingyi_service/tests/test_warehouse_stock_entry_draft.py`
- `07_后端/lingyi_service/app/routers/warehouse.py`
- `07_后端/lingyi_service/app/services/warehouse_service.py`
- `07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`
- `07_后端/lingyi_service/app/models/warehouse.py`
- `07_后端/lingyi_service/app/schemas/warehouse.py`

The worker tests create drafts through the shared legacy `_payload()` helper. Current `WarehouseStockEntryDraftCreateRequest` and the router local write gate require additional carrier fields before the request can reach the expected 201 draft creation branch.

## Boundary

- Classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- Allowed fix file: `07_后端/lingyi_service/tests/test_warehouse_stock_entry_worker.py`
- Next task: `TASK-Z028B-40-FIX-CAND005`
- Run this task: false

## Gates

- Cached empty: true
- Target test dirty diff: false
- Historical dirty forbidden staged: []
- `git diff --check`: PASS
- Tests rerun: false
- Stage/commit/push/tag/PR/release: false
