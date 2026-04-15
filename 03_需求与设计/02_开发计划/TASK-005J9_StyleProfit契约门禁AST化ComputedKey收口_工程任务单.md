# TASK-005J9 Style Profit 契约门禁 AST 化 Computed Key 收口工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J9
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 20:22 CST
- 作者：技术架构师
- 前置审计：审计意见书第 127 份，`TASK-005J8` 有条件通过但存在高危内部方括号 computed key 绕过
- 当前有效前置：`TASK-005J8` 已修复跨行 computed key，但 `[actionMap['onClick']]: openHelp` 仍可绕过
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V4.6；`ADR-122`

## 1. 任务目标

停止继续叠加正则补丁，把 style-profit 契约门禁中“对象属性 / 方法 / computed key”的识别升级为 TypeScript AST 解析。当前正则捕获仍使用类似 `[^\]]+` 的方式处理 computed key，遇到内部方括号会提前截断，例如 `[actionMap['onClick']]: openHelp`，导致非字面量 computed action key 未被识别。

本任务要求：使用项目已有 `typescript` devDependency 的 compiler API 解析 `.ts/.tsx/.vue` script 内容，识别对象字面量成员中的普通属性、字符串属性、方法简写、计算属性、跨行计算属性和嵌套计算属性。正则可继续用于 Vue template / 文本禁线扫描，但不得再作为 computed key 语义判断的唯一依据。

本任务只修复前端契约门禁、测试和证据，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 127 份指出：

1. TASK-005J8 已修复跨行 `[actionMap\n  .onClick]` 绕过。
2. 但 computed key 表达式内部含方括号仍可绕过：`[actionMap['onClick']]: openHelp`。
3. 根因是 `check-style-profit-contracts.mjs` 仍使用 `[^^\]]+` / `[^\]]+` 类捕获 computed key 表达式，遇到内部 `]` 会提前截断。
4. 审计建议改为 balanced bracket scanner，或直接升级 AST 解析。
5. 架构决策：本轮直接升级 TypeScript AST 解析，避免继续陷入正则补洞循环。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 前端约定文档

如需记录门禁边界，可追加：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/README.md`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J9_StyleProfit契约门禁AST化ComputedKey收口_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J9_StyleProfit契约门禁AST化ComputedKey收口证据.md`（交付时新建）
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

