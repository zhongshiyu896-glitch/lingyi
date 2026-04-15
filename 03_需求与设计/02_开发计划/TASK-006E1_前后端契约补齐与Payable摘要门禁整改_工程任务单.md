# TASK-006E1 前后端契约补齐与 Payable 摘要门禁整改工程任务单

- 任务编号：TASK-006E1
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 20:32 CST
- 作者：技术架构师
- 前置依赖：TASK-006E 审计不通过，审计意见书第 167 份指出 2 个 P1 阻断问题
- 任务边界：只修复前后端契约不一致：创建对账单缺 `company`、后端 list/detail 缺 payable outbox 摘要；不得进入 TASK-006F，不得调用 internal worker，不得直连 ERPNext，不得提交 Purchase Invoice，不得创建 Payment Entry/GL Entry。

## 一、任务目标

关闭 TASK-006E 审计发现的两个高危问题：

1. 前端创建对账单时未提交后端必填 `company`，导致创建入口不可用。
2. 前端详情页用 `payable_outbox_status/purchase_invoice_name/logs` 判断按钮门禁，但后端 list/detail 当前未返回这些字段，导致 active payable outbox 后页面仍可能展示取消/重复生成应付草稿入口。

本任务目标：

```text
1. 前端 create payload 与后端 FactoryStatementCreateRequest.company 契约一致。
2. company 不得硬编码，不得从 localStorage token 等不可信来源推断。
3. 后端 list/detail 返回 payable outbox 摘要和 purchase_invoice_name。
4. 后端 detail 返回 logs 或前端不再声明依赖 logs；本任务推荐后端补 logs。
5. 前端按钮门禁必须基于后端返回的真实 payable outbox 摘要。
6. factory-statement contract 增加 company 必填和 payable 摘要字段门禁。
```

## 二、继续冻结的边界

以下内容仍然禁止：

```text
调用 /api/factory-statements/internal/payable-draft-sync/run-once
调用任何 /internal/*/run-once
直连 ERPNext /api/resource
提交 ERPNext Purchase Invoice
创建 Payment Entry
创建 GL Entry
打印页面
对账调整单
自动反冲/红冲
绕过后端权限校验
```

## 三、允许修改文件

### 前端允许修改

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs
```

如 TASK-006E 已修改 `package.json`、router 或 permission store 且本任务需要同步修正，允许最小修改：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts
```

