# TASK-050E_FIX2 Batch / Serial No 详情单资源读取 工程任务单

## 1. 基本信息

- 任务编号：TASK-050E_FIX2
- 任务名称：Batch / Serial No 详情单资源读取
- 模块：仓库管理增强 / 批次序列号只读追溯
- 角色：B Engineer
- 优先级：P0
- 前置：TASK-050E_FIX1 审计意见书第393份 `NEEDS_FIX / 高危1`
- 任务性质：fix pass 2，只修复 C 指出的详情读源问题，不扩大功能范围。

## 2. 修复目标

修复第393份审计指出的两个 P1 问题：

1. `get_batch_detail()` 不得再复用 `list_batches(... page_size=1000)` 后本地过滤。
2. `get_serial_number_detail()` 不得再复用 `list_serial_numbers(... page_size=1000)` 后本地过滤。
3. Batch 详情必须通过 ERPNext `Batch/{name}` 或等价单资源只读 GET 路径读取。
4. Serial No 详情必须通过 ERPNext `Serial No/{name}` 或等价单资源只读 GET 路径读取。
5. 测试必须补充详情读源 mock 证据，证明详情方法读取单资源而不是列表查询。

## 3. 允许范围

仅允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_traceability_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止修改 `app/schemas/warehouse.py`，除非发现不改无法修复详情读源；如必须扩范围，立即 `BLOCKED` 回 A。
2. 禁止修改 `app/services/warehouse_service.py`，除非发现不改无法接入单资源详情；如必须扩范围，立即 `BLOCKED` 回 A。
3. 禁止修改 `app/routers/warehouse.py`。
4. 禁止修改前端 `06_前端/**`。
5. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
6. 禁止新增 migration、model、worker、outbox、main.py 映射、权限注册。
7. 禁止创建、修改、删除 ERPNext `Batch` / `Serial No`。
8. 禁止 ERPNext `POST / PUT / PATCH / DELETE`。
9. 禁止 `Stock Entry submit`、`Stock Reconciliation`、`Stock Ledger Entry` 直接写入。
10. 禁止 `GL Entry`、`Payment Entry`、`Purchase Invoice`。
11. 禁止 push / PR / tag / 生产发布。

继承脏基线：

- `06_前端/lingyi-pc/src/router/index.ts` 当前 SHA-256 必须保持：`0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`
- 本任务不得修改该文件。

## 5. 必须实现

### 5.1 Batch 详情单资源读取

在 `app/services/erpnext_warehouse_adapter.py` 中：

1. 新增或复用单资源 GET helper。
2. `get_batch_detail(batch_no=...)` 必须读取 `Batch/{batch_no}` 或等价单资源路径。
3. 读取后仍必须走 `_normalize_batch_row(...)` 或等价 fail-closed 归一化。
4. 返回结构必须保持 service 现有契约：

```python
{
    "batch_no": normalized_batch,
    "company": company,
    "warehouse": warehouse,
    "item_code": item_code,
    "total": 1 或 0,
    "items": [normalized_batch_row]
}
```

5. 若单资源不存在、company / warehouse / item_code 过滤不匹配，必须返回空 items 或项目既有 not found/fail-closed 语义，不得退回列表前 1000 条扫描。

### 5.2 Serial No 详情单资源读取

在 `app/services/erpnext_warehouse_adapter.py` 中：

1. `get_serial_number_detail(serial_no=...)` 必须读取 `Serial No/{serial_no}` 或等价单资源路径。
2. 读取后仍必须走 `_normalize_serial_number_row(...)` 或等价 fail-closed 归一化。
3. 返回结构必须保持 service 现有契约：

```python
{
    "serial_no": normalized_serial,
    "company": company,
    "warehouse": warehouse,
    "item_code": item_code,
    "total": 1 或 0,
    "items": [normalized_serial_row]
}
```

4. 若单资源不存在、company / warehouse / item_code 过滤不匹配，必须返回空 items 或项目既有 not found/fail-closed 语义，不得退回列表前 1000 条扫描。

### 5.3 不能破坏已通过项

必须保持第393份已验证通过的内容：

1. Batch 字段仍包含 `company / batch_no / item_code / warehouse / manufacturing_date / expiry_date / disabled / qty`。
2. Serial No 字段仍包含 `company / serial_no / item_code / warehouse / batch_no / status / delivery_document_no / purchase_document_no`。
3. 列表读源仍为 `Batch` / `Serial No`。
4. TASK-050D 的 `batch_size = Field(default=10, ge=1, le=50)` 与 `skipped_count` 不得回退。
5. 不得新增写调用或写路由。

## 6. 必须测试

在 `tests/test_warehouse_traceability_readonly.py` 补充：

1. `get_batch_detail()` 详情读源测试：mock 单资源 GET helper，断言读取 `Batch` 单资源或等价 `Batch/{name}` 路径。
2. `get_serial_number_detail()` 详情读源测试：mock 单资源 GET helper，断言读取 `Serial No` 单资源或等价 `Serial No/{name}` 路径。
3. 测试必须证明详情方法未调用 `list_batches()` / `list_serial_numbers()` 作为替代路径。
4. 详情返回仍包含原始字段。
5. 单资源 malformed / 缺必需字段时 fail-closed。
6. 原有 13 个 traceability 测试继续通过。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_warehouse_traceability_readonly.py -v --tb=short
rg -n "get_batch_detail|get_serial_number_detail|Batch|Serial No|_get_resource|_read_resource|manufacturing_date|expiry_date|disabled|delivery_document_no|purchase_document_no" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "list_batches\(|list_serial_numbers\(" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.|httpx\.|submit\(|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/services/erpnext_warehouse_adapter.py app/services/warehouse_service.py app/routers/warehouse.py
rg -n "batch_size: int = Field\(default=10, ge=1, le=50\)|skipped_count" app/schemas/warehouse.py app/services/warehouse_service.py
git diff --name-only -- .github 02_源码 04_生产 06_前端
shasum -a 256 '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts'
```

说明：

- `list_batches(` / `list_serial_numbers(` 扫描允许命中列表方法定义和列表测试，但不得在 `get_batch_detail()` / `get_serial_number_detail()` 内部继续调用。
- `06_前端` 如仍命中 `router/index.ts`，必须报告为继承脏基线且 SHA-256 等于 `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`。

## 8. 回交硬门禁

1. 本任务单是 `A -> B` 执行指令，不是 `B -> C` 审计输入。
2. B 未形成真实代码改动、测试改动、验证结果前，禁止回交 C。
3. B 回交必须包含真实 `CHANGED_FILES`、证据路径、测试结果和边界扫描结果。
4. 如果需要修改允许范围之外文件，必须先 `BLOCKED` 回 A，不得自行扩边界。

## 9. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050E_FIX2
ROLE: B Engineer

CHANGED_FILES:
- ...

EVIDENCE:
- get_batch_detail 已改为 Batch 单资源只读读取：路径 + 行号
- get_serial_number_detail 已改为 Serial No 单资源只读读取：路径 + 行号
- 详情读源测试已覆盖 Batch/{name}：路径 + 行号
- 详情读源测试已覆盖 Serial No/{name}：路径 + 行号
- 未回退第393份已通过字段契约：路径 + 行号

VERIFICATION:
- pytest ...：结果
- 详情读源 rg：结果
- list fallback 扫描：结果
- ERPNext 写调用扫描：结果
- TASK-050D 契约保持扫描：结果
- 禁改目录 diff：结果
- router 继承基线 SHA-256：结果

BLOCKERS:
- 无 / 如有写明

NEXT_ROLE:
- C Auditor
```
