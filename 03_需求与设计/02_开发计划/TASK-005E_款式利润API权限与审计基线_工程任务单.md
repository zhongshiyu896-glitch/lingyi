# TASK-005E 款式利润 API 权限与审计基线工程任务单（待审计版）

## 任务编号

TASK-005E

## 任务名称

款式利润 API 权限与审计基线

## 执行状态

待审计。

本任务单必须先交审计官审查。审计官确认任务单通过前，工程师不得进入 API 实现。

## 任务目标

在 `TASK-005D~D6` 已形成利润快照服务稳定基线的前提下，设计并实现款式利润报表的 FastAPI API 层基线，覆盖鉴权、资源权限、安全审计、操作审计、统一错误信封、幂等创建入口和 PostgreSQL 验证门禁。

## 前置条件

- `TASK-005D3` 已通过：利润快照计算服务阻断问题已关闭。
- `TASK-005D4` 已通过/有条件通过：利润服务本地基线 commit 已形成。
- `TASK-005D5` 已通过：D4 证据提交后 HEAD 已回填。
- `TASK-005D6` 已通过：D5/D6 文档基线已入库。
- 本任务单经过审计官审查通过后，才允许工程实现。

## 严格边界

本任务只允许做款式利润 API 权限与审计基线。

允许做：

1. 新增款式利润 API router。
2. 在 `app/main.py` 注册款式利润 router。
3. 增加款式利润权限动作常量和模块过滤。
4. 增加款式利润资源权限校验。
5. 增加款式利润 API DTO。
6. 增加 API 错误码映射。
7. 增加 API 安全审计和操作审计。
8. 增加 API 单元测试、权限测试、审计测试、错误信封测试。
9. 增加 PostgreSQL 集成测试门禁。

禁止做：

1. 禁止修改利润计算公式。
2. 禁止修改 `StyleProfitService` 已通过审计的计算口径，除非仅为 API 适配且不改变业务结果。
3. 禁止新增或修改利润表迁移。
4. 禁止修改前端。
5. 禁止进入 `TASK-006`。
6. 禁止实现利润导出。
7. 禁止实现加工厂对账。
8. 禁止把客户端提交的 revenue/cost 明细当作可信财务事实。
9. 禁止让 API 直接接受并入账客户端传入的 `sales_invoice_rows / stock_ledger_rows / workshop_ticket_rows / subcontract_rows`。
10. 禁止绕过 ERPNext / FastAPI 服务端事实源。
11. 禁止返回 `detail=str(exc)` 或日志中输出敏感异常明文。

## 涉及文件

### 允许新增

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/style_profit_api_source_collector.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_audit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_errors.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_api_postgresql.py`

### 允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/style_profit.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/pytest.ini`，仅允许注册 `postgresql` marker，如已存在则不得重复改动。

### 禁止修改

- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006*`

## API 设计

### 统一前缀

`/api/reports/style-profit`

### 接口清单

| 接口名称 | HTTP 方法 | 路径 | 权限动作 | 说明 |
| --- | --- | --- | --- | --- |
| 查询当前用户款式利润动作 | GET | `/api/auth/actions?module=style_profit&resource_type=style_profit&resource_item_code={item_code}` | 登录用户 | 复用 auth actions 聚合，返回 `style_profit` 模块动作和按钮权限 |
| 查询利润快照列表 | GET | `/api/reports/style-profit/snapshots` | `style_profit:read` | 分页查询已生成利润快照，V1 必须传 `company + item_code` |
| 查询利润快照详情 | GET | `/api/reports/style-profit/snapshots/{snapshot_id}` | `style_profit:read` | 返回 snapshot、detail、source_map，必须先做资源权限 |
| 创建利润快照 | POST | `/api/reports/style-profit/snapshots` | `style_profit:snapshot_create` | 根据 selector 创建快照，必须服务端采集来源事实，禁止信任客户端来源明细 |

### 列表接口入参

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| company | string | 是 | 用于 Company 资源权限校验 |
| item_code | string | 是 | 用于 Item 资源权限校验 |
| sales_order | string | 否 | 过滤销售订单 |
| from_date | date | 否 | 过滤快照期间起始 |
| to_date | date | 否 | 过滤快照期间结束 |
| snapshot_status | string | 否 | `complete/incomplete/failed` 等现有状态 |
| page | int | 否 | 默认 1，最小 1 |
| page_size | int | 否 | 默认 20，最大 100 |

### 创建接口入参

客户端只允许提交 selector，不允许提交财务来源明细。

| 字段 | 类型 | 必填 | 规则 |
| --- | --- | --- | --- |
| company | string | 是 | 必须通过 Company 资源权限 |
| item_code | string | 是 | 必须通过 Item 资源权限 |
| sales_order | string | 是 | V1 强制非空 |
| from_date | date | 是 | 不得晚于 `to_date` |
| to_date | date | 是 | 不得早于 `from_date` |
| revenue_mode | string | 否 | `actual_first / actual_only / estimated_only` |
| include_provisional_subcontract | bool | 否 | 默认 false |
| formula_version | string | 否 | 默认 `STYLE_PROFIT_V1` |
| idempotency_key | string | 是 | 非空，长度 <= 128 |
| work_order | string | 否 | 仅作为服务端来源采集辅助过滤 |

禁止出现在 API 入参中的字段：

- `sales_invoice_rows`
- `sales_order_rows`
- `bom_material_rows`
- `bom_operation_rows`
- `stock_ledger_rows`
- `purchase_receipt_rows`
- `workshop_ticket_rows`
- `subcontract_rows`
- `allowed_material_item_codes`

如客户端提交上述字段，必须返回：

- HTTP 400
- `code=STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN`

## 权限动作设计

在 `app/core/permissions.py` 增加：

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
| System Manager | `style_profit:read`, `style_profit:snapshot_create` |
| Finance Manager | `style_profit:read`, `style_profit:snapshot_create` |
| Production Manager | `style_profit:read` |
| Sales Manager | `style_profit:read` |
| Viewer | 不默认授予款式利润权限 |

要求：

1. `PermissionService._filter_actions_by_module()` 必须支持 `module == "style_profit"`。
2. `PermissionService._button_permissions()` 必须返回 `read`、`snapshot_create`。
3. `/api/auth/actions?module=style_profit` 必须只返回 `style_profit:*` 动作。
4. 生产环境仍必须使用 ERPNext 权限来源，static 仅为 Sprint 本地临时方案。

## 资源权限设计

款式利润属于敏感经营数据。所有 API 必须同时满足动作权限和资源权限。

### 资源维度

| 资源 | 来源 | 规则 |
| --- | --- | --- |
| company | API 入参或 snapshot.company | 必须通过 ERPNext User Permission Company 校验 |
| item_code | API 入参或 snapshot.item_code | 必须通过 ERPNext User Permission Item 校验 |
| sales_order | API 入参或 snapshot.sales_order | V1 暂不接 ERPNext User Permission；必须与 snapshot/request 完整一致，不得跨订单读取 |

### fail closed 规则

1. 权限源不可用时返回 `503 + PERMISSION_SOURCE_UNAVAILABLE`。
2. ERPNext User Permission 查询失败不得当作“无限制”。
3. ERPNext 模式下缺 `company` 或缺 `item_code` 的请求必须拒绝。
4. 列表 V1 强制要求 `company + item_code`，避免无边界浏览利润数据。
5. 详情必须读取 snapshot 后按 `snapshot.company + snapshot.item_code` 做资源权限。
6. 创建必须先做动作权限和资源权限，再采集来源事实。
7. 未授权访问必须写安全审计。

## 来源采集设计

新增 `StyleProfitApiSourceCollector`，用于把 API selector 转成 `StyleProfitSnapshotCreateRequest` 所需的服务端来源行。

要求：

1. 来源事实必须从服务端采集。
2. 禁止信任客户端提交的收入、材料、工票、外发明细。
3. 来源采集失败必须 fail closed。
4. ERPNext 来源不可用返回 `STYLE_PROFIT_SOURCE_UNAVAILABLE` 或等价 503 错误码。
5. FastAPI 自建来源读取失败返回 `DATABASE_READ_FAILED`。
6. 来源采集结果必须保留 `source_system/source_doctype/source_name/source_line_no/source_status/qty/amount` 等 D 系列已冻结追溯字段。
7. 采集器不得改变 D 系列利润公式和映射口径。

## 统一响应格式

成功响应：

```json
{
  "code": "0",
  "message": "success",
  "data": {}
}
```

分页响应：

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "items": [],
    "total": 0,
    "page": 1,
    "page_size": 20
  }
}
```

