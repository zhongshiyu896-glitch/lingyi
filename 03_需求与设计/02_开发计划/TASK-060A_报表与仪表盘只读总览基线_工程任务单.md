# TASK-060A 报表与仪表盘只读总览基线 工程任务单

- 任务编号：TASK-060A
- 任务名称：报表与仪表盘只读总览基线
- 角色：B Engineer
- 派发时间：2026-04-20 22:28 CST+8
- 派发人：A Technical Architect
- 模块：报表与仪表盘 / dashboard
- 前置依据：`TASK-019A_报表与仪表盘总体设计.md`、`TASK-050I` 审计意见书第404份通过
- 当前定位：仓库管理增强本地封版后，按规划表进入报表与仪表盘方向的第一张实现任务

## 0. 强制说明

本任务单是 A -> B 执行指令，不是 B -> C 审计输入。

未形成真实代码改动、测试结果、验证命令输出和证据路径前，禁止回交 C。

本任务不允许 push、PR、tag、生产发布。

## 1. 目标

实现一个后端为主、前端最小接入的只读 Dashboard Overview 基线：

1. 新增 `GET /api/dashboard/overview`。
2. 校验 `dashboard:read`。
3. 必须要求 `company` 查询参数。
4. 聚合现有质量、销售库存、仓库三个已审计模块的只读摘要。
5. 只读，不新增数据库表，不新增 migration，不新增 outbox/worker。
6. 前端新增最小总览页入口，可展示接口返回的三个模块摘要。

## 2. 允许修改文件

### 2.1 后端允许新增

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/dashboard.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/dashboard_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/dashboard.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_dashboard_overview_readonly.py`

### 2.2 后端允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_permissions_registry.py`（仅允许补充 `dashboard:read` 注册保持测试，如现有测试已覆盖则不要改）

### 2.3 前端允许新增

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/dashboard.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/dashboard/DashboardOverview.vue`

### 2.4 前端允许修改

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`

注意：`router/index.ts` 当前存在继承脏基线。修改前先记录 SHA-256；修改后必须在回交中说明这是本任务必要新增 `/dashboard/overview` 路由，不得混入其他路由改动。

## 3. 禁止修改范围

1. 禁止修改 `.github/**`。
2. 禁止修改 `02_源码/**`。
3. 禁止修改 `04_生产/**`。
4. 禁止新增或修改 migration。
5. 禁止新增或修改 `app/models/**`。
6. 禁止修改质量、销售库存、仓库既有业务服务语义；只允许在 `dashboard_service.py` 中组合调用既有只读服务。
7. 禁止新增 `POST / PUT / PATCH / DELETE` 路由。
8. 禁止新增 ERPNext 写调用。
9. 禁止新增 `outbox`、`worker`、`run-once`、`internal` 接口。
10. 禁止引入缓存表、异步任务、后台任务。
11. 禁止提交、push、PR、tag、生产发布。

## 4. 后端接口契约

### 4.1 路由

```text
GET /api/dashboard/overview
```

### 4.2 权限

必须校验：

```text
dashboard:read
```

不得接受以下权限作为通过条件：

```text
quality:read
sales_inventory:read
warehouse:read
inventory:read
```

这些模块权限可以作为下游服务内部校验或资源过滤依据，但不能替代 `dashboard:read`。

### 4.3 查询参数

- `company`：必填，空字符串拒绝。
- `from_date`：可选，格式 `YYYY-MM-DD`。
- `to_date`：可选，格式 `YYYY-MM-DD`。
- `item_code`：可选。
- `warehouse`：可选。

日期规则：

1. 日期格式非法返回 `400 / INVALID_QUERY_PARAMETER`。
2. `from_date > to_date` 返回 `400 / INVALID_QUERY_PARAMETER`。
3. 不得静默忽略非法日期。

### 4.4 响应字段