## 4. 禁止修改文件与行为

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/**`。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`。
4. 禁止创建或修改任何 `TASK-006*` 文件。
5. 禁止提交 `.pytest-postgresql-*.xml`。
6. 禁止新增 `POST /api/reports/style-profit/snapshots` 的前端调用。
7. 禁止开放创建/生成/重算利润快照入口。
8. 禁止继续使用 `[^\]]+` 或固定窗口作为 computed key 语义判断主路径。
9. 禁止新增第三方 parser 依赖，除非先单独申请架构确认；本任务优先使用已有 `typescript` devDependency。
10. 禁止大改 production-contracts 非 style-profit 门禁。
11. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 使用 TypeScript Compiler API

必须使用 `typescript` 包解析 JS/TS 片段：

1. 对 `.ts/.tsx/.js/.jsx` 文件，直接读取并创建 `SourceFile`。
2. 对 `.vue` 文件，至少提取 `<script setup>` 与 `<script>` 内容后创建 `SourceFile`；template 文本扫描继续保留原门禁逻辑。
3. 遍历 `ObjectLiteralExpression`。
4. 对 `PropertyAssignment`、`MethodDeclaration`、`ShorthandPropertyAssignment`、`SpreadAssignment` 做分类。
5. 对 `ComputedPropertyName` 使用 AST 判断表达式类型，而不是手写 `]` 截断。

### 5.2 属性名分类规则

必须将对象成员属性名分类为：

1. `literal_key`：普通标识符、字符串字面量、数字字面量，以及字符串字面量 computed key，例如 `['onClick']`、`["label"]`。
2. `dynamic_computed_key`：非字面量 computed key，例如 `[ACTION_KEY]`、`[actionMap.onClick]`、`[actionMap['onClick']]`、`[getActionKey()]`、模板字符串变量等。
3. `unknown_key`：AST 无法安全判断的 key，默认 fail closed。

### 5.3 交互字段规则

以下成员必须识别为交互字段：

1. 普通属性：`onClick: openHelp`。
2. 字符串属性：`"onClick": openHelp`、`'handler': showRule`。
3. 方法简写：`onClick() {}`、`async submit() {}`。
4. 字符串方法名：`"onClick"() {}`、`'handler'() {}`。
5. 字符串字面量 computed key：`['onClick']: openHelp`、`["handler"]() {}`。
6. 非字面量 computed key：一律作为风险键，在 style-profit action/menu/toolbar/button/command 语境下 fail closed。

### 5.4 祖先链规则保持不变

AST 化不得削弱既有门禁：

1. 子 `meta/props/extra/payload/children` 内出现利润说明类字段时，必须检查全部祖先对象。
2. 任一祖先对象存在交互属性、交互方法、字符串字面量 computed key 或非字面量 computed key 时，必须按规则处理。
3. 字段顺序不影响判断。
4. 字段距离不影响判断。
5. 真实长距离 fixture 必须继续保留。
6. 非字面量 computed key 必须 fail closed。

### 5.5 SpreadAssignment 处理

对象中出现 spread 时必须保守处理：

1. 如果对象内已经有利润说明 label/title/description，且存在 `...action`、`...menuAction`、`...toolbarAction`、`...profitAction` 等疑似 action spread，必须失败。
2. 如果 spread 名称无法判断且对象处于 style-profit action/menu/toolbar/button/command 配置上下文，必须 fail closed 或输出明确风险错误。
3. 不允许因为 spread 无法解析就默认通过。

## 6. 必补反向测试

必须在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs` 中补充以下失败用例：

### 6.1 内部方括号 computed key

```ts
const actions = [
  {
    label: '利润计算说明',
    [actionMap['onClick']]: openHelp,
  },
]
```

预期：门禁失败。

### 6.2 内部双引号方括号 computed key

```ts
const actions = [
  {
    label: '利润计算说明',
    [actionMap["onClick"]]: openHelp,
  },
]
```

预期：门禁失败。

### 6.3 嵌套函数调用 computed key

```ts
const actions = [
  {
    label: '利润计算说明',
    [getActionKey(actionMap['onClick'])]: openHelp,
  },
]
```

预期：门禁失败。

### 6.4 模板字符串动态 computed key

```ts
const actions = [
  {
    label: '利润计算说明',
    [`${prefix}Click`]: openHelp,
  },
]
```

预期：门禁失败。

### 6.5 真实长距离 + 内部方括号 computed key

```ts
const actions = [
  {
    label: '利润计算说明',
    filler: '<真实1200字符>',
    [actionMap['onClick']]: openHelp,
  },
]
```

预期：门禁失败，并断言 `label` 与 `[actionMap` 的真实距离超过 1200。

### 6.6 子 meta label + 祖先内部方括号 computed key

```ts
const actions = [
  {
    meta: {
      label: '利润快照来源说明',
    },
    [actionMap['onClick']]: openHelp,
  },
]
```

预期：门禁失败。

### 6.7 spread + 利润说明 label

```ts
const actions = [
  {
    label: '利润计算说明',
    ...profitAction,
  },
]
```

预期：门禁失败。

## 7. 必保留成功测试

以下合法场景必须继续通过：

1. 字符串字面量 computed key：`['onClick']`、`["handler"]`、`['label']`，继续按既有门禁规则处理。
2. 跨行字符串字面量 computed key继续按既有规则处理。
3. 纯说明对象，无任何祖先交互字段。
4. `查看详情` + `onClick: goDetail`。
5. `查询` + `onClick: loadRows`。
6. `返回` + `onClick: goBack`。
7. Vue template 只读说明文案成功 fixture 继续通过。

## 8. 验证命令

### 8.1 前端验证

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

### 8.2 后端只读回归

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

### 8.3 AST 与内部方括号覆盖扫描

```bash
rg -n "typescript|createSourceFile|ObjectLiteralExpression|ComputedPropertyName|SpreadAssignment|actionMap\['onClick'\]|actionMap\[\"onClick\"\]|getActionKey\(actionMap|`\$\{prefix\}Click`|profitAction|dynamic_computed_key|unknown_key|fail closed" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

### 8.4 业务禁线扫描

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

## 9. 交付证据要求

工程师必须新建：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J9_StyleProfit契约门禁AST化ComputedKey收口证据.md`

证据文件必须包含：

1. 修改文件清单。
2. TypeScript AST 解析实现说明。
3. `.vue` script 提取策略说明。
4. computed key 分类规则：literal / dynamic / unknown。
5. SpreadAssignment fail closed 策略说明。
6. 新增反向测试清单。
7. 合法字符串字面量 computed key 成功 fixture 清单。
8. 真实长距离 fixture 生成方式与距离断言结果。
9. 所有验证命令和结果。
10. 禁改范围扫描结果。
11. commit hash。
12. 是否新增依赖：必须写“否，使用现有 typescript devDependency”。

## 10. 提交要求

### 10.1 白名单 staged

只允许 staged：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- 必要时允许的 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/README.md`
- 必要时允许的 style_profit 只读页面小范围修正文件
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J9_StyleProfit契约门禁AST化ComputedKey收口证据.md`
- 本任务相关架构、计划、审计文档

### 10.2 推荐提交信息

```bash
git commit -m "fix: parse style profit action keys with typescript ast"
```

## 11. 验收标准

1. `[actionMap['onClick']]: openHelp` 必须失败。
2. `[actionMap["onClick"]]: openHelp` 必须失败。
3. `[getActionKey(actionMap['onClick'])]: openHelp` 必须失败。
4. 模板字符串动态 key ``[`${prefix}Click`]`` 必须失败。
5. 真实长距离 + 内部方括号 computed key 必须失败，且距离断言超过 1200。
6. 子 meta label + 祖先内部方括号 computed key 必须失败。
7. spread + 利润说明 label 必须 fail closed。
8. 字符串字面量 computed key 既有测试继续通过或按既有利润门禁失败。
9. Vue script / script setup 中的 action 对象必须被 AST 扫描覆盖。
10. Vue template 文本禁线既有测试不回退。
11. `npm run test:style-profit-contracts` 通过。
12. `npm run verify` 通过。
13. `npm audit --audit-level=high` 为 0 high vulnerabilities。
14. 后端 style-profit API 定向回归通过。
15. 未新增第三方 parser 依赖。
16. 未开放创建快照入口。
17. 未进入 TASK-006。
