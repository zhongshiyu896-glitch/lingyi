# TASK-005J22 Timer call/apply 等价调用门禁整改工程任务单

- 任务编号：TASK-005J22
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / timer 参数归一
- 前置审计：审计意见书第 140 份
- 更新时间：2026-04-15 00:56 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 对 `setTimeout/setInterval` 等价调用的剩余绕过，把 timer codegen 检测接入统一 call descriptor / 参数归一逻辑。无论通过直接调用、`.call`、`.apply`、`Reflect.apply`、命名空间或别名调用，只要实际 timer callback 参数为字符串或无法证明非字符串，就必须 fail closed。

## 二、背景问题

TASK-005J21 已封住第 139 份审计指出的直接字符串定时器与 constructor 链主路径，但审计官在第 140 份审计中复现 timer `.call/.apply` 等价调用仍可绕过：

```ts
setTimeout.call(window, "Object.assign(item, { onClick: openHelp })")
setTimeout.apply(window, ["Object.assign(item, { onClick: openHelp })", 0])
window.setTimeout.call(window, "Object.defineProperty(item, 'onClick', { value: openHelp })")
globalThis.setInterval.apply(globalThis, ["Reflect.set(item, 'onClick', openHelp)", 0])
```

这些路径仍是字符串 timer 执行代码，必须等价拦截。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J22_TimerCallApply等价调用门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 timer `.call` 必须识别

必须识别以下形式，并剥离 thisArg 后按真实 timer 参数解析：

```ts
setTimeout.call(window, "Object.assign(item, { onClick: openHelp })")
setInterval.call(globalThis, "Reflect.set(item, 'onClick', openHelp)")
window.setTimeout.call(window, "Object.defineProperty(item, 'onClick', { value: openHelp })")
globalThis.setInterval.call(globalThis, "Reflect.set(item, 'onClick', openHelp)")
```

要求：

1. `.call()` 第一个参数是 thisArg，不是 timer callback。
2. `.call()` 第二个参数才是 timer callback，若为字符串、模板字面量、字符串拼接或无法证明非字符串，必须 fail closed。
3. 支持 `setTimeout['call'](...)`、`window.setTimeout['call'](...)`。
4. 支持 timer 直接别名、解构别名、命名空间别名后的 `.call()`。

### 4.2 timer `.apply` 必须识别

必须识别以下形式，并按 apply 第二参数数组映射真实 timer 参数：

```ts
setTimeout.apply(window, ["Object.assign(item, { onClick: openHelp })", 0])
setInterval.apply(globalThis, ["Reflect.set(item, 'onClick', openHelp)", 0])
window.setTimeout.apply(window, ["Object.defineProperty(item, 'onClick', { value: openHelp })", 0])
globalThis.setInterval.apply(globalThis, ["Reflect.set(item, 'onClick', openHelp)", 0])
```

要求：

1. `.apply()` 第二参数为数组字面量时，第一个数组元素是 timer callback。
2. 数组第一个元素为字符串、模板字面量、字符串拼接时必须 fail closed。
3. `.apply()` 第二参数不是数组字面量、含 spread、或无法静态还原时，在 style-profit surface 内必须 fail closed。
4. 支持 `setTimeout['apply'](...)`、`window.setTimeout['apply'](...)`。

### 4.3 Reflect.apply timer 必须识别

必须识别以下形式：

```ts
Reflect.apply(setTimeout, window, ["Object.assign(item, { onClick: openHelp })", 0])
Reflect.apply(window.setTimeout, window, ["Object.defineProperty(item, 'onClick', { value: openHelp })", 0])
Reflect.apply(globalThis.setInterval, globalThis, ["Reflect.set(item, 'onClick', openHelp)", 0])
```

要求：

1. `Reflect.apply` 第一个参数解析为 timer API 时，第三个参数数组第一个元素是 timer callback。
2. 第三个参数不是数组字面量、含 spread、或无法静态还原时，在 style-profit surface 内必须 fail closed。
3. 支持 `Reflect['apply'](...)` 及 Reflect 命名空间别名。

### 4.4 timer 别名与动态成员必须保留

TASK-005J21 已要求识别以下路径，本任务不得回退：