成功响应统一使用既有信封：

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "company": "LY",
    "from_date": "2026-04-01",
    "to_date": "2026-04-20",
    "generated_at": "2026-04-20T22:28:00Z",
    "quality": {
      "inspection_count": 0,
      "accepted_qty": "0",
      "rejected_qty": "0",
      "defect_count": 0,
      "pass_rate": "0"
    },
    "sales_inventory": {
      "item_count": 0,
      "total_actual_qty": "0",
      "below_safety_count": 0,
      "below_reorder_count": 0
    },
    "warehouse": {
      "alert_count": 0,
      "critical_alert_count": 0,
      "warning_alert_count": 0
    },
    "source_status": [
      {"module": "quality", "status": "ok"},
      {"module": "sales_inventory", "status": "ok"},
      {"module": "warehouse", "status": "ok"}
    ]
  }
}
```

字段命名可以按 Pydantic 模型实现，但必须覆盖以上语义。

### 4.5 Fail-closed 规则

1. `dashboard:read` 权限拒绝时返回 403。
2. 任一必需来源不可用，不得返回 `200 + 空摘要`。
3. 来源不可用时返回 503 或既有标准错误信封，错误码建议：`DASHBOARD_SOURCE_UNAVAILABLE`。
4. 不得把异常详情、token、Authorization、Cookie、DSN、password、secret 回传给前端。

## 5. 后端实现要求

1. `app/schemas/dashboard.py` 定义请求/响应数据模型。
2. `app/services/dashboard_service.py` 只组合已存在只读服务或只读查询。
3. `app/routers/dashboard.py` 只暴露 `GET /api/dashboard/overview`。
4. `app/main.py` 注册 dashboard router，并在安全审计 fallback 中补充 `/api/dashboard` 的 `module=dashboard / action=dashboard:read` 映射。
5. 优先复用：
   - `QualityService.statistics(...)`
   - `SalesInventoryService.get_inventory_aggregation(...)`
   - `WarehouseService.get_alerts(...)`
6. 如果既有服务签名与任务单描述不一致，只能在 `dashboard_service.py` 中做适配，不得改动既有模块业务语义。
7. 不允许直接在 dashboard router/service 中写 `requests.post/put/patch/delete` 或裸写 ERPNext resource。

## 6. 前端实现要求

1. 新增 `src/api/dashboard.ts`，通过统一 `request` client 调用 `/api/dashboard/overview`。
2. 新增 `DashboardOverview.vue`，展示：质量、销售库存、仓库预警三个摘要区块。
3. 修改 `router/index.ts` 增加：

```text
path: /dashboard/overview
name: DashboardOverview
meta.module: dashboard
```

4. 前端不得直连 ERPNext。
5. 前端不得裸 `fetch` / `axios` 绕过统一 API client。
6. 前端不得新增写按钮或写动作。

## 7. 测试要求

新增或补充测试必须覆盖：

1. `dashboard:read` 可访问成功。
2. 仅持有 `quality:read`、`sales_inventory:read`、`warehouse:read`、`inventory:read` 但没有 `dashboard:read` 时访问返回 403。
3. `company` 缺失或空字符串返回 400。
4. 日期格式非法返回 400。
5. `from_date > to_date` 返回 400。
6. 来源服务异常时 fail-closed，不能返回 `200 + 空摘要`。
7. dashboard router 中不存在 `POST/PUT/PATCH/DELETE`。
8. dashboard 文件中不存在 ERPNext 写调用、outbox、worker、run-once、internal 接口。
9. 前端 typecheck 通过。

## 8. 必跑验证命令

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest tests/test_dashboard_overview_readonly.py tests/test_permissions_registry.py -v --tb=short
.venv/bin/python -m py_compile app/routers/dashboard.py app/services/dashboard_service.py app/schemas/dashboard.py
rg -n "@router\.(post|put|patch|delete)" app/routers/dashboard.py || true
rg -n "requests\.(post|put|patch|delete)|httpx\.(post|put|patch|delete)|/api/resource/.+/(submit|cancel)|Stock Reconciliation|GL Entry|Payment Entry|Purchase Invoice" app/routers/dashboard.py app/services/dashboard_service.py app/schemas/dashboard.py || true
rg -n "outbox|worker|run-once|internal" app/routers/dashboard.py app/services/dashboard_service.py app/schemas/dashboard.py || true
git diff --name-only -- .github 02_源码 04_生产
```

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run typecheck
rg -n "fetch\(|axios\.|/api/resource" src/api/dashboard.ts src/views/dashboard/DashboardOverview.vue || true
```

## 9. 回交格式

B 完成后回交给 C，必须包含：

```text
STATUS: READY_FOR_AUDIT
TASK_ID: TASK-060A
ROLE: B Engineer

CHANGED_FILES:
- 真实改动文件列表

EVIDENCE:
- dashboard overview 后端路由、schema、service 落点
- dashboard:read 权限校验证据
- 前端 API / 页面 / 路由落点
- fail-closed 证据
- 只读边界扫描结果
- 禁改目录 diff 结果

VERIFICATION:
- pytest 结果
- py_compile 结果
- npm run typecheck 结果
- 负向扫描结果

BLOCKERS:
- 无 / 具体阻塞

NEXT_ROLE:
- C Auditor
```

## 10. 完成定义

满足以下条件才算完成：

1. `/api/dashboard/overview` 可用。
2. `dashboard:read` 是唯一入口动作权限。
3. 返回质量、销售库存、仓库三个摘要。
4. 任一来源不可用时 fail-closed。
5. 后端测试通过。
6. 前端 typecheck 通过。
7. 未新增写路由、ERPNext 写调用、outbox/worker/internal。
8. 禁改目录 diff 为空。
9. 未执行 commit / push / PR / tag / 生产发布。
