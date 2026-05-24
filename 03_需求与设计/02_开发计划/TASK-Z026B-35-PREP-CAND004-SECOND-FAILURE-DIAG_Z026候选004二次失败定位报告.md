# TASK-Z026B-35-PREP-CAND004-SECOND-FAILURE-DIAG

## Scope

- Role: B Engineer
- Selected candidate: Z026-CAND-004
- Source result task: TASK-Z026B-34-FIX-CAND004
- Failed summary: `1 failed, 9 passed, 7 warnings in 1.14s`
- Remaining failed case: `test_subcontract_no_fake_stock_entry_name_after_task_002b1`
- Run this task: NO

## Readonly Evidence

- `03_需求与设计/02_开发计划/task_z026b_34_cand004_fix_result.json`
- `03_需求与设计/02_开发计划/task_z026b_34_cand004_fix_stdout.txt`
- `07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`
- `07_后端/lingyi_service/app/routers/subcontract.py`
- `07_后端/lingyi_service/app/schemas/subcontract.py`
- `07_后端/lingyi_service/app/services/subcontract_service.py`
- `07_后端/lingyi_service/app/models/subcontract.py`

## Remaining Failure

- Status code: `200`
- Response code: `0`
- Assertion: expected `response.json()["data"]["stock_entry_name"]` to be `None`
- Actual: `LOCAL-RECEIPT-SRB-51-20260524191707103052`

## Dirty Diff Relationship

B34 updated the test contract so write requests include the current carrier fields, `X-Request-ID`, and local-dev gate environment. That correctly moves the receive test past the previous `409` local gate and into `SubcontractService.receive`.

The service source shows the current local-dev substitute behavior: when the local-dev sync substitute is enabled, receipt sync status is set to `succeeded` and `stock_entry_name` is set to `LOCAL-RECEIPT-<receipt_batch_no>`. The remaining failing assertion still expects `None`, which is now stale for this local-dev branch.

## Classification

- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_subcontract_exception_handling.py`
- recommended_next_task: `TASK-Z026B-36-FIX-CAND004-SECOND`

No backend app source boundary is recommended by this evidence. The next fix should update only the target test assertion to match the current explicit local-dev substitute contract while preserving the original guard against fake `STE-ISS` / `STE-REC` stock entry names.

## Validation

- current_head: `1f0e1d7bf322cecc7f4d51e93491a282653e6ead`
- cached area: empty
- `git diff --check`: PASS
- pytest rerun: NO
- code/test edits: NO
- stage/commit/push: NO
