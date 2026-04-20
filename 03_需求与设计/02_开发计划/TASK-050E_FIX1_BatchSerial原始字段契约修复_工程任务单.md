# TASK-050E_FIX1 Batch / Serial No 原始字段契约修复 工程任务单

## 1. 基本信息

- 任务编号：TASK-050E_FIX1
- 任务名称：Batch / Serial No 原始字段契约修复
- 模块：仓库管理增强 / 批次序列号只读追溯
- 角色：B Engineer
- 优先级：P0
- 前置：TASK-050E 审计意见书第391份 `NEEDS_FIX / 高危1`
- 任务性质：fix pass 1，只修复 C 指出的 Batch / Serial No 原始只读字段契约偏差，不扩大功能范围。

## 2. 修复目标

修复第391份审计指出的三个问题：

1. Batch 列表/详情不能再只返回 Stock Ledger 聚合字段，必须返回任务单要求的 Batch 原始只读字段：
   - `company`
   - `batch_no`
   - `item_code`
   - `warehouse`
   - `manufacturing_date`
   - `expiry_date`
   - `disabled`
   - `qty`
2. Serial No 列表/详情不能再只返回 Stock Ledger 聚合字段，必须返回任务单要求的 Serial No 原始只读字段：
   - `company`
   - `serial_no`
   - `item_code`
   - `warehouse`
   - `batch_no`
   - `status`
   - `delivery_document_no`
   - `purchase_document_no`
3. Adapter 的 `list_batches` / `get_batch_detail` / `list_serial_numbers` / `get_serial_number_detail` 必须读取 ERPNext `Batch` / `Serial No` 只读资源，不得用 `Stock Ledger Entry` 聚合结果替代 Batch / Serial No 原始字段。

## 3. 允许范围

