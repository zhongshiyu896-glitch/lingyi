# TASK-006B 加工厂对账单后端模型迁移与草稿 API 工程任务单

- 任务编号：TASK-006B
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 17:25 CST
- 作者：技术架构师
- 前置依赖：TASK-006A 审计意见书第 161 份已通过
- 任务边界：只做后端模型、迁移、生成草稿、列表、详情、权限审计和测试；禁止确认、取消、调整、ERPNext Purchase Invoice 写入、前端页面。

## 一、任务目标

实现加工厂对账单本地后端基线：创建 `ly_factory_statement`、`ly_factory_statement_item`、`ly_factory_statement_log` 三张表，基于 `ly_subcontract_inspection` 验货记录粒度生成对账单草稿，提供列表和详情接口，并完成登录鉴权、动作权限、供应商资源权限、安全审计、操作审计、幂等和重复对账防护。

## 二、冻结口径

以下口径来自 TASK-006A 审计通过结论，不允许改动：

1. 对账来源粒度：`ly_subcontract_inspection` 验货记录粒度。
2. 只允许从服务端外发验货事实生成对账单，不允许信任前端传入明细金额。
3. 金额公式：`gross_amount = sum(item.gross_amount)`。
4. 金额公式：`deduction_amount = sum(item.deduction_amount)`。
5. 金额公式：`net_amount = gross_amount - deduction_amount`。
6. `inspected_qty=0` 时 `rejected_rate=0`。
7. 幂等策略：`idempotency_key + request_hash`，同 key 同 hash replay，异 hash 返回 `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。
8. ERPNext 边界：TASK-006B 禁止创建 `Purchase Invoice`。
9. 前端边界：TASK-006B 禁止新增或修改前端页面和前端 API。

## 三、允许修改文件

新建：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006b_create_factory_statement_tables.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_api.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_models.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_idempotency.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006B_加工厂对账单后端模型迁移与草稿API_交付证据.md
```

允许按需修改：

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/main.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/__init__.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/__init__.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/__init__.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
```

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_*.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/**
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tools/**
```

禁止新增接口：

```text
POST /api/factory-statements/{id}/confirm
POST /api/factory-statements/{id}/cancel
POST /api/factory-statements/{id}/payable-draft
```

## 五、数据表要求

### 1. `ly_schema.ly_factory_statement`

必备字段：

| 字段 | 要求 |
| --- | --- |
| `id` | 主键。 |
| `statement_no` | 非空唯一。 |
| `company` | 非空。 |
| `supplier` | 非空。 |
| `supplier_name` | 可空快照。 |
| `from_date` | 非空。 |
| `to_date` | 非空。 |
| `total_order_count` | 非空，默认 0。 |
| `total_delivered_qty` | 非空，默认 0。 |
| `total_inspected_qty` | 非空，默认 0。 |
| `total_accepted_qty` | 非空，默认 0。 |
| `total_rejected_qty` | 非空，默认 0。 |
| `rejected_rate` | 非空，默认 0。 |
| `gross_amount` | 非空，默认 0。 |
| `deduction_amount` | 非空，默认 0。 |
| `net_amount` | 非空，默认 0。 |
| `status` | 非空，只允许 `draft`，确认状态留到 TASK-006C。 |
| `idempotency_key` | 非空。 |
| `request_hash` | 非空。 |
| `created_by` | 非空，来自当前登录用户。 |
| `created_at` | 非空。 |
| `updated_at` | 非空。 |

索引和约束：

| 名称 | 要求 |
| --- | --- |
| `uk_ly_factory_statement_no` | `statement_no` 唯一。 |
| `uk_ly_factory_statement_idempotency` | `company + idempotency_key` 唯一。 |
| `idx_ly_factory_statement_company_supplier_period` | `company, supplier, from_date, to_date`。 |
| `idx_ly_factory_statement_status` | `status`。 |
| `idx_ly_factory_statement_supplier_status` | `company, supplier, status`。 |

