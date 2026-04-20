# TASK-050E 仓库批次序列号只读追溯基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-050E
- 任务名称：仓库批次序列号只读追溯基线
- 模块：仓库管理增强
- 角色：B Engineer
- 优先级：P1
- 前置依赖：TASK-050D_FIX1 审计通过（审计意见书第389份）；TASK-018A 仓库管理增强边界设计
- 当前定位：承接 TASK-018A 第5节批次与序列号边界，实现只读查询与追溯基线；不允许创建、修改、冻结、报废 Batch / Serial No，不允许任何 ERPNext 写入。

## 2. 任务目标

实现仓库批次/序列号只读追溯能力：

1. 查询 Batch 列表与详情。
2. 查询 Serial No 列表与详情。
3. 基于 `company / warehouse / item_code / batch_no / serial_no` 查询只读库存追溯流水。
4. 所有接口执行 `warehouse:read` 权限与 company / warehouse 范围过滤。
5. ERPNext 不可用、返回畸形或字段缺失时 fail-closed。
6. 全链路不提供任何写操作入口。

## 3. 允许范围

后端允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`

测试允许新增：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_traceability_readonly.py`

日志允许追加：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止修改前端 `06_前端/**`。
2. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
3. 禁止新增 migration、model、worker、outbox、main.py 映射、权限注册。
4. 禁止新增 `@router.post` / `@router.put` / `@router.patch` / `@router.delete`。
5. 禁止创建、修改、删除 ERPNext `Batch` / `Serial No`。
6. 禁止 `Stock Entry submit`、`Stock Reconciliation`、`Stock Ledger Entry` 直接写入。
7. 禁止 `GL Entry`、`Payment Entry`、`Purchase Invoice`。
8. 禁止 push / PR / tag / 生产发布。

继承脏基线：

- `06_前端/lingyi-pc/src/router/index.ts` 当前 SHA-256 必须保持：`0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`
- 本任务不得修改该文件。

## 5. 必须实现

### 5.1 Batch 只读接口

新增：

- `GET /api/warehouse/batches`
- `GET /api/warehouse/batches/{batch_no}`

要求：

1. 使用 `warehouse:read` 权限。
2. 支持过滤：`company`、`item_code`、`warehouse`、`batch_no`、`page`、`page_size`。
3. 返回字段至少包括：`company`、`batch_no`、`item_code`、`warehouse`、`manufacturing_date`、`expiry_date`、`disabled`、`qty`。
4. ERPNext 返回缺少关键字段时 fail-closed。

### 5.2 Serial No 只读接口

新增：

- `GET /api/warehouse/serial-numbers`
- `GET /api/warehouse/serial-numbers/{serial_no}`

要求：

1. 使用 `warehouse:read` 权限。
2. 支持过滤：`company`、`item_code`、`warehouse`、`serial_no`、`batch_no`、`page`、`page_size`。
3. 返回字段至少包括：`company`、`serial_no`、`item_code`、`warehouse`、`batch_no`、`status`、`delivery_document_no`、`purchase_document_no`。
4. ERPNext 返回缺少关键字段时 fail-closed。

### 5.3 追溯流水只读接口

新增：

- `GET /api/warehouse/traceability`

要求：

1. 使用 `warehouse:read` 权限。
2. 至少支持以下过滤：`company`、`warehouse`、`item_code`、`batch_no`、`serial_no`、`from_date`、`to_date`。
3. 数据来源只允许 ERPNext 只读 `Stock Ledger Entry` / `Batch` / `Serial No`。
4. 返回按 posting_date 倒序的只读流水，字段至少包含：`posting_date`、`voucher_type`、`voucher_no`、`warehouse`、`item_code`、`batch_no`、`serial_no`、`actual_qty`、`qty_after_transaction`。
5. 不得从本地推断或覆盖 ERPNext 库存事实。

## 6. Adapter 要求

在 `erpnext_warehouse_adapter.py` 中只允许新增 GET 查询方法，例如：

- `list_batches(...)`
- `get_batch(...)`
- `list_serial_numbers(...)`
- `get_serial_number(...)`
- `list_traceability_entries(...)`

要求：

1. 只能使用 `GET /api/resource/...`。
2. 禁止任何 `POST / PUT / PATCH / DELETE`。
3. Authorization / Cookie 不得写入日志或响应。
4. ERPNext unavailable / malformed / timeout 统一 fail-closed。

## 7. 必须测试

新增 `tests/test_warehouse_traceability_readonly.py`，覆盖：

1. Batch 列表按 company / warehouse / item_code 过滤。
2. Batch 详情命中时返回字段完整。
3. Serial No 列表按 company / warehouse / item_code / batch_no 过滤。
4. Serial No 详情命中时返回字段完整。
5. Traceability 按 batch_no 或 serial_no 返回只读流水。
6. 无 `warehouse:read` 返回 403。
7. ERPNext malformed 响应 fail-closed。
8. 代码中无写路由、无 ERPNext 写调用。

## 8. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_warehouse_traceability_readonly.py -v --tb=short
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.|httpx\.|/api/resource/(Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice)" app/services/erpnext_warehouse_adapter.py app/services/warehouse_service.py app/routers/warehouse.py
rg -n "submit\(|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/services/erpnext_warehouse_adapter.py app/services/warehouse_service.py app/routers/warehouse.py
git diff --name-only -- .github 02_源码 04_生产 06_前端
shasum -a 256 '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts'
```

说明：`@router.post` 如命中 TASK-050B/TASK-050D 既有写路由，不直接构成本任务失败；C 审计时应确认 TASK-050E 未新增写路由。`06_前端` 如仍命中 `router/index.ts`，必须报告为继承脏基线且 SHA-256 等于 `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`。

## 9. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050E
ROLE: B Engineer

CHANGED_FILES:
- ...

EVIDENCE:
- Batch 列表/详情接口：路径 + 行号
- Serial No 列表/详情接口：路径 + 行号
- Traceability 接口：路径 + 行号
- Adapter 只读方法：路径 + 行号
- 权限与 fail-closed 测试：路径 + 行号

VERIFICATION:
- pytest ...：结果
- 写路由扫描：结果
- ERPNext 写调用扫描：结果
- 禁止写语义扫描：结果
- 禁改目录 diff：结果
- router 继承基线 SHA-256：结果

BLOCKERS:
- 无 / 如有写明

NEXT_ROLE:
- C Auditor
```
