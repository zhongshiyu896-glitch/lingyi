# TASK-008B ERPNext Fail-Closed Adapter 公共实现交付证据

## 1. 任务结论
- 结论：待审计
- 范围：后端公共 fail-closed adapter 与配套测试
- 本次未进入：TASK-009 / TASK-010 / TASK-011 / TASK-012

## 2. 修改文件清单
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_fail_closed_adapter.py`（新增）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_erpnext_fail_closed_adapter.py`（新增）
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`

## 3. 公共 Adapter API 清单
- `normalize_erpnext_response(...)`
- `validate_docstatus(...)`
- `require_submitted_doc(...)`
- `map_erpnext_exception(...)`
- `sanitize_erpnext_error(...)`
- `is_retryable_erpnext_error(...)`
- 数据结构：`ERPNextNormalizedResult`
- 异常结构：`ERPNextAdapterException`

## 4. 错误码映射表
- `ERPNEXT_TIMEOUT` -> HTTP 503
- `ERPNEXT_AUTH_FAILED` -> HTTP 503
- `ERPNEXT_RESOURCE_NOT_FOUND` -> HTTP 404
- `ERPNEXT_RESPONSE_INVALID` -> HTTP 502
- `ERPNEXT_DOCSTATUS_REQUIRED` -> HTTP 409
- `ERPNEXT_DOCSTATUS_INVALID` -> HTTP 409
- `EXTERNAL_SERVICE_UNAVAILABLE` -> HTTP 503

异常映射策略：
- timeout -> `ERPNEXT_TIMEOUT`
- connection error / ERPNext 5xx -> `EXTERNAL_SERVICE_UNAVAILABLE`
- ERPNext 401/403 -> `ERPNEXT_AUTH_FAILED`
- ERPNext 404 -> `ERPNEXT_RESOURCE_NOT_FOUND`
- malformed response / decode error -> `ERPNEXT_RESPONSE_INVALID`

## 5. docstatus/status 矩阵
- `docstatus=1`：通过 submitted 校验
- `docstatus=0`：`require_submitted_doc` 下 fail closed（`ERPNEXT_DOCSTATUS_INVALID`）
- `docstatus=2`：`require_submitted_doc` 下 fail closed（`ERPNEXT_DOCSTATUS_INVALID`）
- 缺 `docstatus`：默认 fail closed（`ERPNEXT_DOCSTATUS_REQUIRED`）
- status-only：仅在 `status_only_whitelist[doctype]` 明确声明时放行
- whitelist 未命中：fail closed

## 6. 测试命令与结果
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

1. `.venv/bin/python -m pytest -q tests/test_erpnext_fail_closed_adapter.py`
- 结果：`17 passed`

2. `rg --files tests | rg 'erpnext|permissions|factory_statement|style_profit|subcontract|workshop|production' | xargs .venv/bin/python -m pytest -q`
- 结果：`657 passed, 13 skipped`

3. `.venv/bin/python -m pytest -q`
- 结果：`754 passed, 13 skipped`

4. `.venv/bin/python -m unittest discover`
- 结果：`Ran 720 tests ... OK (skipped=1)`

5. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

## 7. 禁改扫描结果
在 `/Users/hh/Desktop/领意服装管理系统` 执行：
- `git diff --name-only -- 06_前端 .github 02_源码` -> 空输出
- `git diff --name-only -- 07_后端/lingyi_service/migrations` -> 空输出
- `git diff --cached --name-only` -> 空输出

结论：未修改前端 / .github / 02_源码 / migrations。

## 8. 敏感信息扫描结果
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：
- `rg -n "Authorization|Cookie|Token|Secret|password|passwd|pwd|DSN|API Key|private key" app/services/erpnext_fail_closed_adapter.py tests/test_erpnext_fail_closed_adapter.py || true`

命中说明：
- 仅命中测试用恶意样本文本与断言（用于验证脱敏），不属于运行期日志泄露。
- `erpnext_fail_closed_adapter.py` 运行逻辑通过 `sanitize_erpnext_error` 做敏感信息防泄露。

## 9. 未接入旧 Adapter 遗留清单
本次先落公共基座，未对以下既有 adapter 做全面迁移：
- `erpnext_permission_adapter.py`
- `erpnext_stock_entry_service.py`
- `erpnext_job_card_adapter.py`
- `erpnext_production_adapter.py`
- `erpnext_purchase_invoice_adapter.py`
- `erpnext_style_profit_adapter.py`

说明：本次保持 TASK-002~006 对外契约稳定，后续可分批接入公共基座函数并补针对性回归。

## 10. 剩余风险
- 旧 adapter 仍存在分散的错误映射逻辑，尚未全部收敛到公共 fail-closed 模块。
- 全量回归存在既有 `datetime.utcnow()` deprecation warnings（历史问题，未在本任务处理）。
- `unittest discover` 有历史 ResourceWarning（未影响结果，但建议后续专项清理）。
