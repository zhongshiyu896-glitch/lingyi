# TASK-006E 加工厂对账单前端联调与契约门禁工程任务单

- 任务编号：TASK-006E
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 20:03 CST
- 作者：技术架构师
- 前置依赖：TASK-006D1 审计通过，允许进入 TASK-006E
- 任务边界：只做加工厂对账单前端 API 封装、列表/详情页面、权限按钮、统一错误提示和前端契约门禁；不得调用 internal worker，不得直连 ERPNext，不得实现打印/付款/GL/提交 Purchase Invoice。

## 一、任务目标

在 TASK-006B~D1 后端能力基础上，完成加工厂对账单前端联调：

1. 新增前端 API 文件 `src/api/factory_statement.ts`，统一走 `request()`。
2. 新增对账单列表页，支持查询、创建草稿、查看状态和进入详情。
3. 新增对账单详情页，展示 statement/items/logs/payable outbox 摘要。
4. 按权限展示按钮：创建、确认、取消、生成应付草稿。
5. `生成应付草稿` 只调用 `/api/factory-statements/{id}/payable-draft` 创建本地 outbox，不调用 internal worker。
6. 前端不得调用 `/api/factory-statements/internal/payable-draft-sync/run-once`。
7. 前端不得直连 ERPNext `/api/resource`。
8. 新增 factory-statement 前端契约扫描和反向测试，并纳入 `npm run verify`。

## 二、继续冻结的边界

以下内容仍然禁止：

```text
调用 /api/factory-statements/internal/payable-draft-sync/run-once
调用任何 /internal/*/run-once
直连 ERPNext /api/resource
提交 ERPNext Purchase Invoice
Payment Entry
GL Entry
打印页面
对账调整单
自动反冲/红冲
裸 fetch()
在前端硬编码 Authorization/Cookie/token/secret/password
```

## 三、允许新增/修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006E_加工厂对账单前端联调与契约门禁_交付证据.md
```

如需要抽公共格式化工具，允许新增：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/utils/factoryStatement.ts
```

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
```

说明：TASK-006E 是前端任务。除非审计指出前后端字段不一致，否则不得修改后端。

## 五、前端 API 契约

新增：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts
```

必须统一：

```text
import { request, type ApiResponse } from '@/api/request'
```

禁止：

```text
fetch(
axios
/api/resource
internal/payable-draft-sync/run-once
Authorization/Cookie/token/secret/password 硬编码
```

### 1. 类型定义

必须至少定义：

```ts
export interface FactoryStatementListQuery {
  supplier?: string
  status?: string
  from_date?: string
  to_date?: string
  page: number
  page_size: number
}

export interface FactoryStatementListItem {
  id: number
  statement_no: string
  company: string
  supplier: string
  from_date: string
  to_date: string
  total_qty: string
  accepted_qty?: string | null
  rejected_qty?: string | null
  gross_amount: string
  deduction_amount: string
  net_amount: string
  status: string
  payable_outbox_id?: number | null
  payable_outbox_status?: string | null
  purchase_invoice_name?: string | null
  created_at: string
}

export interface FactoryStatementDetailData extends FactoryStatementListItem {
  confirmed_by?: string | null
  confirmed_at?: string | null
  cancelled_by?: string | null
  cancelled_at?: string | null
  cancel_reason?: string | null
  items: FactoryStatementItem[]
  logs: FactoryStatementLog[]
  payable_outboxes?: FactoryStatementPayableOutboxSummary[]
}

export interface FactoryStatementCreatePayload {
  supplier: string
  from_date: string
  to_date: string
  idempotency_key: string
}

export interface FactoryStatementConfirmPayload {
  idempotency_key: string
  remark?: string
}

export interface FactoryStatementCancelPayload {
  idempotency_key: string
  reason: string
}

export interface FactoryStatementPayableDraftPayload {
  idempotency_key: string
  payable_account: string
  cost_center: string
  posting_date: string
  remark?: string
}
```

字段名以实际后端 DTO 为准，但不得弱化以下字段：

```text
statement_no
supplier
from_date/to_date
gross_amount/deduction_amount/net_amount
status
items
logs
payable_outbox_status
purchase_invoice_name
```

### 2. API 方法

必须封装：

```ts
fetchFactoryStatements(query)
fetchFactoryStatementDetail(statementId)
createFactoryStatement(payload)
confirmFactoryStatement(statementId, payload)
cancelFactoryStatement(statementId, payload)
createFactoryStatementPayableDraft(statementId, payload)
```

不得封装：

```ts
runFactoryStatementPayableWorker
payableDraftSyncRunOnce
submitPurchaseInvoice
createPaymentEntry
createGlEntry
```

