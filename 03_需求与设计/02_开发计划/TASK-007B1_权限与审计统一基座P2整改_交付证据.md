# TASK-007B1 权限与审计统一基座 P2 整改交付证据

## 1. 任务信息
- 任务编号：TASK-007B1
- 前置状态：TASK-007B 审计不通过（2 个 P2）
- 整改目标：
  - 修复未知 `required_fields` 被静默跳过问题（必须 fail closed）
  - 修复新增安全事件未接入全局 `HTTPException` fallback 安全审计问题

## 2. P2 问题修复说明

### P2-1 未知 required_fields 静默跳过
- 问题位置：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- 修复内容：
  1. `ensure_resource_scope_permission()` 中，`required_fields` 出现未知字段时，不再 `continue`。
  2. 改为 fail closed：
     - 先写安全审计（`event_type=RESOURCE_ACCESS_DENIED`，`reason_code=RESOURCE_SCOPE_FIELD_UNKNOWN`）
     - 再抛出 `HTTPException(500)`，错误码 `RESOURCE_SCOPE_FIELD_UNKNOWN`。
  3. 资源权限流程不会继续进入放行逻辑。

### P2-2 新安全事件未接入全局 fallback 审计
- 问题位置：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- 修复内容：
  1. 扩展 `SECURITY_AUDIT_CODES`，补入新增安全事件：
     - `AUTH_UNAUTHENTICATED`
     - `RESOURCE_ACCESS_DENIED`
     - `EXTERNAL_SERVICE_UNAVAILABLE`
     - `INTERNAL_API_FORBIDDEN`
     - `REQUEST_ID_REJECTED`
  2. 保留旧兼容事件：
     - `AUTH_UNAUTHORIZED`
     - `AUTH_FORBIDDEN`
     - `PERMISSION_SOURCE_UNAVAILABLE`
  3. 新增 fallback 集成测试：路由直接抛出新增安全 code 的 `HTTPException`，`http_exception_handler()` 可补写安全审计且不泄露敏感字段。

## 3. 错误码补齐
- 文件：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- 新增：
  - `RESOURCE_SCOPE_FIELD_UNKNOWN` -> HTTP 500
  - `INTERNAL_API_FORBIDDEN` -> HTTP 403
  - `REQUEST_ID_REJECTED` -> HTTP 400
- 同步补齐默认 message 映射。

## 4. 修改文件清单
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_audit_baseline.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_error_envelope.py`

## 5. 新增/调整测试清单
- `test_permissions_registry.py`
  - `test_unknown_required_field_fails_closed`
- `test_audit_baseline.py`
  - `test_security_audit_fallback_codes_include_new_events`
  - `test_http_exception_fallback_records_security_audit_for_new_code`
- `test_error_envelope.py`
  - 补充 `RESOURCE_SCOPE_FIELD_UNKNOWN / INTERNAL_API_FORBIDDEN / REQUEST_ID_REJECTED` 状态映射与 fail-closed 断言

## 6. 测试执行结果

### 6.1 定向测试
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_permissions*.py tests/test_audit*.py tests/test_error*.py
```
- 结果：`29 passed`

### 6.2 全量 pytest
```bash
.venv/bin/python -m pytest -q
```
- 结果：`737 passed, 13 skipped`

### 6.3 unittest
```bash
.venv/bin/python -m unittest discover
```
- 结果：`Ran 720 tests ... OK (skipped=1)`

### 6.4 py_compile
```bash
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```
- 结果：通过

## 7. 禁改扫描结果
```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/migrations
git diff --cached --name-only
```
- 前端/.github/02_源码：空输出
- migrations：空输出
- staged：空输出

## 8. 敏感信息审计说明
- 新增 fallback 测试已验证：
  - 审计 `deny_reason` 不包含 `Authorization/Cookie/Token/Secret/password`。
- `rg` 对测试目录命中属于合法测试样例和断言，不是日志泄露。

## 9. 剩余风险
- 全仓仍存在 `datetime.utcnow()` deprecation warning（历史问题，未在 B1 范围处理）。
- 本次仅完成 TASK-007B1 P2 整改，不进入 TASK-008/009/010/011/012。

## 10. 结论
- TASK-007B1 两个 P2 问题已完成整改并通过回归。
- 当前状态：`待审计复核`。
