# TASK-006F1 CSV 公式注入防护整改工程任务单

- 任务编号：TASK-006F1
- 模块：加工厂对账单
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-15 21:49 CST
- 作者：技术架构师
- 前置依赖：TASK-006F 审计不通过，审计意见指出 CSV 导出未防护公式注入
- 任务边界：只修复 CSV 导出公式注入防护和 factory-statement contract 反向测试；不得进入 TASK-006G，不得修改后端，不得新增导出接口，不得实现提交发票/付款/GL。

## 一、任务目标

修复 `factoryStatementExport.ts` 中 `escapeCsvCell()` 只处理 CSV 格式转义、未处理 Excel/WPS 公式注入的问题。

必须实现：

1. 对以危险公式前缀开头的单元格进行安全前置单引号。
2. 覆盖 `=`, `+`, `-`, `@`, tab, CR, LF 等危险前缀。
3. 保留现有逗号、换行、双引号 CSV 转义能力。
4. 不使用 `Number/parseFloat` 重算金额。
5. 补 factory-statement contract 反向测试，确保后续不会回退。
6. TASK-006G 继续阻塞。

## 二、风险说明

CSV 导出字段包含：

```text
supplier
statement_no
subcontract_no
inspection_no
company
remark/log 文案（如有）
```

如果这些业务文本以公式前缀开头，例如：

```text
=HYPERLINK("http://evil.example","click")
+cmd|' /C calc'!A0
-2+3
@SUM(1+1)
\t=HYPERLINK(...)
```

财务人员用 Excel/WPS 打开 CSV 时，可能被解释为公式、触发外链访问或其他安全风险。因此导出必须把公式前缀作为数据文本处理。

## 三、允许修改文件

```text
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/utils/factoryStatementExport.ts
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-factory-statement-contracts.mjs
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-factory-statement-contracts.mjs
/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-006F1_CSV公式注入防护整改_交付证据.md
```

如当前导出测试已经有独立前端测试文件，允许最小修改对应测试文件。

## 四、禁止修改文件

```text
/Users/hh/Desktop/领意服装管理系统/07_后端/**
/Users/hh/Desktop/领意服装管理系统/.github/**
/Users/hh/Desktop/领意服装管理系统/02_源码/**
```

禁止新增：

```text
后端导出接口
ERPNext /api/resource 前端直连
internal worker 调用
Purchase Invoice submit
Payment Entry
GL Entry
failed/dead outbox 重建
```

## 五、实现要求

### 1. CSV 安全转义函数

`escapeCsvCell()` 或等价函数必须按以下顺序处理：

```text
1. 将 null/undefined 转为空字符串。
2. 将输入转为字符串。
3. 检测公式注入危险前缀。
4. 如果危险，则前置单引号 `'`。
5. 再执行 CSV 格式转义：双引号转 `""`，包含逗号/双引号/换行时整体加双引号。
```

危险前缀必须至少覆盖：

```text
=
+
-
@
\t
\r
\n
```

建议实现：

```ts
const FORMULA_INJECTION_PREFIX = /^[=+\-@\t\r\n]/

const neutralizeCsvFormula = (value: string): string => {
  if (FORMULA_INJECTION_PREFIX.test(value)) {
    return `'${value}`
  }
  return value
}
```

注意：

```text
1. 不要 trim 后再判断；前导空格是否危险可另行扩展，但本任务至少覆盖首字符危险前缀。
2. 单引号是数据文本前缀，不是 CSV quote。
3. 如果加单引号后仍包含逗号/双引号/换行，仍必须按 CSV 规则加双引号。
```

### 2. 导出字段覆盖

公式注入防护必须应用于所有 CSV 单元格，不仅是 supplier。

至少包括：

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

即使金额是字符串，也统一走 `escapeCsvCell()`。

### 3. 不得引入金额重算

禁止：

```text
Number(net_amount)
parseFloat(net_amount)
Number(item.net_amount)
parseFloat(item.net_amount)
```

## 六、契约门禁要求

`check-factory-statement-contracts.mjs` 必须新增/确认规则：

```text
1. factoryStatementExport.ts 必须包含公式注入前缀防护逻辑。
2. 必须识别 `=`, `+`, `-`, `@`, tab/CR/LF 风险前缀。
3. 如删除 neutralize/FORMULA 相关逻辑，门禁失败。
4. 导出逻辑不得使用 Number/parseFloat 重算金额字段。
```

`test-factory-statement-contracts.mjs` 必须新增反向场景：

```text
□ escapeCsvCell 未处理 `=HYPERLINK(...)` 时失败。
□ escapeCsvCell 未处理 `+SUM(...)` 时失败。
□ escapeCsvCell 未处理 `-2+3` 时失败。
□ escapeCsvCell 未处理 `@SUM(...)` 时失败。
□ escapeCsvCell 未处理 tab 前缀时失败。
□ 合法实现通过。
```

如果 contract 脚本无法直接执行函数测试，也必须通过 fixture 源码扫描证明：

```text
1. 有危险前缀正则或等价判断。
2. 有前置单引号逻辑。
3. 所有 CSV cell 均走统一 escape 函数。
```

## 七、验收标准

```text
□ `=HYPERLINK(...)` 导出为 `'=HYPERLINK(...)` 或 CSV 等价安全文本。
□ `+SUM(...)` 导出为 `'+SUM(...)`。
□ `-2+3` 导出为 `'-2+3`。
□ `@SUM(...)` 导出为 `'@SUM(...)`。
□ tab 前缀公式导出时被前置单引号。
□ 逗号、双引号、换行仍按 CSV 规则正确转义。
□ 所有 CSV 单元格统一经过安全转义。
□ 未使用 Number/parseFloat 重算金额。
□ npm run check:factory-statement-contracts 通过。
□ npm run test:factory-statement-contracts 通过，并包含公式注入反向用例。
□ npm run verify 通过。
□ npm audit --audit-level=high 通过。
□ 禁改扫描确认未修改后端、.github、02_源码。
```

## 八、交付前自测命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc

npm run check:factory-statement-contracts
npm run test:factory-statement-contracts
npm run verify
npm audit --audit-level=high

rg -n "parseFloat\(|Number\(" src/views/factory_statement src/utils scripts
rg -n "fetch\(|axios|/api/resource|factory-statements/internal|run-once|submitPurchaseInvoice|Payment Entry|GL Entry|createPaymentEntry|createGlEntry" src scripts

git diff --name-only -- /Users/hh/Desktop/领意服装管理系统/07_后端 /Users/hh/Desktop/领意服装管理系统/.github /Users/hh/Desktop/领意服装管理系统/02_源码
```

说明：`Number` 或 `parseFloat` 如用于非金额字段，交付说明必须逐条解释；金额字段不得用其重算。

## 九、交付说明必须包含

```text
1. 修改文件清单。
2. CSV 公式注入防护策略。
3. 危险前缀覆盖清单。
4. 新增 contract 反向测试场景数。
5. npm run verify 结果。
6. npm audit 结果。
7. 禁改扫描结果。
8. 明确声明未修改后端、.github、02_源码。
9. 明确声明未提交 Purchase Invoice、未创建 Payment Entry/GL Entry。
10. 明确声明未实现 failed/dead outbox 重建。
```

## 十、下一步门禁

```text
TASK-006F1 审计通过后，才允许重新判断是否进入 TASK-006G 本地封版复审。
TASK-006G 必须单独下发，不得由 F1 自动宣布封版完成。
```
