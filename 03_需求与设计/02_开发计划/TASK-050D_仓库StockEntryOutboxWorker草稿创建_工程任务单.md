# TASK-050D 仓库 Stock Entry Outbox Worker 草稿创建 工程任务单

## 1. 基本信息

- 任务编号：TASK-050D
- 任务名称：仓库 Stock Entry Outbox Worker 草稿创建
- 模块：仓库管理增强
- 角色：B Engineer
- 优先级：P0
- 前置依赖：TASK-050C 审计通过（审计意见书第385份）；TASK-018A 仓库管理增强边界设计
- 当前定位：承接 TASK-050B 的本地 Stock Entry 草稿 Outbox，实现受控 internal run-once worker，仅允许在 ERPNext 创建 `Stock Entry` 草稿，不允许 submit / Stock Reconciliation / 财务写入 / 生产发布。

## 2. 任务目标

实现仓库 Stock Entry Outbox 的内部消费链路：

1. 从 `ly_warehouse_stock_entry_outbox_event` 领取 `in_pending` 或可重试 `failed` 事件。
2. 调用仓库 ERPNext Adapter 创建 `Stock Entry` 草稿。
3. 成功后写回 `succeeded / external_ref / processed_at`。
4. 失败后写回 `failed / retry_count / error_message`，超过上限进入 `dead`。
5. 暴露 internal run-once 接口，受 `warehouse:worker` 权限和内部主体门禁保护。
6. 保持 `Stock Entry submit`、`Stock Reconciliation`、`GL Entry`、`Payment Entry`、`Purchase Invoice` 全部冻结。

## 3. 允许范围

后端允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/warehouse.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/warehouse.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_warehouse_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_050d_*.py`

测试允许新增或修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_stock_entry_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_worker_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`

日志允许追加：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止修改前端 `06_前端/**`；当前 `06_前端/lingyi-pc/src/router/index.ts` 如仍有继承 diff，B 只允许报告其为前序脏基线，不得在本任务继续修改。继承基线 SHA-256：`0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`。
2. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
3. 禁止创建或提交 ERPNext `Stock Entry`；本任务只允许创建 ERPNext `Stock Entry` 草稿。
4. 禁止调用或实现 `Stock Reconciliation`。
5. 禁止写 `Stock Ledger Entry`。
6. 禁止创建 `GL Entry`、`Payment Entry`、`Purchase Invoice`。
7. 禁止自动重试后台常驻 worker；本任务仅允许 internal `run-once`。
8. 禁止 push / PR / tag / 生产发布。

## 5. 必须实现

### 5.1 Adapter 草稿创建

在 `erpnext_warehouse_adapter.py` 中新增受控写方法：

- `create_stock_entry_draft(payload: dict) -> str`

要求：

1. 只允许 `POST /api/resource/Stock Entry` 创建草稿。
2. 请求体必须明确 `docstatus=0` 或等价草稿语义。
3. 禁止调用 `/submit`、`run_method=submit`、`Stock Entry.submit()`。
4. ERPNext 返回 malformed / timeout / unavailable 必须 fail-closed。
5. 不得在日志、异常、测试输出中泄露 token / cookie / authorization。

### 5.2 Worker 状态机

在 `warehouse_service.py` 中新增 worker 方法，建议命名：

- `run_stock_entry_outbox_once(batch_size: int = 10, dry_run: bool = False) -> WarehouseStockEntryWorkerRunOnceData`

状态规则：

1. `in_pending -> processing -> succeeded`
2. `in_pending -> processing -> failed`
3. `failed` 在 `retry_count < 3` 时可再次处理。
4. `retry_count >= 3` 后进入 `dead`。
5. `cancelled` 事件不得处理。
6. 对应草稿单状态为 `cancelled` 时不得处理，事件应进入 `cancelled` 或保持不可处理状态并返回跳过计数。
7. `dry_run=true` 不得调用 ERPNext，不得改变 outbox 状态。

### 5.3 Internal run-once 路由

在 `routers/warehouse.py` 中新增：

- `POST /api/warehouse/internal/stock-entry-sync/run-once`

要求：

1. 必须同时满足内部主体门禁与 `warehouse:worker` 权限。
2. 普通用户即使有 `warehouse:stock_entry_draft` 或 `warehouse:read` 也不得调用。
3. 支持 `batch_size`，默认 10，上限 50。
4. 支持 `dry_run=true`。
5. 返回 processed / succeeded / failed / dead / skipped / dry_run 等统计字段。

### 5.4 权限注册与 main.py 动作映射

1. 在 `app/core/permissions.py` 注册 `warehouse:worker`。
2. 在 `app/main.py` 内部动作映射中登记 `/api/warehouse/internal/stock-entry-sync/run-once`。
3. `tests/test_permissions_registry.py` 必须覆盖 `warehouse:worker`。

## 6. 验收标准

1. Outbox worker 可消费 `in_pending` 事件并创建 ERPNext Stock Entry 草稿。
2. 成功事件写回 `succeeded / external_ref / processed_at`。
3. 失败事件写回 `failed / retry_count / error_message`，超过重试上限进入 `dead`。
4. `dry_run=true` 不改变数据库、不调用 ERPNext。
5. 取消草稿或取消 outbox 不被 worker 处理。
6. internal run-once 权限必须 fail-closed。
7. 只允许 ERPNext 草稿创建，不允许 submit / Stock Reconciliation / 财务写入。
8. 测试全部通过。

## 7. 必须测试

新增或补充测试覆盖：

1. 成功消费 outbox，Adapter 返回 ERPNext 草稿名，事件进入 `succeeded`。
2. Adapter 抛 fail-closed 异常，事件进入 `failed` 并递增 retry_count。
3. retry_count 达上限后进入 `dead`。
4. `dry_run=true` 不改变状态且不调用 Adapter。
5. `cancelled` 事件或已取消 draft 不被处理。
6. 无 `warehouse:worker` 返回 403。
7. 非内部主体返回 403。
8. 仅有 `warehouse:read` / `warehouse:stock_entry_draft` 不得调用 worker。
9. 权限注册表包含 `warehouse:worker`。

## 8. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py tests/test_permissions_registry.py -v --tb=short
rg -n "submit\(|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry|GL Entry|Payment Entry|Purchase Invoice" app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py app/models/warehouse.py
rg -n "requests\.|httpx\." app/routers/warehouse.py app/services/warehouse_service.py app/services/erpnext_warehouse_adapter.py
git diff --name-only -- .github 02_源码 04_生产
shasum -a 256 '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts'
```

允许说明：`erpnext_warehouse_adapter.py` 中如出现 `POST /api/resource/Stock Entry`，仅在创建草稿且测试证明未 submit 的前提下合规；其余写调用一律视为越界。

## 9. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050D
ROLE: B Engineer

CHANGED_FILES:
- ...

EVIDENCE:
- Worker run-once 路由：路径 + 行号
- Adapter 草稿创建方法：路径 + 行号
- Outbox 成功/失败/dead 状态机：路径 + 行号
- warehouse:worker 权限注册：路径 + 行号
- main.py internal 动作映射：路径 + 行号

VERIFICATION:
- pytest ...：结果
- submit / Stock Reconciliation / 财务写入负向扫描：结果
- ERPNext 写调用边界扫描：结果
- 禁改目录 `.github / 02_源码 / 04_生产` diff：结果
- `06_前端/lingyi-pc/src/router/index.ts` 继承脏基线 SHA-256：结果；必须等于 `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`，不得作为 TASK-050D 新增改动

BLOCKERS:
- 无 / 如有写明

NEXT_ROLE:
- C Auditor
```
