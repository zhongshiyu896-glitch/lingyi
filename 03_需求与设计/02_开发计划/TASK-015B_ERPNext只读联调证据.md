# TASK-015B ERPNext 只读联调证据

- 执行时间：2026-04-17 13:19:56 CST
- 执行人：Codex（工程师窗口）
- ERPNext 环境：准生产（本机联调站点 `http://127.0.0.1:9081`）
- commit SHA：`220c0737ad28ca85506504b58c134784f09c2fa1`
- 是否写入 ERPNext：否
- 是否修改代码：否
- 是否生产发布：否

## 1. 只读对象验证表

| DocType | API | 查询条件 | 是否成功 | HTTP status | ERPNext response 摘要 | 本地 Adapter 处理结果 | fail-closed 行为 | 是否包含敏感信息 | 是否只读 | 结论 |
|---|---|---|---|---|---|---|---|---|---|---|
| Item | `/api/resource/Item` | `limit_page_length=1; fields=[name,modified]` | 是 | 200 | `name=TPL-TEE-BASIC; keys=[modified,name]` | `normalize_erpnext_response` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Supplier | `/api/resource/Supplier` | `limit_page_length=1; fields=[name,modified]` | 是 | 200 | `name=联意加工厂R19; keys=[modified,name]` | `normalize_erpnext_response` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Customer | `/api/resource/Customer` | `limit_page_length=1; fields=[name,modified]` | 是 | 200 | `name=LY-DEMO-CUSTOMER; keys=[modified,name]` | `normalize_erpnext_response` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Warehouse | `/api/resource/Warehouse` | `limit_page_length=1; fields=[name,modified]` | 是 | 200 | `name=All Warehouses - GF; keys=[modified,name]` | `normalize_erpnext_response` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| BOM | `/api/resource/BOM` | `limit_page_length=1; fields=[name,modified]` | 是 | 200 | `name=BOM-LY-SEMI-CRUD-084720-001; keys=[modified,name]` | `normalize_erpnext_response` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Work Order | `/api/resource/Work Order` | `limit_page_length=1; fields=[name,docstatus,status,modified]` | 是 | 200 | `name=MFG-WO-2026-00001; docstatus=0` | `normalize_erpnext_response + validate_docstatus` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Job Card | `/api/resource/Job Card` | `limit_page_length=1; fields=[name,docstatus,status,modified]` | 是 | 200 | `name=PO-JOB00001; docstatus=0` | `normalize_erpnext_response + validate_docstatus` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Sales Order | `/api/resource/Sales Order` | `limit_page_length=1; fields=[name,docstatus,status,modified]` | 是 | 200 | `name=SAL-ORD-2026-00001; docstatus=0` | `normalize_erpnext_response + validate_docstatus` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Delivery Note | `/api/resource/Delivery Note` | `limit_page_length=1; fields=[name,docstatus,status,modified]` | 是 | 200 | `name=MAT-DN-2026-00001; docstatus=0` | `normalize_erpnext_response + validate_docstatus` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Stock Ledger Entry | `/api/resource/Stock Ledger Entry` | `limit_page_length=1; fields=[name,modified]` | 是 | 200 | `name=MAT-SLE-2026-00001; keys=[modified,name]` | `normalize_erpnext_response` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Account | `/api/resource/Account` | `limit_page_length=1; fields=[name,modified]` | 是 | 200 | `name=Application of Funds (Assets) - GF; keys=[modified,name]` | `normalize_erpnext_response` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Cost Center | `/api/resource/Cost Center` | `limit_page_length=1; fields=[name,modified]` | 是 | 200 | `name=Garment Factory - GF; keys=[modified,name]` | `normalize_erpnext_response` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Purchase Invoice | `/api/resource/Purchase Invoice` | `limit_page_length=1; fields=[name,docstatus,status,modified]` | 是 | 200 | `name=ACC-PINV-2026-00001; docstatus=0` | `normalize_erpnext_response + validate_docstatus` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| Payment Entry | `/api/resource/Payment Entry` | `limit_page_length=1; fields=[name,docstatus,status,modified]` | 是 | 200 | `name=ACC-PAY-2026-00001; docstatus=1` | `normalize_erpnext_response + validate_docstatus` 通过 | 正常路径未触发 | 否 | 是 | 通过 |
| GL Entry | `/api/resource/GL Entry` | `limit_page_length=1; fields=[name,modified]` | 是 | 200 | `name=ACC-GLE-2026-00001; keys=[modified,name]` | `normalize_erpnext_response` 通过 | 正常路径未触发 | 否 | 是 | 通过 |