### 2. `ly_schema.ly_factory_statement_item`

必备字段：

| 字段 | 要求 |
| --- | --- |
| `id` | 主键。 |
| `statement_id` | 非空，关联 statement。 |
| `subcontract_id` | 非空。 |
| `subcontract_no` | 非空快照。 |
| `inspection_id` | 非空，来源 `ly_subcontract_inspection.id`。 |
| `inspection_no` | 可空快照。 |
| `receipt_batch_no` | 可空快照。 |
| `company` | 非空。 |
| `supplier` | 非空。 |
| `item_code` | 非空。 |
| `sales_order` | 可空快照。 |
| `work_order` | 可空快照。 |
| `delivered_qty` | 非空，来自验货/回料事实。 |
| `inspected_qty` | 非空。 |
| `accepted_qty` | 非空。 |
| `rejected_qty` | 非空。 |
| `rejected_rate` | 非空。 |
| `subcontract_rate` | 非空。 |
| `gross_amount` | 非空。 |
| `deduction_amount` | 非空。 |
| `net_amount` | 非空。 |
| `source_status` | 非空，必须为 `inspected`。 |
| `source_settlement_status` | 非空，生成草稿后应为 `statement_locked`。 |
| `source_snapshot_json` | 非空，保存来源关键字段快照。 |
| `created_at` | 非空。 |

索引和约束：

| 名称 | 要求 |
| --- | --- |
| `idx_ly_factory_statement_item_statement` | `statement_id`。 |
| `idx_ly_factory_statement_item_subcontract` | `subcontract_id`。 |
| `idx_ly_factory_statement_item_inspection` | `inspection_id`。 |
| `uk_ly_factory_statement_item_statement_inspection` | `statement_id + inspection_id` 唯一。 |
| `uk_ly_factory_statement_item_inspection` | `inspection_id` 唯一，防止同一验货记录重复进入多个本地对账单。 |

### 3. `ly_schema.ly_factory_statement_log`

必备字段：

| 字段 | 要求 |
| --- | --- |
| `id` | 主键。 |
| `statement_id` | 可空；失败场景可能尚无 statement。 |
| `action` | 非空，TASK-006B 只允许 `create / list / detail / fail`。 |
| `operator` | 非空，来自当前登录用户。 |
| `operated_at` | 非空。 |
| `remark` | 可空，必须脱敏。 |
| `before_snapshot` | 可空 JSON。 |
| `after_snapshot` | 可空 JSON。 |
| `request_id` | 可空，必须为归一化后的 request_id。 |

索引：

| 名称 | 要求 |
| --- | --- |
| `idx_ly_factory_statement_log_statement_time` | `statement_id, operated_at`。 |
| `idx_ly_factory_statement_log_action_time` | `action, operated_at`。 |

## 六、接口范围

### 1. 生成对账单草稿

```text
POST /api/factory-statements/
```

入参：

```json
{
  "company": "Lingyi",
  "supplier": "SUP-001",
  "from_date": "2026-04-01",
  "to_date": "2026-04-30",
  "idempotency_key": "client-generated-key"
}
```

出参：

```json
{
  "code": "0",
  "message": "success",
  "data": {
    "name": 1,
    "statement_no": "FS-202604-0001",
    "status": "draft",
    "gross_amount": "5000.00",
    "deduction_amount": "300.00",
    "net_amount": "4700.00"
  }
}
```

实现要求：

1. 先校验登录态。
2. 再校验 `factory_statement:create` 动作权限。
3. 再解析 `company + supplier` 资源权限，权限源不可用 fail closed。
4. 从 `ly_subcontract_inspection` 读取来源，必须满足：
   - `company = 入参 company`
   - `supplier = 入参 supplier` 或通过 `ly_subcontract_order.supplier` 匹配
   - `status = inspected`
   - `settlement_status = unsettled`
   - `inspected_at between from_date and to_date`
   - `net_amount >= 0`
