# TASK-050D_FIX1 run-once 契约收紧 工程任务单

## 1. 基本信息

- 任务编号：TASK-050D_FIX1
- 任务名称：run-once 契约收紧
- 模块：仓库管理增强 / Stock Entry Outbox Worker
- 角色：B Engineer
- 优先级：P0
- 前置：TASK-050D 审计意见书第387份 `NEEDS_FIX / 高危1`
- 任务性质：fix pass 1，只修复 C 指出的 run-once API 契约偏差，不扩大功能范围。

## 2. 修复目标

修复第387份审计指出的两个问题：

1. `WarehouseStockEntryWorkerRunOnceRequest.batch_size` 必须从当前 `default=20, le=200` 收紧为：
   - `Field(default=10, ge=1, le=50)`
2. `WarehouseStockEntryWorkerRunOnceData` 必须新增：
   - `skipped_count: int`
3. worker 实现必须对跳过场景显式计数并返回 `skipped_count`。
4. 测试必须覆盖：
   - 未传 `batch_size` 时默认值为 10。
   - `batch_size=51` 被请求校验拒绝。
   - 响应体包含 `skipped_count`。
   - cancelled outbox 或 draft cancelled/missing 场景会体现在 `skipped_count`。

## 3. 允许范围

仅允许修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/warehouse.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/warehouse_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_stock_entry_worker.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_warehouse_worker_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/工程师会话日志.md`

## 4. 禁止范围

1. 禁止修改前端 `06_前端/**`。
2. 禁止修改 `.github/**`、`02_源码/**`、`04_生产/**`。
3. 禁止修改 `app/main.py`、`app/core/permissions.py`、migration、模型、Adapter、router，除非发现不改无法修复本任务；如必须扩范围，立即 `BLOCKED`。
4. 禁止新增 ERPNext 写能力。
5. 禁止 `Stock Entry submit`、`Stock Reconciliation`、`Stock Ledger Entry` 直接写入。
6. 禁止 `GL Entry`、`Payment Entry`、`Purchase Invoice`。
7. 禁止 push / PR / tag / 生产发布。

继承脏基线：

- `06_前端/lingyi-pc/src/router/index.ts` 当前 SHA-256 必须保持：`0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`
- 本任务不得修改该文件。

## 5. 必须实现

### 5.1 schema 契约

在 `app/schemas/warehouse.py`：

```python
batch_size: int = Field(default=10, ge=1, le=50)
```

并在 `WarehouseStockEntryWorkerRunOnceData` 新增：

```python
skipped_count: int
```

### 5.2 service 返回统计

在 `WarehouseService.run_stock_entry_outbox_once(...)`：

1. 所有返回 `WarehouseStockEntryWorkerRunOnceData(...)` 的分支都必须传 `skipped_count`。
2. `dry_run=true` 时 `skipped_count` 可以为 0，但响应字段必须存在。
3. cancelled outbox、draft cancelled、draft missing 等未真正处理的事件必须计入 `skipped_count`。
4. `processed_count` 的语义保持为本轮领取/扫描到的事件数量，不得用 skipped 替代 succeeded/failed/dead。

## 6. 必须测试

在允许测试文件中补充：

1. `POST /api/warehouse/internal/stock-entry-sync/run-once` 空 JSON 或不传 `batch_size`，证明默认值为 10。
2. `batch_size=51` 返回 422 或项目统一参数错误响应，不能进入 worker。
3. 成功响应 `data` 包含 `skipped_count`。
4. cancelled outbox 或 draft cancelled/missing 时 `skipped_count >= 1`。
5. 原有 worker 权限测试继续通过。

## 7. 验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py -v --tb=short
rg -n "batch_size: int = Field\(default=10, ge=1, le=50\)|skipped_count" app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
rg -n "submit\(|run_method.*submit|/submit|Stock Reconciliation|Stock Ledger Entry|GL Entry|Payment Entry|Purchase Invoice" app/schemas/warehouse.py app/services/warehouse_service.py tests/test_warehouse_stock_entry_worker.py tests/test_warehouse_worker_permissions.py
git diff --name-only -- .github 02_源码 04_生产 06_前端
shasum -a 256 '/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts'
```

说明：`git diff --name-only -- 06_前端` 如仍命中 `router/index.ts`，必须报告为继承脏基线，且 SHA-256 必须等于 `0d88ccc9d2ee79283730cdebb3067c8073545daa2185162f7d49cbb3eb821d6a`。

## 8. 回交格式

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-050D_FIX1
ROLE: B Engineer

CHANGED_FILES:
- ...

EVIDENCE:
- batch_size 已收紧为 default=10/le=50：路径 + 行号
- skipped_count 已加入响应 schema：路径 + 行号
- worker 返回 skipped_count：路径 + 行号
- 默认值/51拒绝/skipped_count 测试：路径 + 行号

VERIFICATION:
- pytest ...：结果
- batch_size/skipped_count rg：结果
- 禁止写语义扫描：结果
- 禁改目录 diff：结果
- router 继承基线 SHA-256：结果

BLOCKERS:
- 无 / 如有写明

NEXT_ROLE:
- C Auditor
```
