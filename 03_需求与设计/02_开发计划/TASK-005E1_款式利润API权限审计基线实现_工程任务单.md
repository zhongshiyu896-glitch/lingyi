# TASK-005E1 款式利润 API 权限审计基线实现工程任务单（预派发版）

## 任务编号

TASK-005E1

## 任务名称

款式利润 API 权限审计基线实现

## 执行状态

预派发，待执行。

只有在 `TASK-005E_款式利润API权限与审计基线_工程任务单.md` 经审计官审查通过后，工程师才允许执行本任务。若审计官要求修改 TASK-005E 任务单，则先按审计意见修正任务单，不得直接执行本任务。

## 任务目标

在不修改利润计算公式、不修改前端、不进入 TASK-006 的前提下，实现款式利润报表后端 API 基线，覆盖：登录鉴权、动作权限、`company + item_code` 资源权限、安全审计、操作审计、统一错误信封、服务端来源采集、幂等快照创建入口和 PostgreSQL 安全门禁测试。

## 前置依赖

- `TASK-005D6` 已通过。
- `TASK-005E` 任务单已通过审计官审查。
- 本任务不得替代 TASK-005E 任务单审计。

## 严格边界

允许做：

1. 新增款式利润 API router。
2. 在 `app/main.py` 注册 router。
3. 增加 `style_profit:*` 权限动作。
4. 增加 `style_profit` 模块动作过滤和按钮权限。
5. 增加款式利润 API DTO。
6. 增加服务端来源采集器。
7. 增加 API 错误码。
8. 增加权限、审计、错误信封、幂等和 PostgreSQL 测试。

禁止做：

1. 禁止修改利润计算公式。
2. 禁止修改 `StyleProfitService` 已通过审计的计算口径。
3. 禁止新增或修改 migrations。
4. 禁止修改前端。
5. 禁止修改 `.github`。
6. 禁止修改 `02_源码`。
7. 禁止进入 `TASK-006`。
8. 禁止实现前端页面。
9. 禁止实现导出、打印、加工厂对账。
10. 禁止信任客户端提交的财务来源明细。

## 涉及文件

### 新增

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_api_source_collector.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_errors.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_postgresql.py`

### 修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/pytest.ini`，仅允许补 `postgresql` marker，已存在则不得改动。

### 禁止修改

- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006*`

## API 实现要求

### Router

新增 router：

```python
router = APIRouter(prefix="/api/reports/style-profit", tags=["style-profit"])
```

在 `app/main.py` 注册：

```python
from app.routers.style_profit import get_db_session as style_profit_router_session_dep
from app.routers.style_profit import router as style_profit_router

