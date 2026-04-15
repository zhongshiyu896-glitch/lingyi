# TASK-006D ERPNext 应付草稿 Outbox 集成工程任务单

- 任务编号：TASK-006D
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 19:04 CST
- 作者：技术架构师
- 前置依赖：TASK-006C1 审计通过，允许进入 TASK-006D
- 任务边界：只实现“已确认对账单 -> 本地 payable outbox -> 内部 worker 创建 ERPNext Purchase Invoice 草稿”的受控链路；前端页面、打印页面、付款、提交发票、GL/Payment Entry 仍冻结。

## 一、任务目标

在 TASK-006C/C1 已完成本地草稿、确认、取消的基础上，实现加工厂对账单生成 ERPNext 应付草稿的后端链路：

1. 新增 `POST /api/factory-statements/{id}/payable-draft`，只负责创建本地 payable outbox，不得在请求事务内直接调用 ERPNext。
2. 新增 payable outbox 模型、迁移、状态机、幂等键和事件键。
3. 新增内部 worker `POST /api/factory-statements/internal/payable-draft-sync/run-once`，由服务账号处理 due outbox。
4. worker 调用 ERPNext 创建 `Purchase Invoice` 草稿，必须保持 `docstatus=0`，不得提交发票。
5. ERPNext 不可用、权限源不可用、供应商/科目/成本中心校验失败时 fail closed。
6. 成功后回写 statement `status=payable_draft_created`、`purchase_invoice_name`、`payable_outbox_id` 等字段。
7. 全链路补齐权限、资源权限、安全审计、操作审计、统一错误信封和日志脱敏。

## 二、继续冻结的边界

以下内容仍然禁止：

```text
前端页面
打印页面
提交 ERPNext Purchase Invoice(docstatus=1)
付款 Payment Entry
GL Entry
对账调整单
自动反冲/红冲
按按钮直接调用 ERPNext 创建发票并同步返回发票名
```

本任务允许创建 ERPNext `Purchase Invoice` 草稿，但必须满足：

```text
1. 只能由内部 worker 调用 ERPNext。
2. 只能创建 docstatus=0 的草稿。
3. 请求接口 /payable-draft 只创建本地 outbox。
4. worker 成功前，接口不得伪造 purchase_invoice_name。
5. ERPNext 返回草稿且 docstatus=0 后，才允许本地标记 payable_draft_created。
```

## 三、允许修改/新增文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_outbox_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_payable_worker.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_purchase_invoice_adapter.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_006d_factory_statement_payable_outbox.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_payable*.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_permissions.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement_audit.py
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006D_ERPNext应付草稿Outbox集成_交付证据.md
```

如项目已有 ERPNext 通用适配器，允许复用既有封装，但必须保留本任务的 `Purchase Invoice` 专用边界测试。

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
```

除本任务明确列出的 payable outbox 迁移外，不得顺手改其他模块迁移。

## 五、数据库设计

### 1. 新增表：ly_factory_statement_payable_outbox

用途：记录“对账单生成 ERPNext Purchase Invoice 草稿”的异步同步任务。

建议字段：

| 字段 | 类型 | 要求 | 说明 |
| --- | --- | --- | --- |
| id | bigint | PK | outbox id |
| company | varchar | not null | 公司 |
| statement_id | bigint | not null | 对账单 id |
| statement_no | varchar | not null | 对账单号 |
| supplier | varchar | not null | 加工厂供应商 |
| idempotency_key | varchar | not null | 客户端幂等键 |
| request_hash | varchar | not null | 请求 hash |
| event_key | varchar | not null unique | 稳定事件键 |
| payload_json | json/jsonb | not null | ERPNext Purchase Invoice 草稿 payload |
| payload_hash | varchar | not null | payload hash |
| status | varchar | not null | pending/processing/succeeded/failed/dead |
| attempts | int | not null default 0 | 重试次数 |
| next_retry_at | datetime | nullable | 下次重试时间 |
| locked_by | varchar | nullable | worker id |
| locked_until | datetime | nullable | lease 截止 |
| erpnext_purchase_invoice | varchar | nullable | ERPNext PI name |
| erpnext_docstatus | int | nullable | ERPNext docstatus |
| erpnext_status | varchar | nullable | ERPNext 状态 |
| last_error_code | varchar | nullable | 脱敏错误码 |
| last_error_message | varchar | nullable | 脱敏错误摘要 |
| created_by | varchar | not null | 创建人 |
| created_at | datetime | not null | 创建时间 |
| updated_at | datetime | not null | 更新时间 |

