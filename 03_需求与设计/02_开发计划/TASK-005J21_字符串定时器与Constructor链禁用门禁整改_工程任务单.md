# TASK-005J21 字符串定时器与 Constructor 链禁用门禁整改工程任务单

- 任务编号：TASK-005J21
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / 代码生成派生入口禁用
- 前置审计：审计意见书第 139 份
- 更新时间：2026-04-15 00:30 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 对运行时代码生成派生入口的剩余绕过，禁用 style-profit surface 内的字符串定时器与 `constructor` 派生 Function 链。任何可通过 `setTimeout/setInterval` 字符串参数或 `.constructor/.constructor.constructor` 生成并执行受禁 mutator 的路径，都必须 fail closed。

## 二、背景问题

TASK-005J20 已关闭第 138 份审计中的直接 `eval/Function/new Function/globalThis.Function` 等运行时代码生成入口，但审计官在第 139 份审计中复现以下绕过：

```ts
setTimeout("Object.assign(item, { onClick: openHelp })")
setInterval("Reflect.set(item, 'onClick', openHelp)")
window.setTimeout("Object.defineProperty(item, 'onClick', { value: openHelp })")

;(() => {}).constructor('return Object.assign')()(item, { onClick: openHelp })
;[]['filter']['constructor']('return Reflect.set')()(item, 'onClick', openHelp)
;({}).constructor.constructor('return Object.defineProperty')()(item, 'onClick', { value: openHelp })
```

这些路径本质仍是运行时代码生成或 Function 派生入口，必须作为 P1 阻断修复。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J21_字符串定时器与Constructor链禁用门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 禁用字符串定时器

必须识别并拦截以下形式：

```ts
setTimeout("Object.assign(item, { onClick: openHelp })")
setInterval("Reflect.set(item, 'onClick', openHelp)")
window.setTimeout("Object.defineProperty(item, 'onClick', { value: openHelp })")
globalThis.setInterval("Object.assign(item, { onClick: openHelp })")
```

要求：

1. `setTimeout` / `setInterval` 第一参数为字符串字面量时必须 fail closed。
2. 第一参数为模板字面量时必须 fail closed。
3. 第一参数为字符串拼接表达式时必须 fail closed。
4. 第一参数为变量且无法静态证明非字符串时，在 style-profit surface 内必须 fail closed。
5. 不解析字符串内容；只要 timer 以字符串执行代码，即 fail closed。
6. `window/globalThis` 命名空间、别名、动态成员访问都必须等价处理。

### 4.2 禁用 timer 别名与间接调用

必须识别并拦截以下形式：

```ts
const delay = setTimeout
delay("Object.assign(item, { onClick: openHelp })")

const { setTimeout: delay } = window
delay("Object.defineProperty(item, 'onClick', { value: openHelp })")

;(0, setTimeout)("Reflect.set(item, 'onClick', openHelp)")
window['set' + 'Timeout']("Object.assign(item, { onClick: openHelp })")
```

要求：

1. 直接别名、解构别名、赋值式解构别名必须识别。
2. 间接调用 `(0, setTimeout)(...)` 必须识别。
3. 动态成员名必须按 TASK-005J19 的字符串折叠规则处理。
4. 若 timer callee 可疑且第一参数可能是字符串，必须 fail closed。

### 4.3 禁用 constructor 派生 Function 链

必须识别并拦截以下形式：

```ts
;(() => {}).constructor('return Object.assign')()(item, { onClick: openHelp })
;[]['filter']['constructor']('return Reflect.set')()(item, 'onClick', openHelp)
;({}).constructor.constructor('return Object.defineProperty')()(item, 'onClick', { value: openHelp })
```

要求：

1. 任意表达式上的 `.constructor(...)` 调用，在 style-profit surface 内必须 fail closed。
2. 任意表达式上的 `['constructor'](...)` 调用必须 fail closed。
3. `.constructor.constructor(...)` 与 `['constructor']['constructor'](...)` 必须 fail closed。
4. 构造器链中出现字符串拼接、模板字面量、动态成员名时，必须 fail closed。
5. 不解析 constructor 参数字符串；调用入口出现即 fail closed。

### 4.4 禁用 constructor 源引用中转

以下场景即使未立即调用，也必须 fail closed：

```ts
const Ctor = (() => {}).constructor
const Ctor = []['filter']['constructor']
const holder = { make: ({}).constructor.constructor }
const holder = [Function.prototype.constructor]
const make = condition ? ({}).constructor.constructor : Function
```

要求：