### 后端允许修改

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_factory_statement*.py
```

后端修改只允许补 list/detail 响应字段和测试，不得改变 D/D1 的 payable worker 状态机。

### 文档允许新增

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006E1_前后端契约补齐与Payable摘要门禁整改_交付证据.md
```

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
```

本任务不得新增迁移，除非后端当前确实缺少字段且无法从现有 outbox/statement 表查询。若必须迁移，需先停下说明，不得自行扩 scope。

## 五、整改一：create payload 补齐 company 契约

### 1. 前端 API 类型

`FactoryStatementCreatePayload` 必须包含必填 `company`：

```ts
export interface FactoryStatementCreatePayload {
  company: string
  supplier: string
  from_date: string
  to_date: string
  idempotency_key: string
}
```

禁止：

```text
company?: string
company: ''
company: '默认公司'
company 从 token/localStorage 里解析
company 隐藏硬编码
```

### 2. 列表页创建弹窗

创建弹窗必须补 company 输入或选择。

最低要求：

```text
1. company 字段必填。
2. supplier/from_date/to_date/idempotency_key 仍必填。
3. company 为空时前端禁止提交，并提示“请选择/输入公司”。
4. 提交 payload 必须包含 company。
5. 后端仍是权限权威，前端传 company 只作为业务入参，不代表权限放行。
```

如果已有全局公司选择器/当前公司接口，可优先接入；若没有，可先使用文本输入，但必须提示“后端会校验公司权限”。

### 3. 后端测试

如后端已有 company 必填测试，保留；否则补：

```text
□ 缺 company 返回统一 422/错误信封或 FastAPI 校验错误。
□ 有 company 且有权限时 create 成功。
□ 有 company 但无资源权限时返回 403。
```

## 六、整改二：后端 list/detail 返回 payable outbox 摘要

### 1. list 响应必须返回

后端 `GET /api/factory-statements/` 每行必须返回：

```text
payable_outbox_id
payable_outbox_status
purchase_invoice_name
payable_error_code
payable_error_message
```

字段允许为 null，但不能缺失。

摘要选择规则：

```text
1. 每个 statement 取最新 payable outbox。
2. 最新排序建议：created_at desc, id desc。
3. 如果 statement.status=payable_draft_created 且 purchase_invoice_name 非空，应同步返回 purchase_invoice_name。
4. 不得 N+1 查询；可先按当前页 statement ids 批量取 outbox，再在 Python 合并。后续可优化窗口函数。
```

### 2. detail 响应必须返回

后端 `GET /api/factory-statements/{id}` 必须返回：

```text
payable_outbox_id
payable_outbox_status
purchase_invoice_name
payable_error_code
payable_error_message
payable_outboxes[]
logs[]
```

`payable_outboxes[]` 最少字段：

```text
id
status
erpnext_purchase_invoice
erpnext_docstatus
erpnext_status
last_error_code
last_error_message
created_at
updated_at
```

`logs[]` 最少字段：

```text
action
operator
operated_at
remark
```

如后端已有 logs 表但未返回，补返回；如无 logs 表，本任务应明确失败或删除前端对 logs 的强依赖。推荐补返回。

### 3. active payable outbox 定义

后端/前端同口径：

```text
pending
processing
succeeded
```

前端按钮判断必须基于后端返回的 `payable_outbox_status` 或 `payable_outboxes[]`。

## 七、整改三：前端按钮门禁修正

详情页必须满足：

```text
1. payable_outbox_status 缺失时，不得默认为“无 active outbox”后展示取消/生成应付草稿。
2. 如果后端字段缺失或请求失败，按钮应 fail closed：隐藏或禁用取消/生成应付草稿。
3. pending/processing/succeeded 时取消按钮隐藏或禁用。
4. pending/processing/succeeded 时生成应付草稿按钮隐藏或禁用。
5. failed/dead 是否允许重新生成/重试，前端不得自行判断；如无 retry API，本轮不展示重试按钮。
```

推荐工具函数：

```ts
const activePayableStatuses = new Set(['pending', 'processing', 'succeeded'])
const hasActivePayableOutbox = computed(() => activePayableStatuses.has(detail.value?.payable_outbox_status || ''))
const payableSummaryLoaded = computed(() => Object.prototype.hasOwnProperty.call(detail.value || {}, 'payable_outbox_status'))
```

如果无法确认摘要已加载，按钮 fail closed。

## 八、契约门禁补强

`check-factory-statement-contracts.mjs` 必须新增检查：

```text
1. src/api/factory_statement.ts 的 FactoryStatementCreatePayload 中 company 为必填，不得是 company?。
2. createFactoryStatement 调用 payload 不得 omit company。
3. FactoryStatementList.vue 创建表单必须包含 company 字段。
4. FactoryStatementList.vue submitCreate 必须提交 company。
5. FactoryStatementDetailData/ListItem 类型必须包含 payable_outbox_status 和 purchase_invoice_name。
6. 详情页不得在 payable_outbox_status 缺失时默认允许 cancel/payable-draft。
7. 禁止 internal worker、ERPNext /api/resource、裸 fetch、submit PI、Payment Entry、GL Entry 的规则继续保留。
```

反向测试必须新增：

```text
□ create payload company 可选时失败。
□ create payload 缺 company 时失败。
□ 创建弹窗无 company 字段时失败。
□ detail 类型缺 payable_outbox_status 时失败。
□ detail 类型缺 purchase_invoice_name 时失败。
□ 详情页将缺失 payable_outbox_status 当作无 active outbox 时失败。
□ 合法实现通过。
```

## 九、验收标准

```text
□ 创建对账单弹窗有 company 字段，且必填。
□ submitCreate payload 包含 company。
□ src/api/factory_statement.ts 中 company 为必填。
□ 后端 list 返回 payable_outbox_status/purchase_invoice_name 字段。
□ 后端 detail 返回 payable_outbox_status/purchase_invoice_name/payable_outboxes/logs。
□ 创建 pending payable outbox 后，详情页 reload 能显示 pending。
□ pending/processing/succeeded 时取消按钮不可用。
□ pending/processing/succeeded 时生成应付草稿按钮不可用。
□ npm run check:factory-statement-contracts 通过。
□ npm run test:factory-statement-contracts 通过，并包含新增反向 fixture。
□ npm run verify 通过。
□ 后端 factory statement 定向测试通过。
□ 未调用 internal worker。
□ 未直连 ERPNext /api/resource。
□ 未提交 Purchase Invoice。
□ 未创建 Payment Entry/GL Entry。
□ 未修改 .github、02_源码。
```

## 十、交付前自测命令

### 前端

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc

npm run check:factory-statement-contracts
npm run test:factory-statement-contracts
npm run verify
npm audit --audit-level=high

rg -n "fetch\(|/api/resource|factory-statements/internal|payable-draft-sync/run-once|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|Authorization|Cookie|token|secret|password" src scripts
```

### 后端

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_factory_statement*.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)

rg -n "submit\(|docstatus\s*=\s*1|Payment Entry|GL Entry|create_payment|submit_purchase_invoice" app tests
```

### 禁改扫描

```bash
git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码
```

## 十一、交付说明必须包含

```text
1. 修改文件清单。
2. company 契约修复说明。
3. payable outbox 摘要字段清单。
4. list/detail 后端响应样例。
5. 前端按钮 fail-closed 规则说明。
6. 契约门禁新增规则和反向测试场景数。
7. 前端自测命令和结果。
8. 后端自测命令和结果。
9. 明确声明未调用 internal worker。
10. 明确声明未直连 ERPNext /api/resource。
11. 明确声明未提交 Purchase Invoice、未创建 Payment Entry/GL Entry。
12. 明确声明未修改 .github、02_源码。
```

## 十二、下一步门禁

```text
TASK-006E1 审计通过后，才允许重新判断是否进入 TASK-006F。
TASK-006F 不得自动开始，必须由架构师单独下发任务单。
```