建议索引：

```text
uk_ly_factory_statement_payable_event_key(event_key)
uk_ly_factory_statement_payable_idem(company, statement_id, idempotency_key)
idx_ly_factory_statement_payable_due(status, next_retry_at, id)
idx_ly_factory_statement_payable_statement(statement_id, status, id)
idx_ly_factory_statement_payable_supplier_period(company, supplier, created_at)
```

### 2. statement 表补充字段

如 TASK-006B/C 未补齐，允许补充：

```text
payable_outbox_id
purchase_invoice_name
payable_draft_created_by
payable_draft_created_at
payable_error_code
payable_error_message
```

不得删除或重算历史 statement item 金额快照。

## 六、接口设计

### 1. 创建 payable outbox

```text
POST /api/factory-statements/{id}/payable-draft
```

入参：

```json
{
  "idempotency_key": "client-generated-key",
  "payable_account": "2202 - Accounts Payable - LY",
  "cost_center": "Main - LY",
  "posting_date": "2026-04-15",
  "remark": "4月加工厂对账应付草稿"
}
```

出参：

```json
{
  "code": "0",
  "message": "ok",
  "data": {
    "statement_id": 1,
    "statement_no": "FS-202604-0001",
    "status": "confirmed",
    "payable_outbox_id": 10,
    "payable_outbox_status": "pending",
    "purchase_invoice_name": null,
    "net_amount": "4700.00"
  }
}
```

要求：

```text
1. 只允许 confirmed 状态生成 payable outbox。
2. cancelled 禁止生成。
3. draft 禁止生成。
4. payable_draft_created 重复调用同 key 同 hash replay；异 key 或异 hash 必须返回明确冲突。
5. statement net_amount 必须大于等于 0；负数场景本任务不做自动反冲，应 fail closed 或返回 FACTORY_STATEMENT_NEGATIVE_PAYABLE_UNSUPPORTED。
6. payable_account/cost_center 不得信任前端名称直接入账，必须由 ERPNext adapter 校验存在且属于 company。
7. 请求接口只创建本地 outbox，并写操作审计，不得直接调用 ERPNext 创建 Purchase Invoice。
```

### 2. 内部 worker run-once

```text
POST /api/factory-statements/internal/payable-draft-sync/run-once
```

入参 query/body：

```json
{
  "batch_size": 10,
  "dry_run": false
}
```

出参：

```json
{
  "code": "0",
  "message": "ok",
  "data": {
    "claimed": 1,
    "succeeded": 1,
    "failed": 0,
    "dead": 0,
    "dry_run": false
  }
}
```

要求：

```text
1. 该接口只能服务账号调用。
2. 普通 Finance Manager/Factory Statement Manager 不得调用。
3. 生产环境 dry_run 默认禁用；如保留 dry_run，必须先判断开关，再查询权限源/outbox。
4. worker 必须先本地 claim 并提交，再调用 ERPNext，避免数据库事务包住外部网络请求。
5. worker 必须支持 lease 超时恢复。
6. worker 必须支持 failed -> pending 重试策略；超过 max_attempts 标记 dead。
7. worker 必须写操作审计，dry_run 也必须有审计记录。
```

### 3. 精确重试接口

如 TASK-006D 实现 retry，必须使用精确目标，不得按 statement 最新 outbox 模糊选择：

```text
POST /api/factory-statements/{id}/payable-draft/retry
```

入参：

```json
{
  "outbox_id": 10,
  "idempotency_key": "retry-key",
  "reason": "ERPNext 临时超时后重试"
}
```

要求：

```text
1. 只能 retry failed/dead 且属于该 statement 的 outbox。
2. succeeded 不可 retry。
3. retry 不得影响其他 statement/outbox。
4. retry 必须写操作审计。
```

如果本轮不实现 retry，则必须在交付证据中明确说明，并保证 worker 自动重试足以覆盖本轮验收。

## 七、ERPNext Purchase Invoice 草稿 payload 规则