## 2. Fail-Closed 验证表

| 场景 | 预期 | 实际 | 结论 |
|---|---|---|---|
| ERPNext timeout | `ERPNEXT_TIMEOUT` | `ERPNEXT_TIMEOUT` | 通过 |
| ERPNext 401 | `ERPNEXT_AUTH_FAILED` | `ERPNEXT_AUTH_FAILED` | 通过 |
| ERPNext 403 | `ERPNEXT_AUTH_FAILED` | `ERPNEXT_AUTH_FAILED` | 通过 |
| ERPNext 404 | `ERPNEXT_RESOURCE_NOT_FOUND` | `ERPNEXT_RESOURCE_NOT_FOUND` | 通过 |
| ERPNext 5xx | `EXTERNAL_SERVICE_UNAVAILABLE` | `EXTERNAL_SERVICE_UNAVAILABLE` | 通过 |
| malformed response | `ERPNEXT_RESPONSE_INVALID` | `ERPNEXT_RESPONSE_INVALID` | 通过 |
| docstatus 缺失 | `ERPNEXT_DOCSTATUS_REQUIRED` | `ERPNEXT_DOCSTATUS_REQUIRED` | 通过 |
| docstatus 非法 | `ERPNEXT_DOCSTATUS_INVALID` | `ERPNEXT_DOCSTATUS_INVALID` | 通过 |
| 空数据真实无数据 | `200 + 空列表（真实无数据）` | `200, empty=True` | 通过 |
| 禁止 `200 + 空数据` 伪成功 | 错误必须返回 fail-closed 错误码 | `ERPNEXT_AUTH_FAILED`（未伪装成功） | 通过 |

## 3. 权限验证表

| 场景 | 预期 | 实际 | 结论 |
|---|---|---|---|
| 无权限 Item 不可读取（Guest） | `ERPNEXT_AUTH_FAILED` | `ERPNEXT_AUTH_FAILED` | 通过 |
| 无权限 Supplier 不可读取（Guest） | `ERPNEXT_AUTH_FAILED` | `ERPNEXT_AUTH_FAILED` | 通过 |
| 无权限 Warehouse 不可读取（Guest） | `ERPNEXT_AUTH_FAILED` | `ERPNEXT_AUTH_FAILED` | 通过 |
| 无权限 Sales Order 不可读取（Guest） | `ERPNEXT_AUTH_FAILED` | `ERPNEXT_AUTH_FAILED` | 通过 |
| 权限源不可用 fail-closed | `PERMISSION_SOURCE_UNAVAILABLE` | `PERMISSION_SOURCE_UNAVAILABLE` | 通过 |

补充：资源越权安全审计与权限拒绝路径由回归测试覆盖并通过：
- `tests/test_sales_inventory_permissions.py`
- `tests/test_quality_api.py`

## 4. 敏感信息扫描

| 范围 | 结论 |
|---|---|
| 本文档内容 | 未发现 token/password/cookie/Authorization/API Secret/DSN |
| 联调脚本输出摘要（本次记录） | 未记录真实凭据，仅记录状态码、错误码、脱敏摘要 |
| 回归命令输出 | 未出现敏感凭据 |

## 5. 测试命令与结果

在 `07_后端/lingyi_service` 执行：

1. `.venv/bin/python -m pytest -q tests/test_erpnext_fail_closed_adapter.py`
- 结果：`19 passed, 1 warning`

2. `.venv/bin/python -m pytest -q tests/test_sales_inventory*.py tests/test_quality*.py`
- 结果：`37 passed, 1 warning`

3. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：`PY_COMPILE_OK`

## 6. 问题与风险

1. 本次联调环境为本机准生产联调站点，不等同生产环境。
2. 本次已验证 Guest（无权限）拒绝路径与权限源不可用 fail-closed；生产最小权限账号（非 Administrator）的对象级权限矩阵仍建议在后续任务单中补充专项验证。
3. 本任务仅为只读联调证据，不解冻 `TASK-014C`，不代表 required checks 平台闭环。

## 7. 总结结论

- 15 个只读对象访问验证：通过
- Fail-Closed 10 项验证：通过
- 权限验证：通过
- 敏感信息扫描：通过

结论：提交审计。
