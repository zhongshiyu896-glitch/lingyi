# TASK-Z026B-25-FIX-CAND003 Z026候选003sales-inventory-api测试合同修复报告

## 修复范围

- 候选：`Z026-CAND-003`
- 来源任务：`TASK-Z026B-24-PREP-CAND003-FAILURE-DIAG`
- 允许修改文件：`07_后端/lingyi_service/tests/test_sales_inventory_api.py`
- 实际修改文件：`07_后端/lingyi_service/tests/test_sales_inventory_api.py`

## 修复内容

`test_only_get_routes_are_exposed` 不再把所有 `/api/sales-inventory` 路由统一限制为 `GET/HEAD/OPTIONS`。测试现在显式声明两个当前合法的本地门禁 POST 路由：

- `/api/sales-inventory/sales-orders/drafts`
- `/api/sales-inventory/sales-orders/drafts/{draft_id}/cancel`

测试仍断言：

- 暴露 `POST` 的路由集合必须精确等于上述两个路径。
- 非本地门禁 POST 路由仍只能暴露 `GET/HEAD/OPTIONS`。

未改为任意方法可通过，未 skip、xfail 或删除失败用例。

## 验证

- command：`.venv/bin/python -m pytest tests/test_sales_inventory_api.py -q`
- command_run_count：1
- exit_code：0
- pytest_summary：`15 passed, 1 warning in 1.05s`
- result：PASS
- stdout_log：`03_需求与设计/02_开发计划/task_z026b_25_cand003_fix_stdout.txt`

## 门禁

- 未修改 `06_前端`
- 未修改 `07_后端/lingyi_service/app`
- 未修改其他测试文件
- 未修改共享工程师日志、Z026 candidate pool、B21/B22/B23/B24 产物或既有产物
- 未运行其他 pytest/npm/browser/build/typecheck/verify
- 未 stage/commit/push/tag/PR/release
- 未 reset/checkout/stash/cleanup
- 未声明 production readback、go-live 或项目完成
