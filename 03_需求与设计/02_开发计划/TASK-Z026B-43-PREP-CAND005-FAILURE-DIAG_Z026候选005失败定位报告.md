# TASK-Z026B-43-PREP-CAND005-FAILURE-DIAG Z026-CAND-005 失败定位报告

## 范围

- 候选：Z026-CAND-005
- 来源结果任务：TASK-Z026B-42-IMPL
- 当前 HEAD：b1e6f81edd168fc45cf8f7b6392f63119ce8e481
- 失败命令：`.venv/bin/python -m pytest tests/test_warehouse_inventory_count.py -q`
- 失败摘要：7 failed, 3 passed, 1 warning in 1.10s

## 失败模式

- 失败用例数：7
- 主要失败：create inventory-count 请求先返回 422，而旧测试期望进入 201、403、400、state-machine 或 list-filter 分支。
- 关键错误：`idempotency_key` 与 `source_ref` 为必填 body 字段，但测试 `_payload()` 未提供。
- 级联失败：列表过滤用例 setup 创建失败，导致返回 0 rows 而非 1 row。

## 只读证据

- `task_z026b_42_cand005_result.json`：记录 B42 FAIL 与 7 个失败用例。
- `task_z026b_42_cand005_stdout.txt`：显示 422 schema validation，缺少 `idempotency_key`、`source_ref`。
- `tests/test_warehouse_inventory_count.py`：`_payload()` 仅返回 company、warehouse、count_date、remark、items。
- `app/schemas/warehouse.py`：`WarehouseInventoryCountCreateRequest` 要求 `idempotency_key`、`source_ref`。
- `app/routers/warehouse.py`：`create_inventory_count` 在权限与 service 分支前读取并校验这两个 carrier 字段。
- `app/services/warehouse_service.py`：service 仍保留原目标业务校验，满足 payload 合同后可进入原断言分支。
- `app/models/warehouse.py`：库存盘点 header/item 模型支持现有 state-machine 与明细校验。

## 分类与边界

- classification：TEST_CONTRACT_UPDATE_ALLOWED
- allowed fix file：`07_后端/lingyi_service/tests/test_warehouse_inventory_count.py`
- recommended next task：TASK-Z026B-44-FIX-CAND005
- run this task：NO

## 门禁

- `git diff --cached --name-only`：EMPTY
- `git diff --check`：PASS
- pytest/npm/browser/build/typecheck/verify：未运行
- stage/commit/push/tag/PR/release：未执行