worker 生成 ERPNext `Purchase Invoice` 草稿时，payload 必须具备可追溯字段：

```text
doctype = Purchase Invoice
docstatus = 0
supplier = statement.supplier
company = statement.company
posting_date = request.posting_date
credit_to / payable_account = 校验后的 payable_account
cost_center = 校验后的 cost_center
custom_ly_factory_statement_id = statement.id
custom_ly_factory_statement_no = statement.statement_no
custom_ly_payable_outbox_id = outbox.id
custom_ly_outbox_event_key = outbox.event_key
remarks = remark
```

明细建议：

```text
1. 使用一个服务项或费用项表达加工费应付。
2. item_code / expense_account 必须来自后端配置或 ERPNext 校验，不得由前端任意传入。
3. amount = statement.net_amount。
4. gross/deduction 可放 custom 字段或 remarks，不得影响 grand_total 口径。
```

严禁：

```text
1. 创建 docstatus=1 的已提交发票。
2. 调用 submit。
3. 创建 Payment Entry。
4. 直接写 GL Entry。
5. 生成伪 PI name。
```

## 八、幂等与事件键规则

### 1. 请求幂等

`POST /payable-draft` 幂等键：

```text
company + statement_id + idempotency_key
```

`request_hash` 必须包含：

```text
statement_id
statement_no
supplier
net_amount
payable_account
cost_center
posting_date
remark
```

同 key 同 hash：返回首次 outbox。

同 key 异 hash：返回：

```text
FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT
```

### 2. event_key

`event_key` 必须稳定且不包含易变字段：

```text
statement_id
statement_no
supplier
net_amount
payable_account
cost_center
posting_date
```

不得包含：

```text
outbox_id
request_id
created_at
operator
attempts
locked_by
```

推荐：

```text
fspi:<sha256(canonical_payload核心字段)>
```

## 九、权限与资源权限

新增动作：

```text
factory_statement:payable_draft_create
factory_statement:payable_draft_worker
factory_statement:payable_draft_retry（如实现 retry）
```

角色建议：

```text
Finance Manager: payable_draft_create, read
Accounts Manager: payable_draft_create, read
Factory Statement Manager: read, confirm, cancel，不默认拥有 payable_draft_create
Service Account: payable_draft_worker，只限 worker scope
```

要求：

```text
1. 所有写接口先动作权限，再读取资源，避免 403/404 枚举。
2. 资源权限必须校验 company + supplier。
3. ERPNext Role/User Permission 权限源不可用时 fail closed。
4. Company-only 但无 supplier 权限的场景必须 fail closed，除非已有全局 supplier 权限明确允许。
5. 服务账号必须走最小权限策略，不得全模块全资源硬编码放行。
```

## 十、错误码

必须返回统一错误信封：

```json
{
  "code": "ERROR_CODE",
  "message": "用户可读错误",
  "detail": null
}
```

建议错误码：

```text
FACTORY_STATEMENT_NOT_FOUND
FACTORY_STATEMENT_FORBIDDEN
FACTORY_STATEMENT_INVALID_STATUS
FACTORY_STATEMENT_PAYABLE_ALREADY_CREATED
FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT
FACTORY_STATEMENT_PAYABLE_OUTBOX_NOT_RETRYABLE
FACTORY_STATEMENT_PAYABLE_ACCOUNT_INVALID
FACTORY_STATEMENT_COST_CENTER_INVALID
FACTORY_STATEMENT_NEGATIVE_PAYABLE_UNSUPPORTED
FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE
FACTORY_STATEMENT_ERPNEXT_PURCHASE_INVOICE_INVALID_STATUS
FACTORY_STATEMENT_PERMISSION_SOURCE_UNAVAILABLE
FACTORY_STATEMENT_DATABASE_WRITE_FAILED
FACTORY_STATEMENT_INTERNAL_ERROR
```

要求：

```text
1. 数据库写失败归类 DATABASE_WRITE_FAILED。
2. ERPNext 不可用归类 ERPNEXT_UNAVAILABLE。
3. ERPNext 返回非 docstatus=0 的 Purchase Invoice 必须 fail closed。
4. 未知异常不得泄露 str(exc) 给客户端。
5. 服务端普通日志不得输出 SQL 原文、Authorization/Cookie/Token/Secret/Password。
```

## 十一、审计要求

