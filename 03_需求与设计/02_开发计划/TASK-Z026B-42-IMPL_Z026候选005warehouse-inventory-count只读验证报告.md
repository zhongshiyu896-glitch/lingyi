# TASK-Z026B-42-IMPL Z026-CAND-005 warehouse-inventory-count 只读验证报告

## 验证范围

- 来源任务：TASK-Z026B-41-PREP
- 候选：Z026-CAND-005
- 当前 HEAD：b1e6f81edd168fc45cf8f7b6392f63119ce8e481
- workdir：`07_后端/lingyi_service`
- command：`.venv/bin/python -m pytest tests/test_warehouse_inventory_count.py -q`
- command run count：1

## 结果

- exit code：1
- result：FAIL
- pytest summary：7 failed, 3 passed, 1 warning in 1.10s
- stdout log：`03_需求与设计/02_开发计划/task_z026b_42_cand005_stdout.txt`

## 失败用例

- `tests/test_warehouse_inventory_count.py::WarehouseInventoryCountApiTest::test_cancel_and_repeat_cancel`
- `tests/test_warehouse_inventory_count.py::WarehouseInventoryCountApiTest::test_counted_qty_negative_returns_400`
- `tests/test_warehouse_inventory_count.py::WarehouseInventoryCountApiTest::test_create_inventory_count_draft_with_permission`
- `tests/test_warehouse_inventory_count.py::WarehouseInventoryCountApiTest::test_inventory_write_only_cannot_create_inventory_count`
- `tests/test_warehouse_inventory_count.py::WarehouseInventoryCountApiTest::test_list_filters_by_company_and_warehouse`
- `tests/test_warehouse_inventory_count.py::WarehouseInventoryCountApiTest::test_state_machine_submit_review_confirm`
- `tests/test_warehouse_inventory_count.py::WarehouseInventoryCountApiTest::test_variance_without_reason_returns_400`

## Git Scope

- target test dirty diff：[]
- `git diff --cached --name-only`：EMPTY
- `git diff --check`：PASS

## 禁止动作

- 修复尝试：NO
- 代码或测试修改：NO
- 其他 pytest/npm/browser/build/typecheck/verify：NO
- stage/commit/push/tag/PR/release：NO
- reset/checkout/stash/cleanup：NO
- production readback/go-live/project completion：NO