## 六、页面设计

### 1. 列表页

新增：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue
```

路由建议：

```text
/factory-statements/list
```

页面能力：

```text
1. 查询条件：supplier、status、from_date、to_date。
2. 表格字段：statement_no、company、supplier、期间、total_qty、gross_amount、deduction_amount、net_amount、status、payable_outbox_status、purchase_invoice_name。
3. 操作：详情。
4. 有 create 权限时显示“生成对账单草稿”按钮。
5. 创建草稿弹窗输入 supplier/from_date/to_date/idempotency_key。
6. company 不允许前端手填，必须由后端权限上下文决定。
7. 查询按钮在无 read 权限时禁用，并显示无权限空状态。
```

### 2. 详情页

新增：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue
```

路由建议：

```text
/factory-statements/detail?id=123
```

页面能力：

```text
1. 展示 statement 基本信息。
2. 展示金额：gross_amount、deduction_amount、net_amount。
3. 展示状态：draft/confirmed/cancelled/payable_draft_created。
4. 展示 payable outbox 状态：pending/processing/succeeded/failed/dead。
5. 展示 ERPNext Purchase Invoice 草稿号 purchase_invoice_name；仅展示，不提供提交按钮。
6. 展示 items 明细：inspection_no、subcontract_no、delivered_qty、accepted_qty、rejected_qty、rejected_rate、gross_amount、deduction_amount、net_amount。
7. 展示 logs 操作日志。
8. 有 confirm 权限且 status=draft 时显示“确认对账单”。
9. 有 cancel 权限且 status=draft/confirmed 且无 active payable outbox 时显示“取消对账单”。
10. 有 payable_draft_create 权限且 status=confirmed 时显示“生成应付草稿”。
11. pending/processing/succeeded payable outbox 存在时，取消按钮必须隐藏或禁用，并提示“应付草稿处理中/已生成，不可取消”。
12. 生成应付草稿弹窗输入 payable_account、cost_center、posting_date、idempotency_key、remark。
```

禁止页面能力：

```text
1. 不显示 internal worker run-once 按钮。
2. 不显示提交 Purchase Invoice 按钮。
3. 不显示 Payment Entry 按钮。
4. 不显示 GL Entry 按钮。
5. 不直接打开 ERPNext /api/resource 修改页面。
```

## 七、权限按钮规则

`src/stores/permission.ts` 需新增或映射以下按钮权限：

```text
factory_statement_read
factory_statement_create
factory_statement_confirm
factory_statement_cancel
factory_statement_payable_draft_create
```

实际字段可沿用后端 `button_permissions` 返回命名，但必须满足：

```text
1. read=false 时，不请求列表/详情数据。
2. create=false 时，不显示创建草稿按钮。
3. confirm=false 时，不显示确认按钮。
4. cancel=false 时，不显示取消按钮。
5. payable_draft_create=false 时，不显示生成应付草稿按钮。
6. internal worker 权限不得进入 buttonPermissions。
```

内部动作必须加入前端 denylist：

```text
factory_statement:payable_draft_worker
```

并强制清零对应按钮字段，避免 UI 误暴露 internal worker。

## 八、前端契约门禁

