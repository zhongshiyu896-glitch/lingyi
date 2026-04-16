# TASK-011B1 销售库存 Customer 权限与详情防枚举整改交付证据

- 任务编号：TASK-011B1
- 执行时间：2026-04-16
- 前置：TASK-011B 审计不通过，需修复 Customer 权限 fail-open 与详情 403/404 存在性差异
- 结论：待审计

## 一、整改范围

本任务仅整改 TASK-011B 审计发现项，不扩展销售库存功能边界。

### Finding 1：Customer 资源权限 fail-open

整改内容：

1. `ERPNextPermissionAdapter.is_customer_permitted()` 已改为 fail-closed：
   - `unrestricted=True` 仍放行。
   - `allowed_customers` 非空时仅允许集合内 Customer。
   - `allowed_customers` 为空且处于 restricted 权限事实时拒绝，不再默认放行。
2. 客户列表 `/api/sales-inventory/customers` 继续通过 `_scope_allowed()` 过滤，因此空 Customer 权限事实会返回空列表，不泄露客户清单。
3. 新增测试覆盖：
   - `test_empty_customer_permissions_fail_closed`
   - `test_customers_empty_customer_permissions_filter_all`

### Finding 2：销售订单详情 403/404 差异泄露存在性

整改内容：

1. `GET /api/sales-inventory/sales-orders/{name}` 保持动作权限前置，未授权用户仍不触发 ERPNext 读取。
2. 对已具备 `sales_inventory:read` 动作但资源越权的用户：
   - 仍调用统一资源权限校验并写 `RESOURCE_ACCESS_DENIED` 安全审计。
   - 对外响应转换为统一 `404 + ERPNEXT_RESOURCE_NOT_FOUND`，与 ERPNext 不存在响应形态一致。
3. 新增测试覆盖：
   - `test_detail_resource_denied_returns_not_found_to_hide_existence`
   - `test_detail_not_found_and_out_of_scope_share_not_found_shape`

## 二、修改文件

1. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_permission_adapter.py`
2. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/sales_inventory.py`
3. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_api.py`
4. `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_sales_inventory_permissions.py`

## 三、验证结果

1. `.venv/bin/python -m pytest -q tests/test_sales_inventory_api.py tests/test_sales_inventory_adapter.py tests/test_sales_inventory_permissions.py`
   - 结果：`19 passed, 1 warning`
2. `.venv/bin/python -m pytest -q tests/test_sales_inventory*.py tests/test_permissions*.py tests/test_erpnext_fail_closed_adapter.py`
   - 结果：`47 passed, 1 warning`
3. `.venv/bin/python -m pytest -q`
   - 结果：`834 passed, 13 skipped, 1164 warnings`
4. `.venv/bin/python -m unittest discover`
   - 结果：`Ran 739 tests ... OK (skipped=1)`
5. `.venv/bin/python -m py_compile app/routers/sales_inventory.py app/services/erpnext_permission_adapter.py tests/test_sales_inventory_api.py tests/test_sales_inventory_permissions.py`
   - 结果：通过
6. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

## 四、边界扫描

1. `git diff --check`
   - 结果：通过
2. `git diff --name-only -- '06_前端' '.github' '02_源码' '07_后端/lingyi_service/migrations'`
   - 结果：空输出
3. 销售库存只读禁写扫描：
   - `@router.post/put/patch/delete`：无命中
   - `request.post/put/patch/delete`：无命中
   - `outbox`：无命中
   - `Stock Entry/Payment Entry/GL Entry/Purchase Invoice`：无业务实现命中

## 五、未进入范围

1. 未修改前端页面或前端 API。
2. 未新增 ERPNext 写操作。
3. 未新增 outbox。
4. 未新增数据库迁移。
5. 未进入 TASK-012。
6. 未暂存、未提交、未 push。

## 六、剩余说明

1. 全量测试仍存在历史 `datetime.utcnow()` deprecation warnings，非本任务新增。
2. `unittest discover` 仍输出历史 sqlite ResourceWarning，非本任务新增。
