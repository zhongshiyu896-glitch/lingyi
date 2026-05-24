# TASK-Z026B-45-PREP-CAND005-SECOND-FAILURE-DIAG Z026候选005二次失败定位报告

## 结论

- selected_candidate: `Z026-CAND-005`
- source_result_task: `TASK-Z026B-44-FIX-CAND005`
- failed_summary: `1 failed, 9 passed, 1 warning in 1.10s`
- remaining_failed_case: `test_cancel_and_repeat_cancel`
- classification: `TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file: `07_后端/lingyi_service/tests/test_warehouse_inventory_count.py`
- recommended_next_task: `TASK-Z026B-46-FIX-CAND005-SECOND`
- run_this_task: `NO`

## 失败模式

B44 已在允许测试文件内补齐 create payload 的 `idempotency_key`、`source_ref` 和本地门禁请求头，原始 422 schema payload 漂移已收敛为单个 cancel 分支失败。B44 stdout 显示剩余失败为：

```text
AssertionError: 409 != 200 : {"code":"WAREHOUSE_IDEMPOTENCY_CONFLICT","message":"scenario_tag 载体缺失或格式非法","data":{}}
```

当前 `test_cancel_and_repeat_cancel` 的首次 cancel 请求仍使用：

```python
json={"reason": "manual cancel"}
```

而 `app/routers/warehouse.py` 的 `cancel_inventory_count` 在进入 service cancel 前调用 `_validate_local_warehouse_inventory_count_gate`，校验载体为：

```python
carriers=[str(before_data.get("count_no") or ""), payload.reason]
```

该 gate 要求 request id 与所有 carrier 均包含合法 `Z002-WAREHOUSE-COUNT-...` scenario tag。当前 cancel reason 未携带该 tag，因此在原目标 `200/cancelled` 状态机断言前被本地幂等门禁拦截为 `409 WAREHOUSE_IDEMPOTENCY_CONFLICT`。

## 只读证据

- `03_需求与设计/02_开发计划/task_z026b_44_cand005_fix_result.json`: B44 记录 `1 failed, 9 passed, 1 warning in 1.10s`，剩余失败 actual 为 `409 WAREHOUSE_IDEMPOTENCY_CONFLICT`，expected 为 `200`。
- `03_需求与设计/02_开发计划/task_z026b_44_cand005_fix_stdout.txt`: stdout 中失败断言为 `409 != 200`，响应消息为 `scenario_tag 载体缺失或格式非法`。
- `07_后端/lingyi_service/tests/test_warehouse_inventory_count.py`: 当前 dirty diff 仅显示 B44 对同一允许测试文件的合同修复；剩余 cancel payload 的 `reason` 未承载 scenario tag。
- `07_后端/lingyi_service/app/routers/warehouse.py`: cancel endpoint 对 `before_data.count_no` 与 `payload.reason` 执行本地 warehouse inventory-count gate。
- `07_后端/lingyi_service/app/schemas/warehouse.py`: `WarehouseInventoryCountCancelRequest` 仅要求 `reason` 字段，剩余问题不是新增 schema 字段缺失。
- `07_后端/lingyi_service/app/services/warehouse_service.py`: service cancel 仍保留首次取消成功、重复取消返回 `WAREHOUSE_INVENTORY_COUNT_ALREADY_CANCELLED` 的业务状态机。

## 边界冻结

证据支持继续在测试合同内修复：将 cancel payload 的载体值调整为当前本地门禁合法 carrier，使测试进入原目标的首次 cancel `200/cancelled` 与重复 cancel `409 WAREHOUSE_INVENTORY_COUNT_ALREADY_CANCELLED` 分支。下一任务只允许修改：

`07_后端/lingyi_service/tests/test_warehouse_inventory_count.py`

本轮未运行 pytest，未修改后端代码或测试文件，未 stage/commit/push。