必须新增：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs
```

并更新 `package.json`：

```json
{
  "scripts": {
    "check:factory-statement-contracts": "node scripts/check-factory-statement-contracts.mjs",
    "test:factory-statement-contracts": "node scripts/test-factory-statement-contracts.mjs",
    "verify": "npm run check:production-contracts && npm run test:production-contracts && npm run check:style-profit-contracts && npm run test:style-profit-contracts && npm run check:factory-statement-contracts && npm run test:factory-statement-contracts && npm run typecheck && npm run build"
  }
}
```

### 1. 门禁必须扫描范围

```text
src/api/factory_statement.ts
src/views/factory_statement/**
src/router/**
src/stores/**
src/App.vue
src/components/**（如存在全局菜单）
```

### 2. 禁止规则

门禁必须拦截：

```text
裸 fetch(
/api/resource
/api/factory-statements/internal
payable-draft-sync/run-once
run-once
Purchase Invoice submit
Payment Entry
GL Entry
submitPurchaseInvoice
createPaymentEntry
createGlEntry
Authorization
Cookie
token
secret
password
factory_statement:payable_draft_worker 出现在 UI/路由
```

`factory_statement:payable_draft_worker` 只允许出现在 permission store denylist/内部动作清零逻辑中。

### 3. 反向测试必须覆盖

```text
□ api 文件裸 fetch 必须失败。
□ api 文件直连 /api/resource 必须失败。
□ 页面调用 /api/factory-statements/internal/payable-draft-sync/run-once 必须失败。
□ 页面出现 run-once 按钮必须失败。
□ 页面出现 submit Purchase Invoice 必须失败。
□ 页面出现 Payment Entry/GL Entry 必须失败。
□ UI/路由出现 factory_statement:payable_draft_worker 必须失败。
□ permission store 未清零 internal worker 权限必须失败。
□ 合法列表/详情/创建/确认/取消/payable-draft API 通过。
```

## 九、错误提示要求

前端必须使用 `request()` 统一错误处理。

页面提示建议：

```text
AUTH_UNAUTHORIZED -> 登录已失效，请重新登录
AUTH_FORBIDDEN -> 无权执行该操作
FACTORY_STATEMENT_PAYABLE_OUTBOX_ACTIVE -> 应付草稿处理中或已生成，不可取消
FACTORY_STATEMENT_INVALID_STATUS -> 当前状态不允许执行该操作
FACTORY_STATEMENT_IDEMPOTENCY_CONFLICT -> 重复请求参数不一致，请刷新后重试
FACTORY_STATEMENT_ERPNEXT_UNAVAILABLE -> ERPNext 服务暂不可用，请稍后重试
FACTORY_STATEMENT_PAYABLE_ACCOUNT_INVALID -> 应付科目无效
FACTORY_STATEMENT_COST_CENTER_INVALID -> 成本中心无效
```

禁止吞错：

```text
catch 后静默失败
统一显示“操作成功”但实际后端失败
根据 404/403 差异提示资源是否存在
```

## 十、状态展示规则

状态中文：

```text
draft -> 草稿
confirmed -> 已确认
cancelled -> 已取消
payable_draft_created -> 应付草稿已生成
```

outbox 状态中文：

```text
pending -> 待同步
processing -> 同步中
succeeded -> 已生成草稿
failed -> 同步失败
dead -> 同步死信
```

按钮禁用规则：

```text
confirm：仅 draft + 有 confirm 权限。
cancel：仅 draft/confirmed + 有 cancel 权限 + 无 active payable outbox。
payable-draft：仅 confirmed + 有 payable_draft_create 权限 + 无 active payable outbox。
```

active payable outbox：

```text
pending
processing
succeeded
```

## 十一、验收标准

```text
□ /factory-statements/list 可按 supplier/status/from_date/to_date 查询。
□ 无 read 权限时列表不发请求，并显示无权限空状态。
□ 有 create 权限时可创建草稿，成功后刷新列表。
□ /factory-statements/detail?id=xxx 可展示 statement/items/logs/payable 状态。
□ 有 confirm 权限且 status=draft 时显示确认按钮，并可调用 confirm API。
□ 有 cancel 权限且 status=draft/confirmed 且无 active payable outbox 时显示取消按钮。
□ active payable outbox 存在时取消按钮隐藏或禁用，并显示不可取消提示。
□ 有 payable_draft_create 权限且 status=confirmed 时可创建 payable outbox。
□ 生成应付草稿后页面只显示 outbox pending/processing/succeeded，不调用 internal worker。
□ purchase_invoice_name 只展示，不提供提交或付款按钮。
□ npm run check:factory-statement-contracts 通过。
□ npm run test:factory-statement-contracts 通过，且包含反向 fixture。
□ npm run verify 通过。
□ npm audit --audit-level=high 通过。
□ 禁改扫描确认未修改 07_后端、.github、02_源码。
```

## 十二、交付前自测命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc

npm run check:factory-statement-contracts
npm run test:factory-statement-contracts
npm run verify
npm audit --audit-level=high

rg -n "fetch\(|/api/resource|factory-statements/internal|payable-draft-sync/run-once|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|Authorization|Cookie|token|secret|password" src scripts

git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/07_后端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码
```

如 `rg` 命中合法 denylist/测试 fixture，交付说明必须逐条解释。

## 十三、交付说明必须包含

```text
1. 修改文件清单。
2. 新增页面路由。
3. 新增 API 方法清单。
4. 新增权限按钮字段和 denylist 说明。
5. 新增契约脚本和反向测试场景数。
6. npm run verify 结果。
7. npm audit 结果。
8. 明确声明未调用 internal worker。
9. 明确声明未直连 ERPNext /api/resource。
10. 明确声明未提交 Purchase Invoice、未创建 Payment Entry/GL Entry。
11. 明确声明未修改后端、.github、02_源码。
```

## 十四、下一步门禁

```text
TASK-006E 审计通过后，才允许进入 TASK-006F。
TASK-006F 可考虑打印/导出/封版证据，但必须单独下发任务单。
```