1. `.constructor` 源引用进入变量、数组、对象、函数返回、IIFE、条件表达式时 fail closed。
2. `Function.prototype.constructor` 必须等价视为 Function 构造器源引用。
3. 包装容器，如 `Object.freeze({ make: ({}).constructor.constructor })`，必须 fail closed。
4. 无法静态确认 constructor 链是否安全时，在 style-profit surface 内 fail closed。

### 4.5 必须保留安全用例

以下场景不得误杀：

1. timer 使用函数回调：`setTimeout(() => refresh(), 100)`。
2. timer 使用已知函数引用：`setInterval(refresh, 1000)`。
3. 普通字段名包含 constructor 但不是属性访问：`record['constructor_name']`。
4. 普通说明文案：`const text = 'constructor disabled'`。
5. 普通非代码生成构造器：`new Date()`。

## 五、必须新增反向测试

至少新增以下反向测试，每条都必须明确断言门禁失败：

1. `setTimeout("Object.assign(item, { onClick: openHelp })")`
2. `setInterval("Reflect.set(item, 'onClick', openHelp)")`
3. `window.setTimeout("Object.defineProperty(item, 'onClick', { value: openHelp })")`
4. `globalThis.setInterval("Object.assign(item, { onClick: openHelp })")`
5. `` setTimeout(`Object.assign(item, { onClick: openHelp })`) ``
6. `setTimeout('Object.' + 'assign(item, { onClick: openHelp })')`
7. `const code = "Object.assign(item, { onClick: openHelp })"; setTimeout(code)` 必须 fail closed
8. `const delay = setTimeout; delay("Object.assign(item, { onClick: openHelp })")`
9. `const { setTimeout: delay } = window; delay("Object.defineProperty(item, 'onClick', { value: openHelp })")`
10. `;(0, setTimeout)("Reflect.set(item, 'onClick', openHelp)")`
11. `window['set' + 'Timeout']("Object.assign(item, { onClick: openHelp })")`
12. `;(() => {}).constructor('return Object.assign')()(item, { onClick: openHelp })`
13. `;[]['filter']['constructor']('return Reflect.set')()(item, 'onClick', openHelp)`
14. `;({}).constructor.constructor('return Object.defineProperty')()(item, 'onClick', { value: openHelp })`
15. `;({})['constructor']['constructor']('return Object.assign')()(item, { onClick: openHelp })`
16. `const Ctor = (() => {}).constructor` 源引用未调用也失败
17. `const holder = { make: ({}).constructor.constructor }` 容器未调用也失败
18. `const holder = [Function.prototype.constructor]` 容器未调用也失败
19. `const make = condition ? ({}).constructor.constructor : Function` 条件源引用失败
20. `Object.freeze({ make: ({}).constructor.constructor })` 包装容器失败

## 六、必须保留成功用例

至少新增或保留以下成功 fixture：

1. `setTimeout(() => refresh(), 100)`
2. `setInterval(refresh, 1000)`
3. `record['constructor_name']`
4. `const text = 'constructor disabled'`
5. `new Date()`
6. `const next = { ...base, status: 'readonly' }`

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J20 的既有测试。尤其必须保留：

- 第 131 份到第 138 份所有审计绕过样例。
- eval/Function/new Function/globalThis/window Function/eval 测试。
- runtime mutator 源引用禁用成功/失败 fixture。
- 动态成员名、Reflect.get、optional chain 测试。
- 中文语义、只读说明、多行上下文、AST computed key 全部既有反向测试。

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

- 第 139 份审计列出的字符串 timer 与 constructor 链绕过全部被拦截。
- 字符串 setTimeout/setInterval 全部 fail closed。
- timer 别名、间接调用、动态成员访问全部 fail closed。
- `.constructor(...)`、`['constructor'](...)`、`.constructor.constructor(...)` 全部 fail closed。
- constructor 源引用进入变量、容器、函数返回、条件表达式，即使未调用也 fail closed。
- TASK-005J13-J20 已关闭的绕过不回潮。
- 成功用例不被误杀。
- `npm run verify` 通过。
- 后端 style-profit API 定向回归通过。
- 未修改后端、workflow、`02_源码`、TASK-006 或运行生成物。

## 十、禁止事项

- 禁止开放 `POST /api/reports/style-profit/snapshots` 前端入口。
- 禁止新增 `createStyleProfitSnapshot`、`snapshot_create`、`idempotency_key` 等创建入口调用。
- 禁止引入新的第三方 parser 依赖。
- 禁止通过扩大白名单、跳过测试、缩小扫描范围来让门禁变绿。
- 禁止把 TASK-006 解锁或写入 TASK-006 工程实现内容。

## 十一、交付物

- 更新后的 `check-style-profit-contracts.mjs`
- 更新后的 `test-style-profit-contracts.mjs`
- `TASK-005J21_字符串定时器与Constructor链禁用门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