必须写操作审计：

```text
1. payable-draft outbox 创建成功。
2. payable-draft outbox 创建失败。
3. worker claim。
4. worker dry-run。
5. worker 创建 ERPNext Purchase Invoice 成功。
6. worker 创建 ERPNext Purchase Invoice 失败。
7. retry 成功/失败（如实现 retry）。
```

必须写安全审计：

```text
1. 401 未登录。
2. 403 动作权限拒绝。
3. 403 资源权限拒绝。
4. 503 权限源不可用。
5. 服务账号 scope 不足。
```

审计内容不得包含：

```text
Authorization
Cookie
Token
Secret
Password
ERPNext session 明文
SQL 原文
完整堆栈明文
```

## 十二、必须补测试

### A. payable-draft 接口测试

```text
□ confirmed statement 可创建 payable outbox。
□ draft statement 返回 FACTORY_STATEMENT_INVALID_STATUS。
□ cancelled statement 返回 FACTORY_STATEMENT_INVALID_STATUS。
□ payable_draft_created statement 重复同 key 同 hash replay。
□ 同 key 异 hash 返回 FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT。
□ payable_account 无效返回 FACTORY_STATEMENT_PAYABLE_ACCOUNT_INVALID。
□ cost_center 无效返回 FACTORY_STATEMENT_COST_CENTER_INVALID。
□ ERPNext 校验不可用返回 FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE。
□ 无动作权限用户访问存在/不存在 statement 均优先 403。
□ 无 supplier 资源权限用户返回 403 并写安全审计。
□ request 接口不调用 ERPNext 创建 Purchase Invoice。
```

### B. outbox/worker 测试

```text
□ worker 只能服务账号调用。
□ 普通财务角色不能调用 internal worker。
□ worker 先 claim commit，再调用 ERPNext。
□ ERPNext 创建 Purchase Invoice 草稿成功后 outbox=succeeded，statement=payable_draft_created。
□ ERPNext 返回 docstatus=0 才允许成功。
□ ERPNext 返回 docstatus=1/2 或缺 docstatus 必须失败。
□ ERPNext 已存在同 event_key 且 docstatus=0 时 replay 成功。
□ ERPNext 已存在同 event_key 但 docstatus=1/2 时 fail closed。
□ ERPNext 超时/不可用时 outbox=failed，并设置 next_retry_at。
□ max_attempts 后 outbox=dead。
□ lease 超时可被后续 worker 接管。
□ dry_run 不调用 ERPNext，不改 outbox，仍写操作审计。
```

### C. retry 测试（如实现）

```text
□ 精确 retry failed outbox 成功 requeue。
□ retry succeeded outbox 返回 FACTORY_STATEMENT_PAYABLE_OUTBOX_NOT_RETRYABLE。
□ retry 其他 statement 的 outbox 返回 403/404 同口径，避免枚举。
□ retry 不得影响同 statement 的其他 outbox。
```

### D. 防越界扫描

```text
□ 不存在提交 ERPNext Purchase Invoice 的代码路径。
□ 不存在 Payment Entry/GL Entry 创建路径。
□ 不存在前端页面改动。
□ 不存在 .github/02_源码 改动。
□ 不存在伪 purchase_invoice_name。
```

## 十三、交付前自测命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_factory_statement*.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice" app tests
rg -n "06_前端|factory_statement.ts|factory_statement/.*\.vue" /Users/hh/Desktop/领意服装管理系统/06_前端 || true

git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/06_前端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码
```

## 十四、交付说明必须包含

```text
1. 修改文件清单。
2. 新增表、字段、索引清单。
3. 新增接口清单。
4. ERPNext Purchase Invoice payload 示例，必须标注 docstatus=0。
5. 幂等键、request_hash、event_key 口径。
6. 权限动作和角色映射。
7. 服务账号最小权限策略。
8. outbox worker 状态机说明。
9. 自测命令和结果。
10. 明确声明未提交 Purchase Invoice。
11. 明确声明未创建 Payment Entry/GL Entry。
12. 明确声明未修改前端、.github、02_源码。
```

## 十五、下一步门禁

```text
TASK-006D 审计通过后，才允许进入 TASK-006E。
TASK-006E 预计进入前端只读/操作入口联调，但仍不得跳过权限和契约门禁。
```