app.dependency_overrides[style_profit_router_session_dep] = get_db_session
app.include_router(style_profit_router)
```

### 接口 1：查询利润快照列表

```text
GET /api/reports/style-profit/snapshots
```

权限：`style_profit:read`

入参：

| 字段 | 必填 | 规则 |
| --- | --- | --- |
| company | 是 | 非空，资源权限校验 |
| item_code | 是 | 非空，资源权限校验 |
| sales_order | 否 | 精确过滤 |
| from_date | 否 | 快照期间起始过滤 |
| to_date | 否 | 快照期间结束过滤 |
| snapshot_status | 否 | 状态过滤 |
| page | 否 | 默认 1，最小 1 |
| page_size | 否 | 默认 20，最大 100 |

规则：

1. 必须先登录。
2. 必须校验 `style_profit:read`。
3. 必须校验 `company + item_code` 资源权限。
4. V1 不允许缺 company 或缺 item_code 的全局利润浏览。
5. 返回分页 `{items,total,page,page_size}`。

### 接口 2：查询利润快照详情

```text
GET /api/reports/style-profit/snapshots/{snapshot_id}
```

权限：`style_profit:read`

规则：

1. 必须先登录。
2. 必须先查 snapshot 是否存在。
3. snapshot 不存在返回 `STYLE_PROFIT_NOT_FOUND`。
4. 必须按 `snapshot.company + snapshot.item_code` 做资源权限。
5. 权限通过后才允许读取 detail/source_map。
6. 读取成功必须写操作审计。
7. 操作审计失败不得返回详情，返回 `AUDIT_WRITE_FAILED`。
8. 返回内容必须包含 snapshot、details、source_maps。

### 接口 3：创建利润快照

```text
POST /api/reports/style-profit/snapshots
```

权限：`style_profit:snapshot_create`

客户端只允许提交 selector：

```json
{
  "company": "LY公司",
  "item_code": "STYLE-001",
  "sales_order": "SO-0001",
  "from_date": "2026-04-01",
  "to_date": "2026-04-30",
  "revenue_mode": "actual_first",
  "include_provisional_subcontract": false,
  "formula_version": "STYLE_PROFIT_V1",
  "idempotency_key": "client-generated-key",
  "work_order": "WO-0001"
}
```

禁止客户端提交以下字段：

- `sales_invoice_rows`
- `sales_order_rows`
- `bom_material_rows`
- `bom_operation_rows`
- `stock_ledger_rows`
- `purchase_receipt_rows`
- `workshop_ticket_rows`
- `subcontract_rows`
- `allowed_material_item_codes`

如果请求体包含上述字段，返回：

```json
{
  "code": "STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN",
  "message": "客户端不得提交利润来源明细",
  "data": {}
}
```

创建流程：

1. 登录鉴权。
2. 校验 `style_profit:snapshot_create`。
3. 校验 `company + item_code` 资源权限。
4. 校验 selector 基础字段。
5. 调用 `StyleProfitApiSourceCollector` 从服务端采集来源事实。
6. 组装 `StyleProfitSnapshotCreateRequest`。
7. 调用 `StyleProfitService.create_snapshot()`。
8. 写操作审计。
9. commit。
10. 返回创建结果。

事务要求：

1. `StyleProfitService` 不得 commit。
2. Router 统一 commit / rollback。
3. 创建快照和必需操作审计必须同事务提交。
4. commit 失败返回 `DATABASE_WRITE_FAILED`。
5. rollback 失败只写脱敏日志。

## 权限实现要求

### permissions.py

新增：

```python
STYLE_PROFIT_READ = "style_profit:read"
STYLE_PROFIT_SNAPSHOT_CREATE = "style_profit:snapshot_create"
ALL_STYLE_PROFIT_ACTIONS = {
    STYLE_PROFIT_READ,
    STYLE_PROFIT_SNAPSHOT_CREATE,
}
```

静态角色临时映射：

| 角色 | 动作 |
| --- | --- |
| System Manager | read + snapshot_create |
| Finance Manager | read + snapshot_create |
| Production Manager | read |
| Sales Manager | read |

### permission_service.py

要求：

1. `ERP_ROLE_ACTIONS` 补 `style_profit:*`。
2. `_filter_actions_by_module()` 支持 `module == "style_profit"`。
3. `_button_permissions()` 支持 `read`、`snapshot_create`。
4. 新增或复用资源权限校验，确保 ERPNext 模式下 `company + item_code` 同时校验。
5. 权限源不可用必须返回 `PERMISSION_SOURCE_UNAVAILABLE`。
6. User Permission 查询失败不得 fail open。

## 服务端来源采集器

新增：

```text
app/services/style_profit_api_source_collector.py
```

职责：

1. 输入 selector。
2. 读取服务端可信来源。
3. 输出 `StyleProfitSnapshotCreateRequest` 所需来源 rows。
4. 不计算利润。
5. 不改变 D 系列利润口径。
6. 采集失败 fail closed。

V1 最低要求：

1. 不允许从客户端读取来源 rows。
2. 支持测试注入 collector，便于 API 测试构造来源事实。
3. 真实 collector 若 ERPNext 来源不可用，返回 `STYLE_PROFIT_SOURCE_UNAVAILABLE`。
4. 本地 FastAPI 来源读取失败，返回 `DATABASE_READ_FAILED`。
5. 采集器输出字段必须保留 source 追溯字段。

## 审计实现要求

### 安全审计

必须覆盖：

1. 401 未登录。
2. 403 缺动作权限。
3. 403 缺 company 资源权限。
4. 403 缺 item_code 资源权限。
5. 503 权限源不可用。

### 操作审计

必须覆盖：

1. 创建快照成功。
2. 创建快照失败。
3. 详情读取成功。
4. 详情读取失败。

要求：

1. module=`style_profit`。
2. action=`style_profit:read` 或 `style_profit:snapshot_create`。
3. operator=current_user.username。
4. operator_roles=current_user.roles。
5. resource_type=`STYLE_PROFIT_SNAPSHOT`。
6. resource_id=snapshot_id。
7. resource_no=snapshot_no。
8. 审计失败时按必需审计处理，返回 `AUDIT_WRITE_FAILED`。

## 错误码

必须覆盖：

| code | HTTP | 场景 |
| --- | --- | --- |
| AUTH_UNAUTHORIZED | 401 | 未登录 |
| AUTH_FORBIDDEN | 403 | 权限不足 |
| PERMISSION_SOURCE_UNAVAILABLE | 503 | 权限源不可用 |
| STYLE_PROFIT_NOT_FOUND | 404 | 快照不存在 |
| STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN | 400 | 客户端提交来源明细 |
| STYLE_PROFIT_INVALID_PERIOD | 400 | 日期非法 |
| STYLE_PROFIT_INVALID_REVENUE_MODE | 400 | revenue_mode 非法 |
| STYLE_PROFIT_INVALID_FORMULA_VERSION | 400 | formula_version 非法 |
| STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY | 400 | idempotency_key 非法 |
| STYLE_PROFIT_SALES_ORDER_REQUIRED | 400 | sales_order 为空 |
| STYLE_PROFIT_IDEMPOTENCY_CONFLICT | 409 | 幂等冲突 |
| STYLE_PROFIT_SOURCE_UNAVAILABLE | 503 | 服务端来源不可用 |
| DATABASE_READ_FAILED | 500 | 本地读取失败 |
| DATABASE_WRITE_FAILED | 500 | 本地写入失败 |
| AUDIT_WRITE_FAILED | 500 | 必需审计写入失败 |
| STYLE_PROFIT_INTERNAL_ERROR | 500 | 未知错误 |

## 响应格式

成功：

```json
{"code":"0","message":"success","data":{}}
```

失败：

```json
{"code":"ERROR_CODE","message":"错误说明","data":{}}
```

禁止：

1. 顶层 `detail`。
2. `detail=str(exc)`。
3. 响应或普通日志泄露 SQL、堆栈、Authorization、Cookie、Token、Secret、Password。

## PostgreSQL 集成测试

新增：

```text
tests/test_style_profit_api_postgresql.py
```

安全门禁：

1. 必须设置 `POSTGRES_TEST_DSN`。
2. 必须设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
3. 数据库名必须以 `_test` 结尾，或以 `lingyi_test_` 开头。
4. 不满足条件时必须明确 skip，不得执行 destructive 操作。

至少覆盖：

1. 同一 `company + idempotency_key + 相同请求` 并发创建，只形成一条 snapshot，另一个请求 replay。
2. 同一 `company + idempotency_key + 不同请求` 返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
3. commit 失败返回 `DATABASE_WRITE_FAILED`，不得留下半快照。
4. 资源权限失败返回 403，并写安全审计。

本项目不等待 GitHub Hosted Runner。本地无 PostgreSQL DSN 时，普通回归允许安全 skip，但必须写明原因。

## 测试命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q \
  tests/test_style_profit_api.py \
  tests/test_style_profit_api_permissions.py \
  tests/test_style_profit_api_audit.py \
  tests/test_style_profit_api_errors.py \
  tests/test_style_profit_api_postgresql.py

.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

禁改扫描：

```bash
cd /Users/hh/Desktop/领意服装管理系统

