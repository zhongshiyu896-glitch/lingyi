# TASK-Z026B-44-FIX-CAND005 Z026-CAND-005 warehouse-inventory-count 测试合同修复报告

## 修复范围

- 来源任务：TASK-Z026B-43-PREP-CAND005-FAILURE-DIAG
- 候选：Z026-CAND-005
- fixed file：`07_后端/lingyi_service/tests/test_warehouse_inventory_count.py`
- failure classification：TEST_CONTRACT_UPDATE_ALLOWED
- schema payload contract fixed：PARTIAL_422_SCHEMA_PAYLOAD_DRIFT_RESOLVED
- assertions weakened：NO
- skip/xfail/deleted cases：NO

## 验证

- workdir：`07_后端/lingyi_service`
- command：`.venv/bin/python -m pytest tests/test_warehouse_inventory_count.py -q`
- command run count：1
- exit code：1
- result：FAIL
- pytest summary：1 failed, 9 passed, 1 warning in 1.10s
- stdout log：`03_需求与设计/02_开发计划/task_z026b_44_cand005_fix_stdout.txt`

## 剩余失败

- `tests/test_warehouse_inventory_count.py::WarehouseInventoryCountApiTest::test_cancel_and_repeat_cancel`
- actual：409 WAREHOUSE_IDEMPOTENCY_CONFLICT
- expected：200
- message：scenario_tag 载体缺失或格式非法

## Git Scope

- changed files：`07_后端/lingyi_service/tests/test_warehouse_inventory_count.py`
- `git diff --cached --name-only`：EMPTY
- `git diff --check`：PASS

## 禁止动作

- backend app edits：NO
- frontend edits：NO
- unrelated tests edits：NO
- tests/build/typecheck/npm/browser beyond allowed command：NO
- stage/commit/push/tag/PR/release：NO
- reset/checkout/stash/cleanup：NO
- production readback/go-live/project completion：NO
