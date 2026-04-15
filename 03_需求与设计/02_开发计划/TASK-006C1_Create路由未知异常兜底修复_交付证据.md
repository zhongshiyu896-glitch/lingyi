# TASK-006C1 Create 路由未知异常兜底修复 交付证据

## 1. 任务范围与结论
- 任务：修复 `POST /api/factory-statements/` 未知异常兜底路径的 `statement_id` 未定义问题。
- 结论：已完成最小范围修复；未知异常不再触发二次 `NameError`，返回统一错误信封，失败审计可写且不依赖 `statement_id`，并验证无半落库。

## 2. 修改文件清单
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py`

## 3. 阻断点修复说明
### 3.1 `statement_id` 未定义修复
- 位置：`create_factory_statement()` 的 `except Exception` 分支。
- 修复前：失败审计调用 `_record_failure_safely(..., resource_id=statement_id, ...)`，`statement_id` 在 create 路径未定义，导致二次异常。
- 修复后：改为 `_record_failure_safely(..., resource_id=None, ...)`，避免二次异常。

### 3.2 未知异常统一错误信封
- 未知异常分支返回：
  - `code=FACTORY_STATEMENT_INTERNAL_ERROR`
  - `message=加工厂对账单处理失败`
  - `data=null`
- 保持先 `_rollback_safely(session)`，再记录失败审计，最后返回统一错误响应。

## 4. 新增测试与覆盖点
### 4.1 新增测试
- `FactoryStatementAuditTest.test_create_runtime_error_returns_internal_error_envelope_without_partial_writes`

### 4.2 覆盖点
- patch `FactoryStatementService.create_draft` 抛 `RuntimeError`。
- 断言响应为统一错误信封，不是 `NameError`。
- 断言 `code=FACTORY_STATEMENT_INTERNAL_ERROR`。
- 断言 `message=加工厂对账单处理失败`。
- 断言 `data is null`。
- 断言未创建 `ly_factory_statement`。
- 断言未创建 `ly_factory_statement_item`。
- 断言 inspection 未被锁定（仍为 `unsettled`，`statement_id/statement_no` 为空）。
- 断言失败审计写入成功，且 `resource_id` 允许为空。

## 5. 自测命令与结果
### 5.1 工厂对账单定向回归
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_factory_statement*.py
```
- 结果：`41 passed`。

### 5.2 C1 新增用例定向
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_factory_statement_audit.py -k runtime_error
```
- 结果：`1 passed`。

### 5.3 语法编译检查
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```
- 结果：通过。

### 5.4 禁入扫描
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
rg -n "payable-draft|Purchase Invoice|/api/resource/Purchase Invoice|create_purchase_invoice|tabPurchase Invoice" app tests
```
- 结果：无命中。

### 5.5 禁改范围扫描
```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- '06_前端' '.github' '02_源码'
```
- 结果：空输出。

## 6. 边界声明
- 未实现 `POST /api/factory-statements/{id}/payable-draft`。
- 未创建 ERPNext Purchase Invoice。
- 未修改前端目录（`06_前端/**`）。
- 未修改 `.github/**`。
- 未修改 `02_源码/**`。
