# TASK-005J18 Runtime Mutator 源引用禁用门禁收口工程任务单

- 任务编号：TASK-005J18
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / 门禁策略收口
- 前置审计：审计意见书第 136 份
- 更新时间：2026-04-14 23:16 CST
- 作者：技术架构师

## 一、任务目标

将 style-profit surface 的 runtime mutator 门禁从“逐个追踪调用语法”升级为“源引用禁用 + 中转容器 fail closed”的收口策略。只要页面、API 封装、路由、store、通用入口中出现可用于运行时注入 action key 的 mutator 源引用或等价中转，就必须 fail closed，避免继续被 JS 语法变体绕过。

## 二、背景问题

TASK-005J17 已关闭第 135 份审计中的直接 comma、conditional、array、object container 中转调用，但审计官在第 136 份审计中复现以下新增绕过：

```ts
getMutator()(item, 'onClick', { value: openHelp })

const getMutator = () => Object.assign
getMutator()(item, { onClick: openHelp })

;(() => Object.defineProperty)()(item, 'onClick', { value: openHelp })

;[Object.defineProperty][0](item, 'onClick', { value: openHelp })

;({ dp: Object.defineProperty }).dp(item, 'onClick', { value: openHelp })

const nested = [[Object.defineProperty]]
nested[0][0](item, 'onClick', { value: openHelp })

const frozen = Object.freeze({ dp: Object.defineProperty })
frozen.dp(item, 'onClick', { value: openHelp })

const mutators = condition ? [Object.defineProperty] : [Object.defineProperty]
mutators[0](item, 'onClick', { value: openHelp })
```

这些绕过说明：继续补单个调用形态会导致门禁长期追着 JavaScript 语法变体跑。款式利润前端当前被架构冻结为只读页面，不需要在 style-profit surface 内使用 `Object.defineProperty/Object.defineProperties/Object.assign/Reflect.set/Reflect.apply` 等 runtime mutator。因此本任务改为源引用禁用策略。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J18_RuntimeMutator源引用禁用门禁收口证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、架构决策

### 4.1 禁用 Runtime Mutator 源引用

在 style-profit surface 内，以下源引用一律禁止：

- `Object.defineProperty`
- `Object.defineProperties`
- `Object.assign`
- `Reflect.set`
- `Reflect.apply`

等价来源也一律禁止：

- `globalThis.Object.defineProperty`
- `window.Object.defineProperty`
- `globalThis.Object.assign`
- `window.Object.assign`
- `globalThis.Reflect.set`
- `window.Reflect.set`
- `globalThis.Reflect.apply`
- `window.Reflect.apply`
- 字符串字面量括号访问，例如 `Object['assign']`
- 命名空间别名、解构别名、赋值式解构别名、bind/call/apply、Reflect.apply、中转容器等已识别路径

要求：不再只在“最终调用发生”时拦截。只要这些源引用被放入变量、函数返回、数组、对象、条件表达式、IIFE、包装器、容器或任何中转结构，在 style-profit surface 内都必须 fail closed。

### 4.2 允许的替代写法

如果工程师确实需要对象合并，必须使用只读、显式、可审计的写法：

```ts
const next = { ...base, status: 'readonly' }
```

禁止用 `Object.assign` 代替对象 spread。若对象 spread 目标包含 action key 或来自不可解析 source，仍应按既有 action 门禁规则处理。

### 4.3 函数返回与 IIFE 必须 fail closed

以下场景必须拦截：

```ts
function getMutator() { return Object.defineProperty }
getMutator()(item, 'onClick', { value: openHelp })

const getMutator = () => Object.assign
getMutator()(item, { onClick: openHelp })

;(() => Object.defineProperty)()(item, 'onClick', { value: openHelp })
```

要求：

1. 函数、箭头函数、IIFE 返回 mutator 源引用时 fail closed。
2. 返回 mutator 源引用后即使未立即调用，也必须 fail closed。
3. 返回值被放入变量、容器、条件表达式时也必须 fail closed。

### 4.4 内联字面量容器必须 fail closed

以下场景必须拦截：

```ts
;[Object.defineProperty][0](item, 'onClick', { value: openHelp })
;({ dp: Object.defineProperty }).dp(item, 'onClick', { value: openHelp })
```

要求：

1. 数组字面量中出现 mutator 源引用即 fail closed。
2. 对象字面量中出现 mutator 源引用即 fail closed。
3. 不要求等到容器被调用才拦截。

### 4.5 嵌套、包装与条件容器必须 fail closed

以下场景必须拦截：

