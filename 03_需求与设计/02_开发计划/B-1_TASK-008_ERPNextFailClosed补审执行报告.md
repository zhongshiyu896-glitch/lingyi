# B-1 TASK-008 ERPNext Fail-Closed 补审执行报告

- 任务编号：B-1
- 对应模块：TASK-008 ERPNext Fail-Closed Adapter
- 执行时间：2026-04-16
- 执行角色：工程师（补审执行）
- 基线参考：`384970400f7a137e8384649bd73cab5ae2d33300`

## 一、检查项逐项结论

### 检查项 1：ERPNext timeout / 401 / 403 / 5xx 是否 fail closed
- 结论：✅ 通过
- 证据：
  - `tests/test_erpnext_fail_closed_adapter.py::test_map_timeout_to_erpnext_timeout`
  - `tests/test_erpnext_fail_closed_adapter.py::test_map_http_401_403_to_auth_failed`
  - `tests/test_erpnext_fail_closed_adapter.py::test_map_http_5xx_to_external_unavailable_retryable`
- 说明：错误映射到 `ERPNEXT_TIMEOUT` / `ERPNEXT_AUTH_FAILED` / `EXTERNAL_SERVICE_UNAVAILABLE`，均为失败语义，不存在成功回退。

### 检查项 2：`docstatus` 缺失、非法类型、非法值是否 fail closed
- 结论：✅ 通过
- 证据：
  - `tests/test_erpnext_fail_closed_adapter.py::test_missing_docstatus_fail_closed`
  - `tests/test_erpnext_fail_closed_adapter.py::test_normalize_rejects_malformed_docstatus_literals`
  - `tests/test_erpnext_fail_closed_adapter.py::test_require_submitted_doc_docstatus_0_fails`
  - `tests/test_erpnext_fail_closed_adapter.py::test_require_submitted_doc_docstatus_2_fails`
- 说明：实现中 `_coerce_docstatus()` 仅允许 `0/1/2` 与字符串 `"0"/"1"/"2"`，其余输入触发 `ERPNEXT_DOCSTATUS_INVALID`。

### 检查项 3：malformed response 是否 fail closed
- 结论：✅ 通过
- 证据：
  - `tests/test_erpnext_fail_closed_adapter.py::test_normalize_malformed_response_fail_closed`
- 说明：非 dict/list 或结构异常映射到 `ERPNEXT_RESPONSE_INVALID`，未出现空数据放行。

### 检查项 4：是否禁止 `detail=str(exc)` 泄露
- 结论：✅ 通过
- 证据：
  - 代码扫描命中 `raw_detail=str(exc)`（内部字段）而非 `detail=str(exc)` 对外返回。
  - `ERPNextAdapterException.to_http_detail()` 仅输出 `{code, message, data: null}`。
  - `tests/test_erpnext_fail_closed_adapter.py::test_sensitive_detail_is_redacted_in_safe_message` 覆盖敏感词脱敏。
- 说明：`raw_detail` 用于内部诊断，不在 HTTP detail 对外暴露；`safe_message` 经过脱敏。

### 检查项 5：是否禁止 `200 + 空数据` 伪成功
- 结论：✅ 通过
- 证据：
  - 指定 grep 未发现 `return .*200` / `code.*OK` / `data.*[]` / `data.*{}` 伪成功模式。
  - 适配层失败统一通过异常与错误码返回。
- 说明：未发现将外部失败伪装成成功响应的代码路径。

## 二、测试命令与结果

### 1) pytest
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_erpnext_fail_closed_adapter.py
```
结果：通过（`19 passed, 1 warning`）。

### 2) py_compile
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m py_compile app/services/erpnext_fail_closed_adapter.py app/core/exceptions.py app/core/error_codes.py tests/test_erpnext_fail_closed_adapter.py
```
结果：通过（无报错输出）。

### 3) 审查 grep 与边界检查
```bash
cd /Users/hh/Desktop/领意服装管理系统
grep -R "detail=str(exc)\|return .*200\|code.*OK\|data.*\[\]\|data.*{}" \
  "07_后端/lingyi_service/app/services/erpnext_fail_closed_adapter.py" \
  "07_后端/lingyi_service/app/core/exceptions.py" \
  "07_后端/lingyi_service/app/core/error_codes.py" || true

git diff --name-only -- "06_前端" "07_后端" ".github" "02_源码"
git diff --cached --name-only
```
结果：
- grep 仅命中 `raw_detail=str(exc)`（内部字段）。
- 禁改路径无新增改动输出。
- 暂存区为空。

## 三、发现的问题
- 高危（P1）：0
- 中危（P2）：0
- 低危（P3）：0
- 备注：`raw_detail=str(exc)` 为内部诊断字段，当前未对外泄露，不构成阻断问题。

## 四、是否提交审计官
- 结论：是（提交审计官出具正式审计意见书）。
- 本报告性质：补审执行报告（非审计意见书）。

## 五、2026-04-17 复核补充

- 复核原因：总调度重新下发 B-1 补审任务卡。
- 路径校正：任务卡中的 `07_后端/lingyi_service/app/adapters/erpnext_fail_closed_adapter.py` 在当前仓库不存在；当前实际入库实现路径为 `07_后端/lingyi_service/app/services/erpnext_fail_closed_adapter.py`。
- 本轮未修改业务代码，未暂存，未提交。

### 5.1 本轮逐项复核结论

| 检查项 | 结论 | 说明 |
|---|---|---|
| ERPNext timeout / 401 / 403 / 5xx 是否 fail closed | ✅ 通过 | `map_erpnext_exception()` 将 timeout 映射为 `ERPNEXT_TIMEOUT`，401/403 映射为 `ERPNEXT_AUTH_FAILED`，5xx 映射为 `EXTERNAL_SERVICE_UNAVAILABLE`。 |
| `docstatus` 缺失、非法类型、非法值是否 fail closed | ✅ 通过 | `_coerce_docstatus()` 显式拒绝 `bool`、`float`、空白字符串、`01`、`1.0`、list、dict 等非法值；缺失 docstatus 由 `validate_docstatus()` 返回 `ERPNEXT_DOCSTATUS_REQUIRED`。 |
| malformed response 是否 fail closed | ✅ 通过 | 非 dict/list 结构、非允许 list payload、非 dict data 均返回 `ERPNEXT_RESPONSE_INVALID`。 |
| 是否禁止 `detail=str(exc)` 泄露 | ✅ 通过 | 对外 `to_http_detail()` 只返回 `code/message/data`；`raw_detail=str(exc)` 为内部诊断字段，不在 HTTP detail 输出；敏感信息由 `sanitize_erpnext_error()` 和测试覆盖脱敏。 |
| 是否禁止 `200 + 空数据` 伪成功 | ✅ 通过 | 失败路径统一抛 `ERPNextAdapterException` 并映射错误码，未发现将外部失败伪装为 `200 + 空数据` 的路径。 |

### 5.2 本轮验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_erpnext_fail_closed_adapter.py
.venv/bin/python -m py_compile app/services/erpnext_fail_closed_adapter.py tests/test_erpnext_fail_closed_adapter.py
```

验证结果：

```text
19 passed, 1 warning
py_compile 通过
```

### 5.3 本轮边界检查

```bash
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- "06_前端" "07_后端" ".github" "02_源码"
git diff --cached --name-only
```

结果：空输出。

### 5.4 本轮结论

- 高危：0
- 中危：0
- 低危：0
- 结论：提交审计。
