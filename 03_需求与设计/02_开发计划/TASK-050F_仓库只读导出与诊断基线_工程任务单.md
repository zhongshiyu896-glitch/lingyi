# TASK-050F 仓库只读导出与诊断基线 工程任务单

## 1. 基本信息

- 任务编号：TASK-050F
- 任务名称：仓库只读导出与诊断基线
- 模块：仓库管理增强
- 角色：B Engineer
- 优先级：P1
- 前置依赖：TASK-050E_FIX2 审计通过（审计意见书第395份）；TASK-018A 仓库管理增强边界设计
- 当前定位：承接 TASK-018A 第8节 `warehouse:export` / `warehouse:diagnostic` 动作权限与第9节导出安全边界，实现仓库数据只读导出与管理员诊断基线；不允许新增任何库存写入、ERPNext 写入、前端入口或生产发布。

## 2. 任务目标

实现两个后端只读能力：

1. 仓库只读 CSV 导出：允许导出仓库只读数据集，必须执行 `warehouse:export` 权限、资源范围过滤和 CSV 公式注入防护。
2. 仓库诊断接口：允许管理员/诊断权限查看仓库只读链路健康状态，必须执行 `warehouse:diagnostic` 权限，输出不得包含 token / cookie / secret / DSN / Authorization。
3. 所有导出和诊断都不得写 ERPNext，不得创建/提交/取消 Stock Entry，不得改库存事实。

## 3. 允许范围

后端允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`

可新增后端服务文件：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_export_service.py`