git diff --name-only -- 06_前端 .github 02_源码
git diff --name-only -- 07_后端/lingyi_service/migrations
git diff --name-only -- '03_需求与设计/02_开发计划' | grep 'TASK-006' || true
```

## 验收标准

- [ ] TASK-005E 任务单已先通过审计。
- [ ] 已新增 style_profit router。
- [ ] 已注册 `/api/reports/style-profit`。
- [ ] 列表接口可用。
- [ ] 详情接口可用。
- [ ] 创建接口可用。
- [ ] `/api/auth/actions?module=style_profit` 可返回动作权限。
- [ ] 所有接口接入登录鉴权。
- [ ] 所有接口校验动作权限。
- [ ] 所有接口校验 `company + item_code` 资源权限。
- [ ] 权限源不可用 fail closed。
- [ ] 列表接口强制 `company + item_code`。
- [ ] 创建接口拒绝客户端来源明细。
- [ ] 创建接口幂等 replay 稳定。
- [ ] 幂等冲突返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
- [ ] 401/403/503 写安全审计。
- [ ] 创建成功/失败写操作审计。
- [ ] 详情成功/失败写操作审计。
- [ ] 必需审计失败返回 `AUDIT_WRITE_FAILED`。
- [ ] 错误响应统一 `{code,message,data}`。
- [ ] 无顶层 `detail`。
- [ ] 无 `detail=str(exc)`。
- [ ] 日志脱敏。
- [ ] PostgreSQL 测试具备安全门禁。
- [ ] 定向 pytest 通过。
- [ ] 全量 pytest 通过。
- [ ] unittest discover 通过。
- [ ] py_compile 通过。
- [ ] 未修改前端。
- [ ] 未修改 `.github`。
- [ ] 未修改 `02_源码`。
- [ ] 未修改 migrations。
- [ ] 未进入 TASK-006。

## 交付回报格式

```text
TASK-005E1 已完成。

前置确认：
- TASK-005E 任务单审计：[通过/不通过]

实现内容：
- 新增接口：[列表]
- 新增权限动作：[列表]
- 新增测试：[列表]

验证结果：
- 定向 pytest：[结果]
- 全量 pytest：[结果]
- unittest discover：[结果]
- py_compile：[结果]
- PostgreSQL 测试：[非 skip 结果或 skip 原因]
- 禁改扫描：[通过/不通过]

审计说明：
- 401/403/503 安全审计：[已覆盖/未覆盖]
- 创建操作审计：[已覆盖/未覆盖]
- 详情操作审计：[已覆盖/未覆盖]
- 统一错误信封：[已覆盖/未覆盖]

确认：
- 未修改前端
- 未修改 .github
- 未修改 02_源码
- 未修改 migrations
- 未进入 TASK-006
```
