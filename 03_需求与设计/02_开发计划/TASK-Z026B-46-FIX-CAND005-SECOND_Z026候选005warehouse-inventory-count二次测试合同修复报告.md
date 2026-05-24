# TASK-Z026B-46-FIX-CAND005-SECOND Z026候选005 warehouse-inventory-count 二次测试合同修复报告

## 修复范围

- selected_candidate: `Z026-CAND-005`
- source_task: `TASK-Z026B-45-PREP-CAND005-SECOND-FAILURE-DIAG`
- fixed_file: `07_后端/lingyi_service/tests/test_warehouse_inventory_count.py`
- failure_classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- assertions_weakened: `NO`
- skip_xfail_deleted_cases: `NO`

## 修复内容

根据 B45 定位，剩余失败来自 `test_cancel_and_repeat_cancel` 的 cancel payload carrier 缺失合法 `scenario_tag`。本轮仅在目标测试文件内调整两个 cancel 请求的 `reason`：

- 首次 cancel: `Z002-WAREHOUSE-COUNT-20260420-001 manual cancel`
- 重复 cancel: `Z002-WAREHOUSE-COUNT-20260420-001 repeat cancel`

原断言保持不变：首次 cancel 仍明确断言 `200` 与 `cancelled`，重复 cancel 仍明确断言 `409` 与 `WAREHOUSE_INVENTORY_COUNT_ALREADY_CANCELLED`。未改为任意 2xx/4xx，未 skip/xfail，未删除用例。

## 验证

- workdir: `07_后端/lingyi_service`
- command: `.venv/bin/python -m pytest tests/test_warehouse_inventory_count.py -q`
- command_run_count: `1`
- exit_code: `0`
- pytest_summary: `10 passed, 1 warning in 1.08s`
- result: `PASS`
- stdout_log: `03_需求与设计/02_开发计划/task_z026b_46_cand005_second_fix_stdout.txt`
- git diff --cached --name-only: `EMPTY`
- git diff --check: `PASS`

## 禁止动作确认

- backend app edits: `NO`
- frontend edits: `NO`
- unrelated tests edits: `NO`
- tests/build/typecheck/npm/browser beyond allowed command: `NO`
- stage/commit/push/tag/pr/release: `NO`
- reset/checkout/stash/cleanup: `NO`
- production readback/go-live/project completion: `NO`
- memory citation / unrelated reply blocks: `NO`
