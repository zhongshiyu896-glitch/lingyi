# TASK-006F 打印导出与封版前证据盘点工程任务单

- 任务编号：TASK-006F
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 21:23 CST
- 作者：技术架构师
- 前置依赖：TASK-006E2 审计通过，允许进入 TASK-006F 前置任务单/审计放行流程
- 任务边界：只做加工厂对账单打印视图、当前对账单明细导出、前端契约补强和封版前证据盘点；不得新增后端财务计算口径，不得提交 Purchase Invoice，不得创建 Payment Entry/GL Entry，不得实现 failed/dead outbox 重建。

## 一、任务目标

在 TASK-006A~E2 已完成对账单生成、确认、取消、payable outbox、ERPNext Purchase Invoice 草稿、前端联调和防重门禁的基础上，完成加工厂对账单的可交付闭环：

1. 增加对账单打印友好视图。
2. 支持导出当前对账单详情快照明细。
3. 在详情页提供“打印”和“导出明细”入口。
4. 导出数据必须来自已审计的详情接口返回快照，不得前端重算金额。
5. 打印和导出必须保留 statement_no、supplier、company、期间、金额、items 明细和状态。
6. 补强 factory-statement 前端契约门禁，禁止打印/导出功能绕过业务 API 或引入 ERPNext 直连。
7. 输出 TASK-006 封版前证据盘点，列出已完成链路、测试证据、剩余风险和不得发布项。

## 二、继续冻结的边界

以下内容仍然禁止：

```text
提交 ERPNext Purchase Invoice(docstatus=1)
Payment Entry
GL Entry
failed/dead payable outbox 重建/reset
对账调整单
自动反冲/红冲
新增后端金额重算接口
新增后端导出接口
前端直连 ERPNext /api/resource
调用 internal worker run-once
绕过 request() 的裸 fetch
```

说明：TASK-006F 的打印/导出只基于 `GET /api/factory-statements/{id}` 返回的已冻结快照数据，不新增财务事实来源。

## 三、允许修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F_加工厂对账单封版前证据盘点.md
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F_打印导出与封版前证据盘点_交付证据.md
```

如需公共导出工具，允许新增：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/utils/factoryStatementExport.ts
```

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
```

如发现后端详情字段不足以打印/导出，必须停止并回报，不得在本任务中擅自补后端。

## 五、打印视图要求

### 1. 路由

建议新增：

```text
/factory-statements/print?id=123
```

对应文件：

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue
```

### 2. 数据来源

打印页只能调用：

```text
GET /api/factory-statements/{id}
```

禁止：

```text
/api/factory-statements/internal/*
/api/resource
直接请求 ERPNext
本地重算金额覆盖后端金额
```

### 3. 打印内容

打印视图必须包含：

```text
系统名称：领意服装管理系统
单据名称：加工厂对账单
statement_no
company
supplier
from_date / to_date
status
payable_outbox_status
purchase_invoice_name（如有）
gross_amount
deduction_amount
net_amount
items 明细
制表时间
打印人/当前用户（如前端已有 current user）
```

items 明细至少包含：

```text
inspection_no
subcontract_no 或 subcontract_id
accepted_qty
rejected_qty
rejected_rate
gross_amount
deduction_amount
net_amount
```

### 4. 打印行为

```text
1. 详情页提供“打印”按钮，打开打印路由或新窗口。
2. 打印页加载详情成功后，用户手动点击“打印”触发 window.print()。
3. 打印 CSS 必须隐藏操作按钮，仅保留单据内容。
4. 打印页不得自动触发 window.print()，避免页面加载即弹窗。
5. 无 read 权限或接口 403 时显示无权限，不得泄露单据是否存在。
```

## 六、导出要求

### 1. 导出范围

本任务只支持导出“当前详情页已加载的对账单快照明细”。

禁止：

```text
跨页批量导出
按供应商期间重新查询导出
新增后端导出接口
前端重新计算金额
```

### 2. 导出格式

允许实现 CSV 导出，文件名建议：

```text
factory_statement_<statement_no>.csv
```

CSV 内容必须包含：

```text
statement_no
company
supplier
from_date
to_date
status
gross_amount
deduction_amount
net_amount
inspection_no
subcontract_no/subcontract_id
accepted_qty
rejected_qty
rejected_rate
item_gross_amount
item_deduction_amount
item_net_amount
```

要求：

```text
1. CSV 必须做基础转义，避免逗号、换行、引号破坏格式。
2. 以字符串导出后端返回金额，不得使用 Number 重新格式化导致精度变化。
3. 导出按钮仅在详情成功加载且有 read 权限时显示。
4. 如果 items 为空，允许导出仅表头和主单摘要，但必须提示“无明细”。
```