5. 生成草稿必须在一个本地事务内完成：创建 statement、创建 items、写 log、锁定 inspections。
6. 锁定 inspections 时必须写：`settlement_status='statement_locked'`、`statement_id`、`statement_no`、`settlement_locked_by=current_user`、`settlement_locked_at`。
7. 若本地事务 commit 失败，不得留下半对账单或半锁定来源。
8. 不得调用 ERPNext `Purchase Invoice`。

### 2. 查询对账单列表

```text
GET /api/factory-statements/
```

入参：

```text
company, supplier, status, from_date, to_date, page, page_size
```

要求：

1. 必须先校验 `factory_statement:read`。
2. 列表必须按用户 `company + supplier` 资源权限过滤。
3. 不得通过前端过滤替代后端过滤。
4. 返回分页格式：`items, total, page, page_size`。
5. `items` 必须包含 `statement_no, company, supplier, from_date, to_date, status, gross_amount, deduction_amount, net_amount, created_at`。

### 3. 查询对账单详情

```text
GET /api/factory-statements/{id}
```

要求：

1. 必须先校验 `factory_statement:read` 动作权限，再查询具体 ID，避免 403/404 存在性枚举。
2. 查询到 statement 后必须做 `company + supplier` 资源级权限。
3. 返回 `statement, items, logs`。
4. items 必须来自 `ly_factory_statement_item` 快照，不允许实时重算覆盖快照金额。

## 七、权限动作

在权限矩阵中新增：

```text
factory_statement:read
factory_statement:create
```

角色建议：

