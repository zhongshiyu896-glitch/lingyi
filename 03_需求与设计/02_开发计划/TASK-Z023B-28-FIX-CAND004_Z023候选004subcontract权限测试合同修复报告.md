# TASK-Z023B-28-FIX-CAND004 Z023-CAND-004 subcontract权限测试合同修复报告

## Scope

- Role: B Engineer
- Candidate: Z023-CAND-004
- Allowed fixed file: `07_后端/lingyi_service/tests/test_subcontract_permissions.py`
- Backend app edited: NO
- Frontend edited: NO
- Stage/commit/push performed: NO

## Fix Attempt

- Added subcontract write carrier helpers for `request_id`, `idempotency_key`, `scenario_tag`, `source_ref`, `subcontract_ref`, `supplier_ref`, `work_order_ref`, `operation`, `item_code`, `quantity`, and `status_action`.
- Added `X-Request-ID` support to the test headers helper.
- Set subcontract local write gate environment to `APP_ENV=development` and `LINGYI_DB_URL=sqlite:///./lingyi_service.local.db`.
- Updated create, receive, and inspect write-path tests to send carrier-aware payloads.

## Validation Result

- Command: `.venv/bin/python -m pytest tests/test_subcontract_permissions.py -q`
- Command run count: 1
- Exit code: 1
- Result: FAIL
- Pytest summary: `7 failed, 11 passed, 8 warnings in 1.11s`
- Stdout log: `03_需求与设计/02_开发计划/task_z023b_28_cand004_fix_stdout.txt`

## Failure Notes

- The run failed after the first allowed pytest execution.
- Main observed failure categories:
  - `TypeError: SubcontractPermissionTest._create_payload() got multiple values for argument 'item_code'`
  - `test_receive_fail_closed_after_auth_does_not_create_receipt` expected `sync_status=pending`, actual `succeeded`
- Per task requirement, no further fix was attempted after the FAIL result.

## Forbidden Actions

- Product code edits: NO
- Backend app edits: NO
- Unrelated tests edits: NO
- Control-plane edits outside allowed files: NO
- Stage/commit/push: NO
- PR/tag/release/cleanup: NO
- Production account / ERPNext production / real business write: NO
- Parked blockers released: NO