```ts
const delay = setTimeout
delay("Object.assign(item, { onClick: openHelp })")
const { setTimeout: delay } = window
delay("Object.assign(item, { onClick: openHelp })")
window['set' + 'Timeout']("Object.assign(item, { onClick: openHelp })")
```

本任务必须保证这些路径和新增 `.call/.apply/Reflect.apply` 路径共用同一 timer descriptor 归一逻辑，避免后续继续出现等价调用绕过。

### 4.5 成功用例必须保留

以下场景不得误杀：

```ts
setTimeout.call(window, () => refresh(), 100)
setTimeout.apply(window, [() => refresh(), 100])
Reflect.apply(setTimeout, window, [refresh, 100])
setInterval.call(window, refresh, 1000)
```

要求：函数回调和已知函数引用 timer 可以通过；只有字符串或无法证明非字符串的 callback fail closed。

## 五、必须新增反向测试

至少新增以下反向测试，每条都必须明确断言门禁失败：

1. `setTimeout.call(window, "Object.assign(item, { onClick: openHelp })")`
2. `setInterval.call(globalThis, "Reflect.set(item, 'onClick', openHelp)")`
3. `window.setTimeout.call(window, "Object.defineProperty(item, 'onClick', { value: openHelp })")`
4. `globalThis.setInterval.call(globalThis, "Reflect.set(item, 'onClick', openHelp)")`
5. `setTimeout['call'](window, "Object.assign(item, { onClick: openHelp })")`
6. `setTimeout.apply(window, ["Object.assign(item, { onClick: openHelp })", 0])`
7. `setInterval.apply(globalThis, ["Reflect.set(item, 'onClick', openHelp)", 0])`
8. `window.setTimeout.apply(window, ["Object.defineProperty(item, 'onClick', { value: openHelp })", 0])`
9. `globalThis.setInterval.apply(globalThis, ["Reflect.set(item, 'onClick', openHelp)", 0])`
10. `setTimeout['apply'](window, ["Object.assign(item, { onClick: openHelp })", 0])`
11. `setTimeout.apply(window, args)` 中 `args` 无法静态还原时 fail closed
12. `setTimeout.apply(window, [code, 0])` 中 `code` 无法证明非字符串时 fail closed
13. `Reflect.apply(setTimeout, window, ["Object.assign(item, { onClick: openHelp })", 0])`
14. `Reflect.apply(window.setTimeout, window, ["Object.defineProperty(item, 'onClick', { value: openHelp })", 0])`
15. `Reflect.apply(globalThis.setInterval, globalThis, ["Reflect.set(item, 'onClick', openHelp)", 0])`
16. `Reflect['apply'](setTimeout, window, ["Object.assign(item, { onClick: openHelp })", 0])`
17. `const delay = setTimeout; delay.call(window, "Object.assign(item, { onClick: openHelp })")`
18. `const delay = setTimeout; delay.apply(window, ["Object.assign(item, { onClick: openHelp })", 0])`

## 六、必须保留成功用例

至少新增或保留以下成功 fixture：

1. `setTimeout.call(window, () => refresh(), 100)`
2. `setTimeout.apply(window, [() => refresh(), 100])`
3. `Reflect.apply(setTimeout, window, [refresh, 100])`
4. `setInterval.call(window, refresh, 1000)`
5. `setInterval.apply(window, [refresh, 1000])`

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J21 的既有测试。尤其必须保留：

- 第 131 份到第 139 份所有审计绕过样例。
- 字符串 setTimeout/setInterval 直接调用测试。
- timer 别名、间接调用、动态成员访问测试。
- eval/Function/new Function/globalThis/window Function/eval 测试。
- constructor 链测试。
- runtime mutator 源引用禁用成功/失败 fixture。

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

- 第 140 份审计列出的 timer `.call/.apply` 绕过全部被拦截。
- `setTimeout/setInterval.call` 字符串 callback 全部 fail closed。
- `setTimeout/setInterval.apply` 字符串 callback 全部 fail closed。
- `Reflect.apply(timer, ...)` 字符串 callback 全部 fail closed。
- apply 参数无法静态还原时 fail closed。
- timer 函数回调和已知函数引用成功用例不被误杀。
- TASK-005J13-J21 已关闭的绕过不回潮。
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
- `TASK-005J22_TimerCallApply等价调用门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
