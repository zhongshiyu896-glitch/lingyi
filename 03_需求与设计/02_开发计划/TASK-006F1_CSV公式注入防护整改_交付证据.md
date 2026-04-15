# TASK-006F1 CSV 公式注入防护整改交付证据

- 任务编号：TASK-006F1
- 前置状态：TASK-006F 审计不通过（CSV 公式注入防护缺失）
- 完成时间：2026-04-15

## 1. 修改文件清单

1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/utils/factoryStatementExport.ts`
2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs`
3. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs`
4. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F1_CSV公式注入防护整改_交付证据.md`

## 2. CSV 公式注入防护策略

`factoryStatementExport.ts` 已新增并启用全字段统一防护：

1. `FORMULA_INJECTION_PREFIX = /^[=+\-@\t\r\n]/`
2. `neutralizeCsvFormula(value)`：命中危险前缀时前置单引号 `'`
3. `escapeCsvCell(value)` 处理顺序：
   - `null/undefined -> ''`
   - 转字符串
   - 公式注入中和（前置 `'`）
   - CSV quote 转义（`" -> ""`，含逗号/引号/换行时整体双引号包裹）

该策略对所有 CSV 单元格生效，不只 supplier 字段。

## 3. 危险前缀覆盖清单

已覆盖并由契约门禁强校验：

1. `=`
2. `+`
3. `-`
4. `@`
5. `\t`（tab）
6. `\r`（CR）
7. `\n`（LF）

## 4. Contract 反向测试场景

`test-factory-statement-contracts.mjs` 反向测试已新增并通过：

1. `export util formula prefix missing equals`
2. `export util formula prefix missing plus`
3. `export util formula prefix missing minus`
4. `export util formula prefix missing at`
5. `export util formula prefix missing tab`
6. `export util formula prefix missing cr`
7. `export util formula prefix missing lf`

说明：总场景数由 `19` 增加到 `26`，包含任务单要求的 5 类注入前缀反向用例和合法实现通过用例。

## 5. 验证命令结果

执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:factory-statement-contracts`：通过（Scanned files: 8）
2. `npm run test:factory-statement-contracts`：通过（scenarios=26）
3. `npm run verify`：通过
4. `npm audit --audit-level=high`：通过（`found 0 vulnerabilities`）

## 6. 扫描结果

### 6.1 Number/parseFloat 扫描

命令：
`rg -n "parseFloat\(|Number\(" src/views/factory_statement src/utils scripts`

结果：
- `src/utils/factoryStatementExport.ts` 无 `parseFloat/Number`。
- 命中项位于：
  - 详情/列表/打印页面的路由或显示格式化（非金额重算导出逻辑）
  - 契约脚本测试 fixture（故意反向样例）

### 6.2 风险关键词扫描

命令：
`rg -n "fetch\(|axios|/api/resource|factory-statements/internal|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|createPaymentEntry|createGlEntry" src scripts`

结果：
- 命中主要来自契约脚本规则定义与 fixture 反向样例。
- 未在 `factoryStatementExport.ts` 增加任何 `fetch/axios` 调用。

### 6.3 禁改目录扫描

命令：
`git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/07_后端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码`

结果：
- 仍有历史既有脏改动（后端文件）显示；本次 TASK-006F1 未新增修改这些目录。

## 7. 合规声明

1. 未修改后端、`.github`、`02_源码`（本任务新增改动范围内）。
2. 未提交 Purchase Invoice。
3. 未创建 Payment Entry / GL Entry。
4. 未实现 failed/dead outbox 重建。
5. 未新增后端导出接口。

## 8. 结论

TASK-006F1 已完成：CSV 公式注入防护已在导出单元格统一生效，危险前缀覆盖完整，契约门禁与反向测试已补齐并通过验证。

结论：建议进入 TASK-006F1 审计复核；是否进入 TASK-006G 需单独任务单放行。