错误响应：

```json
{
  "code": "ERROR_CODE",
  "message": "错误说明",
  "data": {}
}
```

禁止：

1. 禁止返回 `detail` 顶层字段。
2. 禁止返回 `str(exc)`。
3. 禁止返回 SQL、堆栈、Cookie、Authorization、Token、Secret、Password。

## 错误码要求

| 错误码 | HTTP | 场景 |
| --- | --- | --- |
| AUTH_UNAUTHORIZED | 401 | 未登录 |
| AUTH_FORBIDDEN | 403 | 动作权限或资源权限不足 |
| PERMISSION_SOURCE_UNAVAILABLE | 503 | ERPNext 权限源不可用 |
| STYLE_PROFIT_NOT_FOUND | 404 | 快照不存在 |
| STYLE_PROFIT_CLIENT_SOURCE_FORBIDDEN | 400 | 客户端提交来源明细 |
| STYLE_PROFIT_INVALID_PERIOD | 400 | 日期区间非法 |
| STYLE_PROFIT_INVALID_REVENUE_MODE | 400 | revenue_mode 非法 |
| STYLE_PROFIT_INVALID_FORMULA_VERSION | 400 | formula_version 非法 |
| STYLE_PROFIT_INVALID_IDEMPOTENCY_KEY | 400 | idempotency_key 非法 |
| STYLE_PROFIT_SALES_ORDER_REQUIRED | 400 | sales_order 为空 |
| STYLE_PROFIT_IDEMPOTENCY_CONFLICT | 409 | 幂等键冲突 |
| STYLE_PROFIT_SOURCE_UNAVAILABLE | 503 | ERPNext 或服务端来源不可用 |
| DATABASE_READ_FAILED | 500 | 本地数据库读取失败 |
| DATABASE_WRITE_FAILED | 500 | 本地数据库写入失败 |
| AUDIT_WRITE_FAILED | 500 | 必需审计写入失败 |
| STYLE_PROFIT_INTERNAL_ERROR | 500 | 未知错误兜底 |

## 审计要求

### 安全审计

以下场景必须写安全审计：

1. 401 未登录。
2. 403 缺动作权限。
3. 403 缺公司资源权限。
4. 403 缺款式资源权限。
5. 503 权限源不可用。

安全审计不得记录 Authorization、Cookie、Token、Secret、Password 明文。

### 操作审计

以下场景必须写操作审计：

| 接口 | 成功审计 | 失败审计 | 审计要求 |
| --- | --- | --- | --- |
| POST 创建快照 | 必须 | 必须 | 审计失败则请求失败，返回 `AUDIT_WRITE_FAILED` |
| GET 快照详情 | 必须 | 必须 | 利润详情为敏感经营数据，审计失败不得返回详情 |
| GET 快照列表 | 可不写成功审计 | 必须写失败审计 | 列表成功不强制写，避免高频放大 |

操作审计字段必须包含：

- module=`style_profit`
- action=`style_profit:read` 或 `style_profit:snapshot_create`
- operator=current_user.username
- operator_roles=current_user.roles
- resource_type=`STYLE_PROFIT_SNAPSHOT`
- resource_id=snapshot_id，如创建前失败则为空
- resource_no=snapshot_no，如创建前失败则为空
- before_data / after_data 的安全摘要
- request_id

