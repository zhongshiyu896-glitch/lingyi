# TASK-005J33 循环与参数解构 Alias 门禁整改工程任务单

- 任务编号：TASK-005J33
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / loop and parameter destructuring alias tracking
- 前置审计：审计意见书第 151 份
- 更新时间：2026-04-15 11:16 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 中 `for...of` 绑定、函数参数解构、回调参数解构未进入数组状态图导致的绕过。必须将 binding pattern 解析从变量声明/赋值扩展到循环绑定、函数参数、箭头函数参数、回调参数和高阶函数回调，使这些位置产生的 alias 与原数组共享同一 `array_id`；无法静态还原来源时必须 fail closed。

本任务只修前端只读契约门禁，不开放款式利润快照创建入口，不进入 TASK-006。

## 二、背景问题

TASK-005J32 已修复变量声明/赋值式解构 alias，例如 `const [alias] = [args]`、`const { value: alias } = { value: args }`。但审计官第 151 份审计复现 `for...of`、函数参数解构、回调参数解构仍可绕过：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]

for (const alias of [args]) {
  alias[0] = 'data:text/javascript,postMessage(1)'
}

new Worker(...args)
```

函数参数解构绕过：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]
const tuple = [args]

poison(tuple)
new Worker(...args)

function poison([alias]) {
  alias[0] = 'data:text/javascript,postMessage(1)'
}
```

回调参数解构绕过：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]

