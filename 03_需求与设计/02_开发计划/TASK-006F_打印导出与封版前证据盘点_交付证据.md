# TASK-006F 打印导出与封版前证据盘点交付证据

- 任务编号：TASK-006F
- 前置状态：TASK-006E2 审计通过（第 169 份）
- 完成时间：2026-04-15

## 1. 修改文件清单

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`
2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementPrint.vue`
3. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/utils/factoryStatementExport.ts`
4. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`
5. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs`
6. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs`
7. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F_加工厂对账单封版前证据盘点.md`
8. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F_打印导出与封版前证据盘点_交付证据.md`

## 2. 新增打印路由

- 路由：`/factory-statements/print`
- 页面：`FactoryStatementPrint.vue`
- 入口：详情页“打印”按钮。

## 3. 打印页数据来源说明

1. 打印页只调用 `fetchFactoryStatementDetail(statementId)`。
2. 未调用 `/api/factory-statements/internal/*`。
3. 未调用 `/api/resource`。
4. 未自动触发 `window.print()`，仅用户点击按钮后触发。

## 4. CSV 导出字段清单

CSV 字段为：
- `statement_no`
- `company`
- `supplier`
- `from_date`
- `to_date`
- `status`
- `gross_amount`
- `deduction_amount`
- `net_amount`
- `inspection_no`
- `subcontract_no`
- `subcontract_id`
- `accepted_qty`
- `rejected_qty`
- `rejected_rate`
- `item_gross_amount`
- `item_deduction_amount`
- `item_net_amount`

## 5. 金额不重算说明

1. 导出工具 `factoryStatementExport.ts` 直接使用详情接口返回的金额字段字符串/原值输出。
2. 导出工具未使用 `parseFloat`/`Number` 对金额字段重算。
3. `parseFloat/Number` 扫描仅命中 `FactoryStatementPrint.vue` 的 `statementId` 解析（路由参数转数字），不涉及金额计算。

## 6. 契约门禁新增规则与反向测试

### 6.1 新增规则

1. 打印页禁止 `/api/resource`。
2. 打印页禁止 internal/run-once。
3. 打印页禁止 submitPurchaseInvoice/createPaymentEntry/createGlEntry 及 Payment Entry/GL Entry 文案。
4. 打印页必须通过 `fetchFactoryStatementDetail` 加载数据。
5. 打印页禁止 `onMounted` 自动 `window.print()`。
6. 导出工具禁止 `fetch/axios`。
7. 导出工具禁止 `parseFloat/Number` 金额重算。
8. 详情页必须保留打印和“导出明细 CSV”入口；路由必须包含 `/factory-statements/print`。

### 6.2 反向测试结果

- `npm run test:factory-statement-contracts` 通过。
- 场景总数：`19`。
- 覆盖了任务单要求的 6 类新增反向场景（打印页 /api/resource、internal run-once、导出工具裸 fetch、导出工具 parseFloat(net_amount)、打印页 submit PI、合法实现通过）。

## 7. 验证命令与结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:factory-statement-contracts`：通过。
2. `npm run test:factory-statement-contracts`：通过（`scenarios=19`）。
3. `npm run verify`：通过。
4. `npm audit --audit-level=high`：通过（`found 0 vulnerabilities`）。

## 8. 扫描与禁改结果

### 8.1 关键字扫描

1. `rg -n "fetch\(|axios|/api/resource|factory-statements/internal|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|createPaymentEntry|createGlEntry" src/views/factory_statement/FactoryStatementPrint.vue src/utils/factoryStatementExport.ts`
   - 结果：无命中。
2. `rg -n "parseFloat\(|Number\(" src/views/factory_statement/FactoryStatementPrint.vue src/utils/factoryStatementExport.ts`
   - 结果：仅命中 `FactoryStatementPrint.vue` 的 `statementId` 路由参数解析；导出工具无命中。

### 8.2 禁改目录扫描

命令：
`git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/07_后端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码`

结果：仍有历史脏改动（后端既有文件）显示；本任务未新增对这些目录的改动。

## 9. 封版前证据盘点路径

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F_加工厂对账单封版前证据盘点.md`

## 10. 合规声明

1. 未调用 internal worker run-once。
2. 未直连 ERPNext `/api/resource`。
3. 未提交 Purchase Invoice、未创建 Payment Entry、未创建 GL Entry。
4. 未实现 failed/dead outbox 重建。
5. 未修改后端业务文件、`.github/**`、`02_源码/**`（历史脏改动除外）。

## 11. 结论

TASK-006F 前端打印/导出与契约门禁补强已完成，封版前证据盘点已输出，建议进入 TASK-006F 审计复核。
