# TASK-164F 仓库成品入仓与 Stock Entry 草稿回归归口报告

## 1. 任务范围

- TASK_ID: `TASK-164F`
- 白名单文件：
  - `06_前端/lingyi-pc/src/api/warehouse.ts`
  - `06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue`
  - `07_后端/lingyi_service/app/routers/warehouse.py`
  - `07_后端/lingyi_service/app/schemas/warehouse.py`
  - `07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`
  - `07_后端/lingyi_service/app/services/warehouse_service.py`
- 文档输出：
  - `03_需求与设计/02_开发计划/TASK-164F_仓库成品入仓与StockEntry草稿回归归口报告.md`
  - `03_需求与设计/02_开发计划/工程师会话日志.md`

## 2. 六文件 diff 摘要（只读）

命令：

`git -C '/Users/hh/Desktop/领意服装管理系统' diff --stat -- '06_前端/lingyi-pc/src/api/warehouse.ts' '06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue' '07_后端/lingyi_service/app/routers/warehouse.py' '07_后端/lingyi_service/app/schemas/warehouse.py' '07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py' '07_后端/lingyi_service/app/services/warehouse_service.py'`

结果：

- `warehouse.ts`: `+138`
- `WarehouseDashboard.vue`: `+292/-1`
- `routers/warehouse.py`: `+76/-1`
- `schemas/warehouse.py`: `+27`
- `erpnext_warehouse_adapter.py`: `+159/-2`
- `warehouse_service.py`: `+195/-22`
- 合计：`6 files changed, 861 insertions(+), 26 deletions(-)`

## 3. 归属关系

- 该组六文件属于历史仓库主链产物：
  - `TASK-050A~TASK-050I`
  - `TASK-090C`
- 本轮执行的是定向回归与归口冻结，不扩展到其他 business diff。

## 4. 定向验证结果

执行结果：

1. 前端（`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`）
   - `npm run typecheck` -> **PASS**
2. 后端编译（`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`）
   - `python3 -m py_compile app/routers/warehouse.py app/schemas/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py` -> **PASS**
3. 后端定向测试（同目录）
   - `.venv/bin/python -m pytest tests/test_warehouse_finished_goods_inbound.py tests/test_warehouse_stock_entry_draft.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_inventory_count.py tests/test_warehouse_readonly_baseline.py tests/test_warehouse_traceability_readonly.py tests/test_warehouse_export_diagnostic.py tests/test_warehouse_worker_permissions.py -v --tb=short`
   - 结果：**PASS**（`74 passed, 1 warning`）

结论：本轮无需在六文件内进行修复。

## 5. 静态业务锚点核对

- `warehouse.ts`：
  - 存在 `finished-goods-inbound-candidates`、`stock-entry-drafts`、`outbox-status` API 封装。
  - 存在 `idempotency_key`、`allocation_mode(strict_alloc/zero_placeholder_fallback)` 等入仓/草稿参数与字段承载。
- `WarehouseDashboard.vue`：
  - 存在“成品入仓”入口与候选加载、草稿创建/详情刷新/Outbox 状态刷新/取消入口。
  - 存在权限 guard：`warehouse:stock_entry_draft`、`warehouse:stock_entry_cancel`，无权限时禁用或提前返回。
  - 未发现前端直接调用 ERPNext 资源路径（无 `/api/resource`、`/api/app/` 直连）。
- `routers/warehouse.py`：
  - 覆盖 `finished-goods-inbound-candidates`、`stock-entry-drafts create/detail/cancel/outbox-status` 路由。
- `schemas/warehouse.py`：
  - 覆盖入仓候选与草稿 outbox 结构，含 `finished_goods_source_id`、`allocation_mode`、`strict_failure_reason`、`show_completed_forced`。
- `erpnext_warehouse_adapter.py`：
  - 覆盖候选接口 payload（含 `showCompleted`）及候选归一化。
- `warehouse_service.py`：
  - 覆盖成品入仓候选、草稿 create/detail/cancel、outbox/worker 边界，分配模式 `strict_alloc -> zero_placeholder_fallback` 闭环。

静态核对结论：**PASS**。

## 6. 归口结论

- `CODE_CHANGED`: `NO`
- `can_reclassify_to`: `HISTORICAL_TASK_OUTPUT_VERIFIED`
- `remaining_unowned_business_diffs_excluded`: `YES`

本报告不覆盖 `sales-inventory / factory-statement / production / style-profit / backend 非白名单 / CCC` 等其他差异。

## 7. 收尾校验

1. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --check -- '06_前端/lingyi-pc/src/api/warehouse.ts' '06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue' '07_后端/lingyi_service/app/routers/warehouse.py' '07_后端/lingyi_service/app/schemas/warehouse.py' '07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py' '07_后端/lingyi_service/app/services/warehouse_service.py'`
   - 结果：**PASS**（无输出）
2. `git -C '/Users/hh/Desktop/领意服装管理系统' diff --name-only -- '06_前端/lingyi-pc/src/api/warehouse.ts' '06_前端/lingyi-pc/src/views/warehouse/WarehouseDashboard.vue' '07_后端/lingyi_service/app/routers/warehouse.py' '07_后端/lingyi_service/app/schemas/warehouse.py' '07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py' '07_后端/lingyi_service/app/services/warehouse_service.py' '03_需求与设计/02_开发计划/TASK-164F_仓库成品入仓与StockEntry草稿回归归口报告.md' '03_需求与设计/02_开发计划/工程师会话日志.md'`
   - 结果：见回交 `CHANGED_FILES` 与范围核对。

## 8. 风险与边界

- 未运行 `npm run dev/build/verify`
- 未运行后端全量测试
- 未触碰其他前端 src/scripts、后端非白名单文件、tests、CCC、控制面、AGENTS、架构师日志、审计官日志、生产/GitHub 管理配置
- 不代表剩余 business tracked diff、REL-004/REL-005、生产联调、ERPNext 生产写入或业务功能放行
