# TASK-Z026B-24-PREP-CAND003-FAILURE-DIAG Z026候选003失败定位报告

## 输入证据

- 候选：`Z026-CAND-003`
- 来源结果任务：`TASK-Z026B-23-IMPL`
- 失败命令：`.venv/bin/python -m pytest tests/test_sales_inventory_api.py -q`
- 失败摘要：`1 failed, 14 passed, 1 warning in 1.08s`
- 失败用例：`test_only_get_routes_are_exposed`

## 失败断言

`test_sales_inventory_api.py` 中 `test_only_get_routes_are_exposed` 枚举所有 `/api/sales-inventory` 路由，并断言每个路由方法集合都必须是 `GET/HEAD/OPTIONS` 的子集。

B23 stdout 记录的实际失败为：

- 断言：`self.assertLessEqual(set(methods), {"GET", "HEAD", "OPTIONS"})`
- 实际：`{"POST"}` 不属于允许集合

## 只读源码证据

- `07_后端/lingyi_service/app/routers/sales_inventory.py:617`：`@router.post("/sales-orders/drafts")`
- `07_后端/lingyi_service/app/routers/sales_inventory.py:659`：`@router.post("/sales-orders/drafts/{draft_id}/cancel")`
- 同一 router 中 POST 分支调用 `_validate_local_sales_order_write_gate`，并使用本地写入/幂等冲突门禁。
- `07_后端/lingyi_service/app/services/sales_inventory_service.py` 包含 `create_sales_order_draft`、`cancel_sales_order_draft`、`get_sales_order_draft_gate_carriers` 等对应服务方法。

## 分类

证据指向测试合同/路由清单断言漂移：当前 router 已存在本地门禁保护的销售订单草稿 POST 路由，而测试仍按早期“全量 sales-inventory 路由只读 GET”合同断言。未发现必须修改业务源码才能完成本轮边界的证据。

- classification：`TEST_CONTRACT_UPDATE_ALLOWED`
- allowed_fix_file：`07_后端/lingyi_service/tests/test_sales_inventory_api.py`
- recommended_next_task：`TASK-Z026B-25-FIX-CAND003`
- run_this_task：NO

## 门禁

- 未修改代码或测试
- 未运行 pytest/npm/browser/build/typecheck/verify
- 未 stage/commit/push/tag/PR/release
- 未 reset/checkout/stash/cleanup
- 未声明 production readback、go-live 或项目完成