测试允许新增：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_export_diagnostic.py`

日志允许追加：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止修改前端 `06_前端/**`。
2. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
3. 禁止新增 migration、model、worker、outbox、权限注册常量；`WAREHOUSE_EXPORT` / `WAREHOUSE_DIAGNOSTIC` 已存在，若缺失再 `BLOCKED` 回 A。
4. 禁止新增 `@router.post` / `@router.put` / `@router.patch` / `@router.delete`。
5. 禁止创建、修改、删除 ERPNext `Warehouse` / `Bin` / `Stock Ledger Entry` / `Stock Entry` / `Batch` / `Serial No`。
6. 禁止 ERPNext `POST / PUT / PATCH / DELETE`。
7. 禁止 `Stock Entry submit`、`Stock Reconciliation`、`Stock Ledger Entry` 直接写入。
8. 禁止 `GL Entry`、`Payment Entry`、`Purchase Invoice`。
9. 禁止导出泄露 Authorization、Cookie、token、secret、password、DSN。
10. 禁止 push / PR / tag / 生产发布。

继承脏基线：

- `06_前端/lingyi-pc/src/router/index.ts` 当前 SHA-256 必须保持：`0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`
- 本任务不得修改该文件。

## 5. 必须实现

### 5.1 仓库只读 CSV 导出

新增或实现：

- `GET /api/warehouse/export`

参数建议：

- `dataset`: `stock_ledger | stock_summary | alerts | batches | serial_numbers | traceability`
- `company`: 可选
- `warehouse`: 可选
- `item_code`: 可选
- `batch_no`: 可选，仅适用于 batches / serial_numbers / traceability
- `serial_no`: 可选，仅适用于 serial_numbers / traceability
- `from_date`: 可选，仅适用于 stock_ledger / traceability
- `to_date`: 可选，仅适用于 stock_ledger / traceability
- `alert_type`: 可选，仅适用于 alerts
- `limit`: 默认 500，最大 5000

要求：

1. 必须校验 `warehouse:export`。
2. 必须沿用仓库资源范围过滤：`company / warehouse / item_code / batch_no / serial_no`。
3. 必须复用现有只读 service/adapter 查询，不得新增写入查询路径。
4. 只要求 CSV；不得为了 Excel 引入大范围依赖或前端改动。
5. CSV 必须 UTF-8，包含表头。
6. CSV 单元格防公式注入：以 `=`, `+`, `-`, `@`, tab, carriage-return 开头的字符串必须转义，例如前缀 `'`。
7. 文件名不得包含用户输入原文，避免路径/响应头注入。
8. 空结果返回空 CSV 表头，不得报 500。

### 5.2 仓库诊断接口

新增或实现：

- `GET /api/warehouse/diagnostic`

要求：

1. 必须校验 `warehouse:diagnostic`。
2. 不得暴露到前端普通菜单；本任务不改前端。
3. 返回只读诊断摘要，建议包含：
   - `adapter_configured`: bool
   - `supported_datasets`: list[str]
   - `export_supported_formats`: list[str]
   - `write_boundary`: 固定说明 no_erpnext_write / no_submit / no_stock_reconciliation
   - `last_checked_at`: ISO 时间
4. 可选执行轻量只读 smoke，但不得要求真实 ERPNext 可用才能通过单元测试。
5. 任何异常必须 fail-closed，且错误响应不得包含 token / cookie / secret / DSN。

### 5.3 main.py 动作映射

在 `app/main.py` 仅允许补齐仓库路径动作映射：

1. `/api/warehouse/export` -> `warehouse:export`
2. `/api/warehouse/diagnostic` -> `warehouse:diagnostic`
3. 其他仓库 GET 仍可保持现状或最小映射为 `warehouse:read`，但不得影响既有 worker 映射。

## 6. 必须测试

新增 `tests/test_warehouse_export_diagnostic.py`，覆盖：

1. 无 `warehouse:export` 访问 `/api/warehouse/export` 返回 403。
2. 有 `warehouse:export` 时可导出 stock_summary 或 stock_ledger CSV。
3. 导出会执行 company / warehouse / item_code 过滤。
4. CSV 公式注入字符被转义。
5. 导出响应头 `Content-Type` 与 `Content-Disposition` 合规，文件名不含用户输入原文。
6. 无 `warehouse:diagnostic` 访问 `/api/warehouse/diagnostic` 返回 403。
7. 有 `warehouse:diagnostic` 时返回诊断摘要且不包含 secret/token/cookie/Authorization/DSN。
8. `main.py` 动作映射测试：export/diagnostic 路径能映射到 `warehouse:export` / `warehouse:diagnostic`。
9. 负向扫描证明未新增 ERPNext 写调用、未新增写路由。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_warehouse_export_diagnostic.py tests/test_permissions_registry.py -v --tb=short
rg -n "warehouse:export|warehouse:diagnostic|WAREHOUSE_EXPORT|WAREHOUSE_DIAGNOSTIC|/api/warehouse/export|/api/warehouse/diagnostic" app/routers/warehouse.py app/services/warehouse_service.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
rg -n "^[^#]*(Authorization|Cookie|token|secret|password|DSN|dsn)" app/routers/warehouse.py app/services/warehouse_service.py app/services/warehouse_export_service.py app/main.py tests/test_warehouse_export_diagnostic.py
rg -n "@router\.(post|put|patch|delete)" app/routers/warehouse.py
rg -n "method=\"(POST|PUT|PATCH|DELETE)\"|requests\.|httpx\.|submit\(|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry.*insert|GL Entry|Payment Entry|Purchase Invoice" app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/services/warehouse_export_service.py
git diff --name-only -- .github 02_源码 04_生产 06_前端
shasum -a 256 '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts'
```

说明：

- `@router.post` 如命中 TASK-050B/TASK-050C/TASK-050D 既有写路由，不直接构成本任务失败；B 必须说明本轮未新增写路由。
- secret/token 扫描如命中“禁止泄露”的测试断言文本，需要说明为测试负向断言，不得在响应样本中出现真实敏感值。
- `06_前端` 如仍命中 `router/index.ts`，必须报告为继承脏基线且 SHA-256 等于 `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`。

## 8. 回交硬门禁

1. 本任务单是 `A -> B` 执行指令，不是 `B -> C` 审计输入。
2. B 未形成真实代码改动、测试改动、验证结果前，禁止回交 C。
3. B 回交必须包含真实 `CHANGED_FILES`、证据路径、测试结果和边界扫描结果。
4. 如果需要修改允许范围之外文件，必须先 `BLOCKED` 回 A，不得自行扩边界。

## 9. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050F
ROLE: B Engineer

CHANGED_FILES:
- ...

EVIDENCE:
- 仓库导出接口：路径 + 行号
- warehouse:export 权限校验：路径 + 行号
- CSV 公式注入防护：路径 + 行号
- 仓库诊断接口：路径 + 行号
- warehouse:diagnostic 权限校验：路径 + 行号
- main.py export/diagnostic 动作映射：路径 + 行号
- 测试覆盖：路径 + 行号

VERIFICATION:
- pytest ...：结果
- export/diagnostic rg：结果
- secret/token 泄露扫描：结果
- 写路由扫描：结果
- ERPNext 写调用扫描：结果
- 禁改目录 diff：结果
- router 继承基线 SHA-256：结果

BLOCKERS:
- 无 / 如有写明

NEXT_ROLE:
- C Auditor
```
