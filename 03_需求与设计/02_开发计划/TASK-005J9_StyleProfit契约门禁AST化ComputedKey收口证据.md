# TASK-005J9 Style Profit 契约门禁 AST 化 Computed Key 收口证据

## 1. 基本信息
- 任务编号：`TASK-005J9`
- 任务名称：Style Profit 契约门禁 AST 化 Computed Key 收口
- 执行时间：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`030a39b`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J9_StyleProfit契约门禁AST化ComputedKey收口证据.md`

## 3. TypeScript AST 解析实现
### 3.1 解析策略
- 在 `check-style-profit-contracts.mjs` 中引入 `typescript`，使用 Compiler API 解析 JS/TS 与 Vue 脚本内容。
- 对 `.ts/.tsx/.js/.jsx` 文件直接创建 `SourceFile`。
- 对 `.vue` 文件提取 `<script>` 与 `<script setup>` 文本后分别创建 `SourceFile`。
- Vue template 文本禁线扫描保持原有逻辑，不回退。

### 3.2 AST 主流程
新增 AST 分析函数并接入 style-profit surface 文件扫描：
- `extractScriptBlocksForAst()`
- `classifyPropertyNameNode()`
- `collectObjectLiteralsFromSourceFile()`
- `collectAstObjectChain()`
- `objectHasInteractiveMemberAst()`
- `objectHasExplanationFieldPhraseAst()`
- `collectDynamicComputedKeyInfos()`
- `hasSpreadRiskInExplanationChain()`
- `analyzeStyleProfitAstContracts()`

### 3.3 computed key 分类规则
- `literal_key`：普通标识符、字符串字面量键、字符串字面量 computed key（如 `['onClick']`、`["label"]`）。
- `dynamic_computed_key`：非字面量 computed key（如 `[ACTION_KEY]`、`[actionMap['onClick']]`、`[getActionKey()]`、模板表达式 key）。
- `unknown_key`：无法安全判定的 key，默认按 fail closed 处理。

### 3.4 祖先链与 fail closed
- 子对象（`meta/props/extra/payload/children`）命中利润说明字段时，向上检查全部祖先对象。
- 祖先对象存在交互字段（属性、方法、字符串字面量 computed key）时按既有门禁处理。
- 命中 `dynamic_computed_key` / `unknown_key` 且处于 style-profit action/menu/toolbar/button/command 上下文时，直接失败（fail closed）。

### 3.5 SpreadAssignment 收口
- 若说明字段对象链中存在疑似 action spread（如 `...profitAction` / `...menuAction` / `...toolbarAction`），按 fail closed 失败。
- 保持“无法安全判断即拒绝”的策略，避免 spread 绕过。

### 3.6 依赖边界
- 本任务未新增第三方 parser 依赖。
- 仅复用既有 `typescript` devDependency。

## 4. 新增反向测试（J9）
在 `test-style-profit-contracts.mjs` 新增并通过：
1. `[actionMap['onClick']]: openHelp` 必须失败。
2. `[actionMap["onClick"]]: openHelp` 必须失败。
3. `[getActionKey(actionMap['onClick'])]: openHelp` 必须失败。
4. ``[`${prefix}Click`]: openHelp`` 必须失败。
5. 真实长距离（1200）+ 内部方括号 computed key 必须失败，并做距离断言。
6. 子 `meta.label` + 祖先 `[actionMap['onClick']]` 必须失败。
7. `spread + 利润说明 label`（`...profitAction`）必须 fail closed。

## 5. 合法成功 fixture（保持通过）
- 字符串字面量 computed key：`['onClick']`、`["handler"]`、`['label']` 按既有规则处理。
- 跨行字符串字面量 computed key fixture 继续通过。
- 纯说明对象（无祖先交互字段）通过。
- `查看详情 / 查询 / 返回` 只读动作继续通过。
- Vue template 只读说明文案成功 fixture 不回退。

## 6. 验证命令与结果
### 6.1 前端验证
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=72`）

3. `npm run verify`
- 结果：通过（`check-production-contracts`、`test-production-contracts`、`check-style-profit-contracts`、`test-style-profit-contracts`、`typecheck`、`build` 全部通过）

4. `npm audit --audit-level=high`
- 结果：通过（`found 0 vulnerabilities`）

### 6.2 后端只读回归（未改后端代码）
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
- 结果：通过（`34 passed, 1 warning`）

2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

## 7. 扫描结果
### 7.1 AST 与内部方括号覆盖扫描
命令：
- `rg -n "typescript|createSourceFile|ObjectLiteralExpression|ComputedPropertyName|SpreadAssignment|actionMap\['onClick'\]|actionMap\[\"onClick\"\]|getActionKey\(actionMap|\$\{prefix\}Click|profitAction|dynamic_computed_key|unknown_key|fail closed" scripts/check-style-profit-contracts.mjs scripts/test-style-profit-contracts.mjs`

结果：命中 AST 关键实现点、内部方括号 computed key 反向用例、spread fail closed 用例（符合预期）。

### 7.2 业务禁线扫描
命令：
- `rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|...|profitRecalculate" src`

结果：无命中（退出码 1，符合“src 业务文件不得命中写入口语义”）。

## 8. 禁改范围确认
- 未修改：`07_后端/**`
- 未修改：`.github/**`
- 未修改：`02_源码/**`
- 未修改：`TASK-006*`
- 未提交：`.pytest-postgresql-*.xml`

## 9. 提交信息
- commit：`<待提交后回填>`
- message：`fix: parse style profit action keys with typescript ast`

## 10. 结论
`TASK-005J9` 已完成实现与验证：
- style-profit computed key 门禁已由正则补丁升级为 TypeScript AST 分析主路径。
- 内部方括号、嵌套表达式、模板表达式 dynamic computed key 均已 fail closed。
- spread 风险纳入 fail closed 收口。
- 前端门禁、后端只读回归全部通过。
- 未开放创建快照入口，未进入 `TASK-006`。