## 事务边界

1. `StyleProfitService.create_snapshot()` 不得在服务内提交事务。
2. Router 负责 commit / rollback。
3. 创建快照时，业务写入和必需操作审计必须在同一事务中成功后再 commit。
4. commit 失败必须 rollback，并返回 `DATABASE_WRITE_FAILED`。
5. rollback 失败只允许脱敏日志，不得泄露异常明文。
6. 读接口不得改变业务事实。
7. 详情读若操作审计失败，不得返回详情数据。

## PostgreSQL 验证门禁

必须新增 `tests/test_style_profit_api_postgresql.py`。

测试必须使用安全破坏性门禁：

- `POSTGRES_TEST_DSN` 必须存在。
- `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 必须存在。
- 数据库名必须匹配 `_test` 后缀或 `lingyi_test_` 前缀。
- 不满足条件时必须明确 skip，不得执行 destructive schema 操作。

PostgreSQL 测试至少覆盖：

1. 同一 `company + idempotency_key + 相同请求` 并发创建，只形成一条 snapshot，另一个请求稳定 replay。
2. 同一 `company + idempotency_key + 不同请求` 返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`，不得产生半快照。
3. 创建接口 commit 失败返回 `DATABASE_WRITE_FAILED`，不得调用成功审计。
4. 详情读取在资源权限失败时返回 403，并写安全审计。

验收口径：

- 本地无 PostgreSQL DSN 时，普通回归允许安全 skip，但必须保留明确 skip 原因。
- 进入前端联调或发布前，必须补一次真实 PostgreSQL 非 skip 证据。
- 本项目是本地项目，不要求 GitHub Hosted Runner，不等待 GitHub。

## 测试要求

后端目录：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
```

定向测试：

```bash
.venv/bin/python -m pytest -q \
  tests/test_style_profit_api.py \
  tests/test_style_profit_api_permissions.py \
  tests/test_style_profit_api_audit.py \
  tests/test_style_profit_api_errors.py \
  tests/test_style_profit_api_postgresql.py
```

全量测试：

```bash
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

要求：

1. 不得出现前端、`.github`、`02_源码` 改动。
2. 不得出现 migration 改动。
3. 不得出现 TASK-006 文件。

## 验收标准

- [ ] 本任务单已先通过审计官审查。
- [ ] 新增 `/api/reports/style-profit/snapshots` 列表接口。
- [ ] 新增 `/api/reports/style-profit/snapshots/{snapshot_id}` 详情接口。
- [ ] 新增 `/api/reports/style-profit/snapshots` 创建接口。
- [ ] `/api/auth/actions?module=style_profit` 返回 style_profit 权限动作。
- [ ] 所有 API 均接入 `get_current_user`。
- [ ] 所有 API 均校验动作权限。
- [ ] 所有 API 均校验 `company + item_code` 资源权限。
- [ ] ERPNext 权限源不可用时 fail closed。
- [ ] 列表接口 V1 强制 `company + item_code`。
- [ ] 创建接口拒绝客户端来源明细。
- [ ] 创建接口幂等 replay 稳定。
- [ ] 幂等冲突返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
- [ ] 401/403/503 写安全审计。
- [ ] 创建成功/失败写操作审计。
- [ ] 详情成功/失败写操作审计。
- [ ] 必需操作审计失败返回 `AUDIT_WRITE_FAILED`。
- [ ] 所有错误响应统一 `{code,message,data}`。
- [ ] 无 `detail=str(exc)`。
- [ ] 日志脱敏。
- [ ] PostgreSQL 集成测试文件存在并具备安全破坏性门禁。
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
TASK-005E 已完成。

实现内容：
- 新增接口：[列出]
- 新增权限动作：[列出]
- 新增测试：[列出]

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
- 详情读取操作审计：[已覆盖/未覆盖]
- 统一错误信封：[已覆盖/未覆盖]

确认：
- 未修改前端
- 未修改 .github
- 未修改 02_源码
- 未修改 migrations
- 未进入 TASK-006
```