```ts
const nested = [[Object.defineProperty]]
nested[0][0](item, 'onClick', { value: openHelp })

const frozen = Object.freeze({ dp: Object.defineProperty })
frozen.dp(item, 'onClick', { value: openHelp })

const mutators = condition ? [Object.defineProperty] : [Object.defineProperty]
mutators[0](item, 'onClick', { value: openHelp })
```

要求：

1. 嵌套数组、嵌套对象中出现 mutator 源引用即 fail closed。
2. `Object.freeze/Object.seal/Object.create/Object.fromEntries` 等包装结构中包含 mutator 源引用时 fail closed。
3. 条件表达式任一分支包含 mutator 源引用时 fail closed。
4. 包装器无法静态还原时，在 style-profit surface 内 fail closed。

### 4.6 Source Surface 范围

门禁至少覆盖以下路径：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/**`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/api/**`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/router/**`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/stores/**`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/components/**`

判断为 style-profit surface 的文件中，runtime mutator 源引用必须按本任务规则 fail closed。

## 五、必须新增反向测试

至少新增以下反向测试，每条都必须明确断言门禁失败：

1. `function getMutator() { return Object.defineProperty }; getMutator()(...)`
2. `const getMutator = () => Object.assign; getMutator()(...)`
3. `;(() => Object.defineProperty)()(...)`
4. `;[Object.defineProperty][0](...)`
5. `;({ dp: Object.defineProperty }).dp(...)`
6. `const nested = [[Object.defineProperty]]; nested[0][0](...)`
7. `const frozen = Object.freeze({ dp: Object.defineProperty }); frozen.dp(...)`
8. `const sealed = Object.seal({ assign: Object.assign }); sealed.assign(...)`
9. `const mutators = condition ? [Object.defineProperty] : [Object.defineProperty]; mutators[0](...)`
10. `const mutators = condition ? { dp: Object.defineProperty } : { dp: Object.defineProperty }; mutators.dp(...)`
11. `const getMutator = () => globalThis.Object.assign; getMutator()(...)`
12. `const getMutator = () => window.Reflect.set; getMutator()(...)`
13. `const holder = { make: () => Object.defineProperty }; holder.make()(...)`
14. `const holder = [() => Object.assign]; holder[0]()(...)`
15. 源引用存在但未调用也失败：`const dangerous = Object.defineProperty`
16. 容器存在但未调用也失败：`const dangerous = { dp: Object.defineProperty }`

## 六、必须保留成功用例

以下场景不得误杀：

1. 只读对象 spread：`const next = { ...base, status: 'readonly' }`
2. 普通非 mutator 工具函数：`const format = formatAmount`
3. 纯说明文案：`const title = '利润计算说明'`
4. 非 action 字段写入：`item.tooltip = '说明'`
5. 纯读取动态 key：`const fn = item['onClick']`，前提是不形成调用入口、不写入、不放入容器作为 mutator source

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J17 的既有测试。尤其必须保留：

- 第 131 份审计 6 个绕过样例。
- 第 132 份审计 5 个绕过样例。
- 第 133 份审计 7 个绕过样例。
- 第 134 份审计 6 个绕过样例。
- 第 135 份审计 4 个绕过样例。
- 中文语义、只读说明、多行上下文、AST computed key、runtime mutator 全部既有反向测试。

## 八、验证命令

工程师必须执行并在证据文件中贴摘要：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high

cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 九、验收标准

- 第 136 份审计列出的新增绕过全部被拦截。
- runtime mutator 源引用在 style-profit surface 内禁用。
- 函数返回、IIFE、内联字面量容器、嵌套容器、包装容器、条件容器全部 fail closed。
- TASK-005J13/J14/J15/J16/J17 已关闭的绕过不回潮。
- 对象 spread 成功用例不被误杀。
- 普通说明文案不被误杀。
- 非 action 字段写入不被误杀。
- `npm run verify` 通过。
- 后端 style-profit API 定向回归通过。
- 未修改后端、workflow、`02_源码`、TASK-006 或运行生成物。

## 十、禁止事项

- 禁止开放 `POST /api/reports/style-profit/snapshots` 前端入口。
- 禁止新增 `createStyleProfitSnapshot`、`snapshot_create`、`idempotency_key` 等创建入口调用。
- 禁止引入新的第三方 parser 依赖。
- 禁止通过扩大白名单、跳过测试、缩小扫描范围来让门禁变绿。
- 禁止把 TASK-006 解锁或写入 TASK-006 工程实现内容。
- 禁止继续以“只补一个调用语法”为主要实现策略，必须采用源引用禁用或等价强收口策略。

## 十一、交付物

- 更新后的 `check-style-profit-contracts.mjs`
- 更新后的 `test-style-profit-contracts.mjs`
- `TASK-005J18_RuntimeMutator源引用禁用门禁收口证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
