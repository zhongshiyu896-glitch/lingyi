# TASK-006E 加工厂对账单前端联调与契约门禁交付证据

## 1. 任务信息
- 任务编号：TASK-006E
- 前置：TASK-006D1 审计通过
- 结论：完成前端 API、列表/详情联调、权限按钮控制、契约门禁与反向测试接入

## 2. 修改文件清单
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/factory_statement.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/factory_statement/FactoryStatementDetail.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/index.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/permission.ts`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006E_加工厂对账单前端联调与契约门禁_交付证据.md`

## 3. 路由与页面
- 新增路由：`/factory-statements/list`
- 新增路由：`/factory-statements/detail`
- 新增页面：`FactoryStatementList.vue`
- 新增页面：`FactoryStatementDetail.vue`

## 4. 新增 API 方法
`src/api/factory_statement.ts` 已封装并统一使用 `request + ApiResponse`：
- `fetchFactoryStatements(query)`
- `fetchFactoryStatementDetail(statementId)`
- `createFactoryStatement(payload)`
- `confirmFactoryStatement(statementId, payload)`
- `cancelFactoryStatement(statementId, payload)`
- `createFactoryStatementPayableDraft(statementId, payload)`

未封装内部/禁用方法：
- `runFactoryStatementPayableWorker`
- `payableDraftSyncRunOnce`
- `submitPurchaseInvoice`
- `createPaymentEntry`
- `createGlEntry`

## 5. 权限字段与 denylist
`src/stores/permission.ts` 已新增按钮权限字段：
- `factory_statement_read`
- `factory_statement_create`
- `factory_statement_confirm`
- `factory_statement_cancel`
- `factory_statement_payable_draft_create`
- `factory_statement_payable_draft_worker`（内部动作，强制清零）

内部动作 denylist 已加入：
- `factory_statement:payable_draft_worker`

## 6. 契约脚本与反向测试
- 新增：`check-factory-statement-contracts.mjs`
- 新增：`test-factory-statement-contracts.mjs`
- `package.json` 已新增：
  - `check:factory-statement-contracts`
  - `test:factory-statement-contracts`
- `verify` 已接入新契约检查与测试

反向 fixture 场景数：
- `test-factory-statement-contracts`：`scenarios=9`

## 7. 自测命令结果
在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

1. `npm run check:factory-statement-contracts`
- 结果：通过
- 输出：`Factory statement contract check passed. Scanned files: 6`

2. `npm run test:factory-statement-contracts`
- 结果：通过
- 输出：`All factory statement contract fixture tests passed. scenarios=9`

3. `npm run verify`
- 结果：通过
- 关键输出：
  - `check-production-contracts` 通过
  - `test-production-contracts` 通过
  - `check-style-profit-contracts` 通过
  - `test-style-profit-contracts` 通过（`scenarios=475`）
  - `check-factory-statement-contracts` 通过
  - `test-factory-statement-contracts` 通过
  - `typecheck` 通过
  - `build` 通过

4. `npm audit --audit-level=high`
- 结果：`found 0 vulnerabilities`

## 8. 关键扫描与解释
执行：
`rg -n "fetch\(|/api/resource|factory-statements/internal|payable-draft-sync/run-once|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|Authorization|Cookie|token|secret|password" src scripts`

说明：
- 命中主要来自：
  - 既有通用鉴权请求文件（`src/api/auth.ts`、`src/api/request.ts`、`src/api/bom.ts`、`src/api/workshop.ts`）
  - 契约脚本与反向测试 fixture（`scripts/check-*.mjs`、`scripts/test-*.mjs`）
- 在本任务新增的 factory statement 业务页面/API 中，未发现禁用调用。

执行：
`rg -n "fetch\(|/api/resource|factory-statements/internal|payable-draft-sync/run-once|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|Authorization|Cookie|token|secret|password|factory_statement:payable_draft_worker" src/api/factory_statement.ts src/views/factory_statement src/router/index.ts src/stores/permission.ts`

结果：
- 仅命中 `src/stores/permission.ts` 中 denylist 条目：`factory_statement:payable_draft_worker`
- 属于允许命中（内部动作屏蔽用途）

## 9. 禁改边界说明
执行：
`git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/07_后端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码`

结果：
- 输出非空，命中为既有后端历史改动（来自前序 TASK-006B~D1 链路）
- 本次 TASK-006E 未新增后端、`.github`、`02_源码` 变更

## 10. 合规声明
- 未调用 `/api/factory-statements/internal/payable-draft-sync/run-once`
- 未调用任何 `/internal/*/run-once`
- 未直连 ERPNext `/api/resource`
- 未实现或调用 `submit Purchase Invoice`
- 未实现或调用 `Payment Entry`
- 未实现或调用 `GL Entry`
- 未修改后端业务代码（TASK-006E 范围内）
- 未修改 `.github`、`02_源码`（TASK-006E 范围内）

## 11. 结论
- TASK-006E 开发与契约门禁已完成，前端本地验证通过。
- 建议进入审计复核；审计通过后再进入 TASK-006F。