仅允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_traceability_readonly.py`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止修改前端 `06_前端/**`。
2. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
3. 禁止修改 `app/routers/warehouse.py`。如发现不改 router 无法完成契约修复，立即 `BLOCKED` 回报 A，不得自行扩范围。
4. 禁止新增 migration、model、worker、outbox、main.py 映射、权限注册。
5. 禁止新增或修改任何写路由。
6. 禁止创建、修改、删除 ERPNext `Batch` / `Serial No`。
7. 禁止 ERPNext `POST / PUT / PATCH / DELETE`。
8. 禁止 `Stock Entry submit`、`Stock Reconciliation`、`Stock Ledger Entry` 直接写入。
9. 禁止 `GL Entry`、`Payment Entry`、`Purchase Invoice`。
10. 禁止 push / PR / tag / 生产发布。

继承脏基线：

- `06_前端/lingyi-pc/src/router/index.ts` 当前 SHA-256 必须保持：`0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`
- 本任务不得修改该文件。

## 5. 必须实现

### 5.1 Schema 字段契约

在 `app/schemas/warehouse.py` 中调整 Batch / Serial No 响应模型。

Batch 响应 item 至少必须包含：

```python
company: str
batch_no: str
item_code: str
warehouse: str
manufacturing_date: date | None
expiry_date: date | None
disabled: bool
qty: Decimal
```

Serial No 响应 item 至少必须包含：

```python
company: str
serial_no: str
item_code: str
warehouse: str
batch_no: str | None
status: str
delivery_document_no: str | None
purchase_document_no: str | None
```

注意：

1. 如保留历史聚合字段，不能替代上述必需字段。
2. 列表与详情返回都必须满足上述字段契约。
3. 字段命名必须与任务单一致，不得改成前端自定义别名。

### 5.2 Adapter 只读查询源

在 `app/services/erpnext_warehouse_adapter.py` 中修复读源：

1. `list_batches(...)` 必须调用 ERPNext `Batch` 资源只读查询。
2. `get_batch_detail(...)` 必须调用 ERPNext `Batch` 资源只读查询。
3. `list_serial_numbers(...)` 必须调用 ERPNext `Serial No` 资源只读查询。
4. `get_serial_number_detail(...)` 必须调用 ERPNext `Serial No` 资源只读查询。
5. `list_traceability_entries(...)` 可以继续读取 `Stock Ledger Entry`，但不得反向替代 Batch / Serial No 列表和详情。

允许的 ERPNext 资源读：

```text
GET /api/resource/Batch
GET /api/resource/Batch/{name}
GET /api/resource/Serial No
GET /api/resource/Serial No/{name}
GET /api/resource/Stock Ledger Entry
```

禁止：

```text
POST /api/resource/Batch
PUT /api/resource/Batch
PATCH /api/resource/Batch
DELETE /api/resource/Batch
POST /api/resource/Serial No
PUT /api/resource/Serial No
PATCH /api/resource/Serial No
DELETE /api/resource/Serial No
```

### 5.3 Service 映射

在 `app/services/warehouse_service.py` 中同步映射：

1. Batch 列表 / 详情必须把 `manufacturing_date`、`expiry_date`、`disabled`、`qty` 原样带入响应模型。
2. Serial No 列表 / 详情必须把 `status`、`delivery_document_no`、`purchase_document_no` 原样带入响应模型。
3. `company / warehouse / item_code / batch_no / serial_no` 过滤语义保持不变。
4. ERPNext 返回缺少必需字段时必须 fail-closed，不得静默补默认值制造假数据。
5. Authorization / Cookie / token 不得写入日志、异常消息或测试快照。

## 6. 必须测试

在 `tests/test_warehouse_traceability_readonly.py` 补充或修正测试，至少覆盖：

1. Batch 列表返回字段包含：`company / batch_no / item_code / warehouse / manufacturing_date / expiry_date / disabled / qty`。
2. Batch 详情返回字段包含：`company / batch_no / item_code / warehouse / manufacturing_date / expiry_date / disabled / qty`。
3. Serial No 列表返回字段包含：`company / serial_no / item_code / warehouse / batch_no / status / delivery_document_no / purchase_document_no`。
4. Serial No 详情返回字段包含：`company / serial_no / item_code / warehouse / batch_no / status / delivery_document_no / purchase_document_no`。
5. Adapter 测试或 mock 证据必须证明 Batch / Serial No 列表与详情读取 `Batch` / `Serial No` 资源，而不是 `Stock Ledger Entry` 聚合结果。
6. Batch 缺少 `manufacturing_date` / `expiry_date` / `disabled` / `qty` 等必需字段时 fail-closed。
7. Serial No 缺少 `status` / `delivery_document_no` / `purchase_document_no` 等必需字段时 fail-closed。
8. Traceability 只读流水原测试继续通过。
9. 无新增 ERPNext 写调用、无新增写路由。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_warehouse_traceability_readonly.py -v --tb=short
rg -n "manufacturing_date|expiry_date|disabled|qty|status|delivery_document_no|purchase_document_no" app/schemas/warehouse.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_service.py tests/test_warehouse_traceability_readonly.py
rg -n "doctype=.*Batch|doctype=.*Serial No|/api/resource/Batch|/api/resource/Serial%20No|/api/resource/Serial No" app/services/erpnext_warehouse_adapter.py tests/test_warehouse_traceability_readonly.py
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.|httpx\.|submit\(|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/services/erpnext_warehouse_adapter.py app/services/warehouse_service.py app/routers/warehouse.py
git diff --name-only -- .github 02_源码 04_生产 06_前端
shasum -a 256 '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts'
```

说明：

- `@router.post` 如命中 TASK-050B/TASK-050C/TASK-050D 既有写路由，不直接构成本 fix pass 失败；B 必须说明本轮未新增写路由。
- `06_前端` 如仍命中 `router/index.ts`，必须报告为继承脏基线且 SHA-256 等于 `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`。

## 8. 回交硬门禁

1. 本任务单是 `A -> B` 执行指令，不是 `B -> C` 审计输入。
2. B 未形成真实代码改动、测试改动、验证结果前，禁止回交 C。
3. B 回交必须包含真实 `CHANGED_FILES`、证据路径、测试结果和边界扫描结果。
4. 如果需要修改允许范围之外文件，必须先 `BLOCKED` 回 A，不得自行扩边界。

## 9. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050E_FIX1
ROLE: B Engineer

CHANGED_FILES:
- ...

EVIDENCE:
- Batch schema 已补齐原始字段：路径 + 行号
- Serial No schema 已补齐原始字段：路径 + 行号
- Adapter 已改为读取 Batch / Serial No 资源：路径 + 行号
- Service 映射已带出必需字段：路径 + 行号
- 测试已覆盖列表/详情字段与 fail-closed：路径 + 行号

VERIFICATION:
- pytest ...：结果
- 字段契约 rg：结果
- Adapter 读源 rg：结果
- 写路由扫描：结果
- ERPNext 写调用扫描：结果
- 禁改目录 diff：结果
- router 继承基线 SHA-256：结果

BLOCKERS:
- 无 / 如有写明

NEXT_ROLE:
- C Auditor
```
