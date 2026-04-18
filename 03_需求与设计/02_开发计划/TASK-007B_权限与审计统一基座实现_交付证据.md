# TASK-007B 权限与审计统一基座实现_交付证据

- 任务编号：TASK-007B
- 执行日期：2026-04-16
- 执行结论：待审计

## 1. 修改文件清单

后端公共基座：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

新增测试：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_audit_baseline.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_error_envelope.py`

交付证据：
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-007B_权限与审计统一基座实现_交付证据.md`

## 2. 权限动作新增/保留清单

### 2.1 Sprint 2 P1 新增动作（已注册）
- `permission_audit:read/manage/diagnostic`
- `erpnext_adapter:read/dry_run/diagnostic`
- `outbox:read/retry/manage/dry_run/diagnostic/worker`
- `frontend_contract:read/manage/diagnostic`
- `sales:read/export`
- `inventory:read/export`
- `quality:read/create/update/confirm/cancel/export/dry_run/diagnostic/worker`
- `dashboard:read`

### 2.2 兼容保留
- 保留 TASK-001~006 既有动作集（bom/workshop/subcontract/production/style_profit/factory_statement）。
- `MODULE_ACTION_REGISTRY` 新增统一注册表，同时保留历史角色动作映射。
- `ERP_ROLE_ACTIONS["System Manager"]` 对齐 `DEFAULT_STATIC_ROLE_ACTIONS`，避免双份清单漂移。

## 3. 资源权限统一入口说明

在 `permission_service.py` 新增公共入口：
- `ensure_resource_scope_permission(...)`

统一资源字段支持：
- `company`
- `item_code`
- `supplier`
- `warehouse`
- `work_order`
- `sales_order`
- `bom_id`

统一规则：
1. 校验顺序：动作权限 -> 资源字段完整性 -> 资源权限。
2. 缺关键资源字段：fail closed，返回 `RESOURCE_ACCESS_DENIED`（403）。
3. Company-only 不自动推导 Item 权限：`allowed_companies` 不代表 `allowed_items`。
4. `work_order/sales_order/bom_id` 当前无 ERPNext 授权矩阵时 fail closed。
5. 权限源不可用：返回 `PERMISSION_SOURCE_UNAVAILABLE`（503）。

## 4. 安全审计事件清单

`AuditService.SECURITY_EVENT_TYPES` 已统一覆盖：
- `AUTH_UNAUTHORIZED`（兼容保留）
- `AUTH_UNAUTHENTICATED`
- `AUTH_FORBIDDEN`
- `RESOURCE_ACCESS_DENIED`
- `PERMISSION_SOURCE_UNAVAILABLE`
- `INTERNAL_API_FORBIDDEN`
- `REQUEST_ID_REJECTED`
- `EXTERNAL_SERVICE_UNAVAILABLE`

补充：
- `record_security_audit(...)` 新增 `reason_code`、`resource_scope` 参数。
- `reason_code` 以前缀写入 `deny_reason`；`resource_scope` 安全序列化后附加。

## 5. 操作审计事件清单

`AuditService.OPERATION_EVENT_TYPES` 已统一覆盖：
- `create`
- `update`
- `confirm`
- `cancel`
- `export`
- `dry_run`（兼容增加 `dry-run` 别名）
- `diagnostic`
- `worker_run`
- `retry`

补充：
- `before_data/after_data` 统一经过 `_normalize`。
- `_normalize` 增加敏感字段脱敏：`authorization/cookie/token/secret/password/passwd/pwd/dsn/api_key/private_key`。

## 6. 错误码映射表（本次新增/统一）

- `AUTH_UNAUTHENTICATED` -> 401
- `AUTH_FORBIDDEN` -> 403
- `RESOURCE_ACCESS_DENIED` -> 403
- `RESOURCE_NOT_FOUND` -> 404
- `PERMISSION_SOURCE_UNAVAILABLE` -> 503
- `EXTERNAL_SERVICE_UNAVAILABLE` -> 503
- `DATABASE_READ_FAILED` -> 500
- `DATABASE_WRITE_FAILED` -> 500
- `AUDIT_WRITE_FAILED` -> 500
- `INTERNAL_ERROR` -> 500

兼容说明：
- 保留 `AUTH_UNAUTHORIZED` 作为历史兼容错误码（401）。
- 未强行替换 TASK-001~006 现网既有模块错误码，仅补统一通用码能力。

## 7. 测试命令与结果

### 7.1 定向测试
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_permissions*.py tests/test_audit*.py tests/test_error*.py
```
结果：`26 passed`。

### 7.2 全量 pytest
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q
```
结果：`734 passed, 13 skipped`。

### 7.3 unittest
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m unittest discover
```
结果：`Ran 717 tests ... OK (skipped=1)`。

### 7.4 语法编译
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```
结果：通过。

## 8. 禁改扫描结果

### 8.1 前端/.github/02_源码
```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 06_前端 .github 02_源码
```
结果：空输出（无改动）。

### 8.2 migrations
```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 07_后端/lingyi_service/migrations
```
结果：空输出（无改动）。

### 8.3 敏感信息扫描
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "Authorization|Cookie|Token|Secret|password|passwd|pwd|DSN|API Key|private key" app/services/audit_service.py tests || true
```
结果说明：
- `audit_service.py` 命中为“脱敏关键字常量定义”。
- tests 命中为“反向测试样例/断言文案”。
- 未发现将敏感值明文写入审计落库字段的实现代码路径。

## 9. 剩余风险

1. 全量测试仍存在较多 `datetime.utcnow()` 的 deprecation warnings（历史遗留，未在本任务范围内清理）。
2. 历史模块中部分接口仍返回 `AUTH_FORBIDDEN` 作为资源越权码（兼容保留），后续可在 Sprint2 分模块收敛到 `RESOURCE_ACCESS_DENIED`。
3. 本任务未进入 TASK-008~TASK-012 业务实现，仅完成公共基座能力与测试基线。