| 角色 | read | create |
| --- | --- | --- |
| Finance Manager | 是 | 是 |
| Accounts User | 是 | 是 |
| Production Manager | 是 | 否 |
| Subcontract Manager | 是 | 是 |
| Workshop Manager | 否 | 否 |
| Sales Manager | 否 | 否 |
```

要求：

1. static 权限源和 ERPNext role 聚合口径必须同时补齐。
2. 生产环境不得因 static 权限源缺配置而放行。
3. Company-only 权限不能替代 Supplier 权限。
4. ERPNext User Permission 查询失败必须 fail closed。

## 八、错误码要求

必须实现或预留以下错误码：

| 错误码 | 场景 |
| --- | --- |
| `FACTORY_STATEMENT_PERMISSION_DENIED` | 动作权限或资源权限不足。 |
| `FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE` | ERPNext 权限源不可用。 |
| `FACTORY_STATEMENT_SUPPLIER_REQUIRED` | supplier 为空。 |
| `FACTORY_STATEMENT_COMPANY_REQUIRED` | company 为空。 |
| `FACTORY_STATEMENT_PERIOD_INVALID` | 日期范围非法。 |
| `FACTORY_STATEMENT_SOURCE_NOT_FOUND` | 无可对账验货记录。 |
| `FACTORY_STATEMENT_SOURCE_ALREADY_LOCKED` | 来源已被锁定或已进入对账单。 |
| `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT` | 同一幂等键下 request_hash 不一致。 |
| `FACTORY_STATEMENT_DATABASE_READ_FAILED` | 数据库读取失败。 |
| `FACTORY_STATEMENT_DATABASE_WRITE_FAILED` | 数据库写入或 commit 失败。 |
| `FACTORY_STATEMENT_INTERNAL_ERROR` | 未知异常，响应不得泄露 SQL 或异常明文。 |

## 九、审计要求

1. 401 未登录必须写安全审计。
2. 403 动作权限拒绝必须写安全审计。
3. 403 资源权限拒绝必须写安全审计。
4. 503 权限源不可用必须写安全审计。
5. 生成草稿成功必须写操作审计。
6. 生成草稿失败必须写操作失败审计。
7. 列表和详情可以写轻量操作审计；详情越权必须写安全审计。
8. 审计日志不得记录 Authorization、Cookie、密码、Secret、Token 明文。
9. `request_id` 必须使用既有归一化逻辑。

## 十、测试要求

必须新增/覆盖以下测试：

1. 迁移能创建三张表和关键索引。
2. `POST /api/factory-statements/` 可从两条 `ly_subcontract_inspection` 生成草稿。
3. 加工费 `5000`、扣款 `300` 时 `net_amount=4700`。
4. `inspected_qty=0` 时 `rejected_rate=0`。
5. 生成草稿后来源 inspection 变为 `statement_locked`，写入 `statement_id/statement_no`。
6. 相同 `company + idempotency_key + request_hash` 重试 replay 同一 statement。
7. 相同 `company + idempotency_key` 但 request_hash 不同返回 `FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT`。
8. 已锁定 inspection 不会再次生成新对账单。
9. 无 `factory_statement:create` 权限时 POST 返回 403 且不落库。
10. 无 Supplier 资源权限时 POST 返回 403 且不落库。
11. 权限源不可用时返回 503 且不落库。
12. `GET /api/factory-statements/` 按资源权限过滤。
13. `GET /api/factory-statements/{id}` 先动作鉴权后查 ID，无读权限访问存在/不存在 ID 均返回 403。
14. 详情返回 statement、items、logs，items 金额来自快照。
15. 数据库 commit 失败归类为 `FACTORY_STATEMENT_DATABASE_WRITE_FAILED`。
16. 普通日志和审计日志不泄露 SQL、Authorization、Cookie、Secret、Token。
17. 扫描确认没有 `Purchase Invoice`、`/api/resource/Purchase Invoice`、`payable-draft` 实现。
18. 扫描确认没有修改 `06_前端/**`、`.github/**`、`02_源码/**`。

## 十一、验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_factory_statement_api.py tests/test_factory_statement_models.py tests/test_factory_statement_permissions.py tests/test_factory_statement_idempotency.py tests/test_factory_statement_audit.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "Purchase Invoice|/api/resource/Purchase Invoice|payable-draft|payable_draft" app tests
cd /Users/hh/Desktop/领意服装管理系统
git diff --name-only -- '06_前端' '.github' '02_源码'
```

预期：

1. 定向测试通过。
2. 全量 pytest 通过。
3. unittest discover 通过。
4. py_compile 通过。
5. `Purchase Invoice/payable-draft` 扫描不得出现 TASK-006B 业务实现入口；只允许文档或未来任务说明。
6. 禁改目录扫描无输出。

## 十二、交付证据要求

创建：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006B_加工厂对账单后端模型迁移与草稿API_交付证据.md
```

证据必须包含：

1. 修改文件清单。
2. 新增表和索引清单。
3. 接口清单和权限动作。
4. 金额公式测试结果。
5. 幂等 replay / conflict 测试结果。
6. 来源 inspection 锁定测试结果。
7. 权限和资源权限测试结果。
8. 审计日志测试结果。
9. ERPNext Purchase Invoice 禁入扫描结果。
10. 前端、workflow、`02_源码` 禁改扫描结果。
11. 是否建议进入 TASK-006C。

## 十三、交付后回复格式

```text
TASK-006B 已完成。

已输出/修改：
- /07_后端/lingyi_service/app/models/factory_statement.py
- /07_后端/lingyi_service/app/schemas/factory_statement.py
- /07_后端/lingyi_service/app/routers/factory_statement.py
- /07_后端/lingyi_service/app/services/factory_statement_service.py
- /07_后端/lingyi_service/migrations/versions/task_006b_create_factory_statement_tables.py
- /03_需求与设计/02_开发计划/TASK-006B_加工厂对账单后端模型迁移与草稿API_交付证据.md

验证：
- 定向 pytest：[结果]
- 全量 pytest：[结果]
- unittest：[结果]
- py_compile：[结果]
- Purchase Invoice/payable-draft 禁入扫描：[结果]
- 前端/workflow/02_源码 禁改扫描：[结果]

结论：建议/不建议进入 TASK-006C。
```