## 七、详情页入口要求

`FactoryStatementDetail.vue` 增加：

```text
打印
导出明细 CSV
```

按钮规则：

```text
1. read=false 时不显示。
2. detail 未加载成功时禁用。
3. cancelled/confirmed/payable_draft_created 均可打印和导出。
4. pending/processing payable outbox 不影响打印/导出，因为打印的是当前快照，但必须显示 outbox 状态。
```

## 八、契约门禁补强

`check-factory-statement-contracts.mjs` 必须新增扫描：

```text
1. 打印页不得出现 /api/resource。
2. 打印页不得出现 internal/run-once。
3. 导出工具不得出现 fetch/axios。
4. 导出工具不得出现 Number( 金额字段 )、parseFloat( 金额字段 ) 之类重算金额逻辑。
5. 打印页不得出现 submitPurchaseInvoice/createPaymentEntry/createGlEntry。
6. 打印页不得出现 Payment Entry/GL Entry 按钮文案。
7. FactoryStatementPrint.vue 必须调用 fetchFactoryStatementDetail 或同等业务 API 封装。
8. package verify 必须包含 factory-statement contract 检查和测试。
```

反向测试必须新增：

```text
□ 打印页直连 /api/resource 必须失败。
□ 打印页调用 internal run-once 必须失败。
□ 导出工具裸 fetch 必须失败。
□ 导出工具 parseFloat(net_amount) 重算金额必须失败。
□ 打印页出现 submit Purchase Invoice 必须失败。
□ 合法打印页和 CSV 导出工具通过。
```

## 九、封版前证据盘点

必须新增：

```text
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F_加工厂对账单封版前证据盘点.md
```

内容必须包含：

```text
1. TASK-006A~F 任务链路表。
2. 每个阶段对应审计意见书编号和结论。
3. 后端能力清单：草稿、确认、取消、payable outbox、ERPNext PI 草稿、worker、active 防重。
4. 前端能力清单：列表、详情、创建、确认、取消、payable draft、打印、导出。
5. 禁止能力清单：提交 PI、Payment Entry、GL Entry、调整单、反冲、dead outbox 重建。
6. 测试命令和最近一次结果。
7. 剩余风险：datetime.utcnow warning、failed/dead outbox 重建策略、生产 ERPNext 权限源/主数据可用性、工作区历史未跟踪文件。
8. 是否建议进入本地封版审计：只能写“建议进入审计”，不得自行宣布封版通过。
```

## 十、验收标准

```text
□ 详情页有打印入口。
□ 打印页可加载并展示 statement/items/logs/payable 状态。
□ 打印页不自动弹出打印，用户点击后才 window.print()。
□ 打印 CSS 隐藏按钮，仅保留单据内容。
□ 详情页有导出 CSV 入口。
□ CSV 使用后端返回的字符串金额，不重算金额。
□ CSV 字段包含主单摘要和 items 明细。
□ 无 read 权限时不显示打印/导出入口。
□ 契约门禁新增打印/导出反向测试。
□ npm run check:factory-statement-contracts 通过。
□ npm run test:factory-statement-contracts 通过。
□ npm run verify 通过。
□ npm audit --audit-level=high 通过。
□ 禁改扫描确认未修改 07_后端、.github、02_源码。
□ 输出 TASK-006F 封版前证据盘点文档。
```

## 十一、交付前自测命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc

npm run check:factory-statement-contracts
npm run test:factory-statement-contracts
npm run verify
npm audit --audit-level=high

rg -n "fetch\(|axios|/api/resource|factory-statements/internal|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|createPaymentEntry|createGlEntry" src scripts
rg -n "parseFloat\(|Number\(" src/views/factory_statement src/utils scripts

git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/07_后端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码
```

说明：`Number` 或 `parseFloat` 如用于非金额字段，交付说明必须逐条解释；金额字段不得用其重算。

## 十二、交付说明必须包含

```text
1. 修改文件清单。
2. 新增打印路由。
3. 打印页数据来源说明。
4. CSV 导出字段清单。
5. 金额不重算说明。
6. 契约门禁新增规则和反向测试场景数。
7. npm run verify 结果。
8. npm audit 结果。
9. 禁改扫描结果。
10. TASK-006F 封版前证据盘点路径。
11. 明确声明未修改后端、.github、02_源码。
12. 明确声明未提交 Purchase Invoice、未创建 Payment Entry/GL Entry。
13. 明确声明未实现 failed/dead outbox 重建。
```

## 十三、下一步门禁

```text
TASK-006F 审计通过后，才允许进入 TASK-006G 本地封版复审。
TASK-006G 必须单独下发，不得由 F 自动宣布封版完成。
```