[[args]].forEach(([alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
})

new Worker(...args)
```

当前 BindingPattern 处理主要覆盖变量声明/赋值式解构，未覆盖 loop binding、function parameter binding 和 callback parameter binding。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J33_循环与参数解构Alias门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 BindingPattern 解析必须抽成统一入口

必须将解构 alias 解析抽成统一函数或等价机制，覆盖：

1. VariableDeclaration binding
2. AssignmentPattern binding
3. ForOfStatement initializer binding
4. FunctionDeclaration parameter binding
5. FunctionExpression parameter binding
6. ArrowFunction parameter binding
7. callback parameter binding
8. nested binding patterns

要求：

1. 同一套 `ArrayBindingPattern / ObjectBindingPattern` 解析逻辑必须可被以上场景复用。
2. 解析结果必须能绑定到数组状态图的 `array_id`。
3. 来源无法静态还原时，必须标记 alias unknown/escaped，并在后续 Worker/unknown constructor spread 使用时 fail closed。
4. 不允许只在变量声明场景补分支。

### 4.2 for...of 绑定必须进入数组状态图

必须拦截以下形式：

```ts
for (const alias of [args]) {
  alias[0] = 'data:text/javascript,postMessage(1)'
}
new Worker(...args)

for (const [alias] of [[args]]) {
  alias[0] = 'data:text/javascript,postMessage(1)'
}
new Worker(...args)
```

要求：

1. `for (const alias of [args])` 必须让 alias 指向 args 的同一 `array_id`。
2. `for (const [alias] of [[args]])` 必须追踪嵌套解构。
3. for...of 的 iterable 无法静态还原时，循环体内 alias 必须 unknown/escaped。
4. 循环体内 alias 写入、mutating method、逃逸必须污染原数组。
5. for...of 执行在 Worker spread 前时，污染必须影响后续 Worker spread。

### 4.3 函数参数解构必须进入数组状态图

必须拦截以下形式：

```ts
const tuple = [args]
poison(tuple)
new Worker(...args)

function poison([alias]) {
  alias[0] = 'data:text/javascript,postMessage(1)'
}
```

要求：

1. 调用 `poison(tuple)` 时，必须把实参 `tuple` 与形参 `[alias]` 绑定。
2. 如果 `tuple` 可静态解析为 `[args]`，alias 必须指向 args 的同一 `array_id`。
3. 函数参数解构内的 alias 写入必须进入 function side-effect summary，并按调用点污染原数组。
4. 实参无法静态还原时，形参 alias 必须 unknown，后续 Worker spread fail closed。
5. 多参数、默认参数、rest 参数和 nested binding pattern 必须保守处理。

### 4.4 箭头函数与函数表达式参数解构必须进入数组状态图

必须拦截以下形式：

```ts
const poison = ([alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
}
poison([args])
new Worker(...args)

const poison = function ([alias]) {
  alias[0] = 'data:text/javascript,postMessage(1)'
}
poison([args])
new Worker(...args)
```

要求：

1. 箭头函数参数解构必须进入 side-effect summary。
2. 函数表达式参数解构必须进入 side-effect summary。
3. 调用点实参与形参必须按调用点绑定。
4. 函数别名、call/apply/bind 调用也必须应用参数解构绑定或 fail closed。

### 4.5 回调参数解构必须进入数组状态图

必须拦截以下形式：

```ts
[[args]].forEach(([alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
})
new Worker(...args)
```

要求：

1. 对静态数组 `.forEach/.map/.some/.every/.filter/.find` 的回调参数解构，必须尝试绑定元素来源。
2. `[[args]].forEach(([alias]) => ...)` 中 alias 必须指向 args 的同一 `array_id`。
3. callback 内 alias 写入必须污染原数组。
4. 回调来源无法静态还原时，必须 fail closed 或将相关 tracked arrays 标记 unknown。
5. 不得因为是回调函数就跳过 side-effect summary。

### 4.6 ObjectBindingPattern 参数与循环绑定必须同样支持

必须处理以下形式：

```ts
for (const { value: alias } of [{ value: args }]) {
  alias[0] = 'data:text/javascript,postMessage(1)'
}

function poison({ value: alias }) {
  alias[0] = 'data:text/javascript,postMessage(1)'
}
poison({ value: args })
```

要求：

1. 对象解构参数、对象解构 loop binding 必须进入数组状态图。
2. 对象属性重命名、嵌套对象解构必须支持。
3. computed/rest/default 无法静态证明安全时必须 fail closed。

### 4.7 Reflect.construct 参数数组同样适用

必须同步处理：

```ts
for (const alias of [args]) {
  alias[0] = 'data:text/javascript,postMessage(1)'
}
Reflect.construct(Worker, args)
```

要求：

1. for...of / 参数解构 / 回调解构污染原数组后，Reflect.construct 必须 fail closed。
2. NewExpression spread 与 Reflect.construct 参数数组必须共用同一数组状态图。

## 五、必须新增反向测试

至少新增以下反向测试，每条必须断言门禁失败：

1. `for (const alias of [args]) { alias[0] = 'data:text/javascript,postMessage(1)' } new Worker(...args)`
2. `for (const [alias] of [[args]]) { alias[0] = 'data:text/javascript,postMessage(1)' } new Worker(...args)`
3. `for (const { value: alias } of [{ value: args }]) { alias[0] = 'data:text/javascript,postMessage(1)' } new Worker(...args)`
4. `for (const alias of iterable) { alias[0] = 'data:text/javascript,postMessage(1)' } new Worker(...args)` 必须 fail closed when iterable cannot be proven safe
5. `function poison([alias]) { alias[0] = 'data:text/javascript,postMessage(1)' } poison([args]); new Worker(...args)`
6. `const tuple = [args]; function poison([alias]) { alias[0] = 'data:text/javascript,postMessage(1)' } poison(tuple); new Worker(...args)`
7. `function poison({ value: alias }) { alias[0] = 'data:text/javascript,postMessage(1)' } poison({ value: args }); new Worker(...args)`
8. `const poison = ([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)' }; poison([args]); new Worker(...args)`
9. `const poison = function ([alias]) { alias[0] = 'data:text/javascript,postMessage(1)' }; poison([args]); new Worker(...args)`
10. `function poison([alias = args]) { alias[0] = 'data:text/javascript,postMessage(1)' } poison([]); new Worker(...args)` 必须 fail closed or precise block
11. `function poison(...rest) { rest[0][0] = 'data:text/javascript,postMessage(1)' } poison(args); new Worker(...args)` 必须 fail closed or precise block
12. `[[args]].forEach(([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)' }); new Worker(...args)`
13. `[{ value: args }].forEach(({ value: alias }) => { alias[0] = 'data:text/javascript,postMessage(1)' }); new Worker(...args)`
14. `collection.forEach(([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)' }); new Worker(...args)` 必须 fail closed when collection cannot be proven safe
15. `for (const alias of [args]) { alias[0] = 'data:text/javascript,postMessage(1)' } Reflect.construct(Worker, args)`
16. `function poison([alias]) { alias[0] = '/runtime/style-profit-worker.js' } poison([args]); new unknownCtor(...args)`

## 六、必须保留成功用例

至少保留或新增以下成功 fixture：

1. `for (const alias of [args]) { noop(alias) } new Worker(...args)`，仅当 noop 明确安全且 alias 未写入/逃逸时允许
2. `function noop([alias]) {} noop([args]); new Worker(...args)`，仅当 noop 明确无副作用时允许
3. `[[args]].forEach(([alias]) => { readonly(alias) }); new Worker(...args)`，仅当 readonly 明确安全时允许
4. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new Worker(...args)`
5. `const dateArgs = ['2026-04-15']; function noop([alias]){}; noop([dateArgs]); new Date(...dateArgs)`
6. 普通非数组参数解构不被误杀。

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J32 的既有测试。尤其必须保留：

- 第 131 份到第 151 份所有审计绕过样例。
- 解构 alias 数组状态跟踪测试。
- 函数调用副作用数组污染测试。
- Spread 数组状态跟踪测试。
- NewExpression spread 参数归一化测试。
- unknown constructor URL 严格门禁测试。
- Worker.bind、Reflect.construct、函数返回 Worker、IIFE 返回 Worker 测试。
- Worker alias、namespace alias、conditional alias、container alias 测试。
- URL.createObjectURL call/apply/别名测试。
- Blob URL 传播到 import/Worker/script 测试。
- dynamic import、Blob URL module loading、timer、constructor、eval/Function 全部既有测试。

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

- 第 151 份审计列出的 for...of、函数参数解构、回调参数解构 alias 绕过全部被拦截。
- BindingPattern 解析不再只覆盖变量声明/赋值式解构。
- for...of binding、函数参数、箭头函数参数、回调参数全部进入数组状态图。
- 解构 alias 与原数组共享同一 `array_id` 或在无法还原时 fail closed。
- 函数 side-effect summary 能识别参数解构 alias 污染，并按调用点生效。
- Reflect.construct 参数数组同样受这些解构 alias 状态影响。
- clean 只读循环/参数/回调成功用例不被误杀。
- TASK-005J13-J32 已关闭的绕过不回潮。
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
- `TASK-005J33_循环与参数解构Alias门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
