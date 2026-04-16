# TASK-011B 销售库存只读后端接口基线实现交付证据

- 任务编号：TASK-011B
- 执行时间：2026-04-16
- 前置：TASK-011A 审计通过
- 结论：待审计

## 一、实现范围

本任务按 TASK-011 设计冻结实现销售/库存只读后端接口基线。

### 新增只读接口

1. `GET /api/sales-inventory/sales-orders`
2. `GET /api/sales-inventory/sales-orders/{name}`
3. `GET /api/sales-inventory/items/{item_code}/stock-summary`
4. `GET /api/sales-inventory/items/{item_code}/stock-ledger`
5. `GET /api/sales-inventory/warehouses`
6. `GET /api/sales-inventory/customers`
7. `GET /api/sales-inventory/diagnostic`（诊断动作，需 `sales_inventory:diagnostic`）

### 新增/修改文件

1. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/sales_inventory.py`
2. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_sales_inventory_adapter.py`
3. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/sales_inventory_service.py`
4. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
5. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
6. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
7. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_permission_adapter.py`
8. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
9. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py`
10. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_adapter.py`
11. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_permissions.py`

## 二、关键边界

1. 本任务仅实现只读查询，不新增 POST/PUT/PATCH/DELETE 业务接口。
2. 未新增 outbox。
3. 未新增数据库迁移。
4. 未写入销售/库存本地业务事实表。
5. ERPNext 调用全部通过只读 GET 路径。
6. Sales Order 强制 `docstatus=1`，缺失或 draft/cancelled fail closed。
7. Stock Ledger Entry 缺少 `company/item_code/warehouse/posting_date/actual_qty/qty_after_transaction` 不纳入结果，并以 `dropped_count` 体现。
8. 详情接口先动作权限，再读取资源，再资源权限校验，避免无动作权限用户通过 403/404 差异探测存在性。
9. 普通 read 成功不写操作审计；依赖不可用、动作拒绝、资源拒绝写安全审计。

## 三、权限与资源范围

新增动作：

1. `sales_inventory:read`
2. `sales_inventory:export`
3. `sales_inventory:diagnostic`

资源字段补齐：

1. `company`
2. `item_code`
3. `warehouse`
4. `customer`

说明：`sales_order` 作为资源编号参与详情审计与防枚举；当前 ERPNext User Permission 基座没有 Sales Order 级授权事实，因此未将其作为 `required_fields` 强校验字段，避免伪校验。

## 四、验证结果

1. `.venv/bin/python -m pytest -q tests/test_sales_inventory_api.py tests/test_sales_inventory_adapter.py tests/test_sales_inventory_permissions.py`
   - 结果：`16 passed, 1 warning`
2. `.venv/bin/python -m pytest -q tests/test_sales_inventory*.py tests/test_permissions*.py tests/test_erpnext_fail_closed_adapter.py`
   - 结果：`44 passed, 1 warning`
3. `.venv/bin/python -m pytest -q`
   - 结果：`831 passed, 13 skipped, 1164 warnings`
4. `.venv/bin/python -m unittest discover`
   - 结果：`Ran 736 tests ... OK (skipped=1)`
5. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过
6. `git diff --check`
   - 结果：通过（空输出）
7. `git diff --name-only -- '06_前端' '.github' '02_源码' '07_后端/lingyi_service/migrations'`
   - 结果：空输出
8. 销售库存只读实现禁写扫描：
   - `@router.post/put/patch/delete`：无命中
   - `request.post/put/patch/delete`：无命中
   - `outbox`：无命中
   - `Stock Entry/Payment Entry/GL Entry/Purchase Invoice`：无业务实现命中

## 五、未进入范围

1. 未开发前端页面。
2. 未新增前端 API 类型。
3. 未新增 ERPNext 写操作。
4. 未新增 outbox。
5. 未新增迁移。
6. 未进入 TASK-012。
7. 未暂存、未提交、未 push。

## 六、剩余说明

1. 全量测试仍存在历史 `datetime.utcnow()` deprecation warnings，非本任务新增。
2. `ERPNextSalesInventoryAdapter` 使用 `/api/resource/*` 仅限后端 ERPNext 只读适配器，不是前端直连，也不是写调用。
