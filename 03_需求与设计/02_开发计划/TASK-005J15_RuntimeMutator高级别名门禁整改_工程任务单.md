# TASK-005J15 Runtime Mutator 高级别名门禁整改工程任务单

- 任务编号：TASK-005J15
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改
- 前置审计：审计意见书第 133 份
- 更新时间：2026-04-14 22:12 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 对运行时 mutator API 的高级别名绕过，覆盖赋值式解构、`bind/call/apply`、`globalThis/window` 命名空间，确保 style-profit surface 内任何等价调用 `Object.defineProperty/Object.defineProperties/Object.assign/Reflect.set` 的路径都 fail closed。

## 二、背景问题

TASK-005J14 已关闭第 132 份审计提出的声明式解构别名与命名空间别名绕过，但审计官在第 133 份审计中复现以下绕过：

```ts
let defineProperty
;({ defineProperty } = Object)
defineProperty(item, 'onClick', { value: openHelp })

const defineProperty = Object.defineProperty.bind(Object)
defineProperty(item, 'onClick', { value: openHelp })

Object.defineProperty.call(Object, item, 'onClick', { value: openHelp })
Object.defineProperty.apply(Object, [item, 'onClick', { value: openHelp }])

const Obj = globalThis.Object
Obj.defineProperty(item, 'onClick', { value: openHelp })
```

这些路径仍会在运行时注入 action key，必须按原 API 等价拦截。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J15_RuntimeMutator高级别名门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 赋值式解构必须识别

必须识别以下形式：

```ts
let defineProperty
;({ defineProperty } = Object)
defineProperty(item, 'onClick', { value: openHelp })

let assign
;({ assign } = Object)
assign(item, { onClick: openHelp })

let set
;({ set } = Reflect)
set(item, 'onClick', openHelp)
```

要求：

1. 识别 `BinaryExpression` 中对象解构赋值。
2. 识别解构重命名：`({ defineProperty: dp } = Object)`。
3. 识别 `Object` 与 `Reflect` 两类来源。
4. 赋值式解构别名必须映射回源 API。

### 4.2 bind 别名必须识别

必须识别以下形式：

```ts
const defineProperty = Object.defineProperty.bind(Object)
const assign = Object.assign.bind(Object)
const set = Reflect.set.bind(Reflect)
```

调用别名时，必须按源 API 等价拦截。

### 4.3 call/apply 必须识别

必须识别以下形式：

```ts
Object.defineProperty.call(Object, item, 'onClick', { value: openHelp })
Object.defineProperty.apply(Object, [item, 'onClick', { value: openHelp }])
Object.assign.call(Object, item, { onClick: openHelp })
Object.assign.apply(Object, [item, { onClick: openHelp }])
Reflect.set.call(Reflect, item, 'onClick', openHelp)
Reflect.set.apply(Reflect, [item, 'onClick', openHelp])
```

要求：

1. `.call()` 参数需剥离第一个 thisArg 后按源 API 参数位置解析。
2. `.apply()` 第二参数为数组字面量时，按数组元素映射源 API 参数位置解析。
3. `.apply()` 第二参数非数组字面量或无法解析时，在 style-profit surface 内 fail closed。
4. 支持 bracket 形式：`Object.defineProperty['call'](...)`、`Object.assign['apply'](...)`。

### 4.4 globalThis/window 命名空间必须识别

必须识别以下来源：

```ts
globalThis.Object
window.Object
globalThis.Reflect
window.Reflect
```

并拦截：

```ts
const Obj = globalThis.Object
Obj.defineProperty(item, 'onClick', { value: openHelp })

const R = window.Reflect
R.set(item, 'onClick', openHelp)

globalThis.Object.assign(item, { onClick: openHelp })
window.Reflect.set(item, 'onClick', openHelp)
```

### 4.5 Fail Closed 口径

1. 来源可疑、参数无法还原、别名被重写或作用域冲突时，在 style-profit surface 内 fail closed。
2. 不得通过 `查看详情/查询/返回/利润计算说明` 等只读文案豁免 mutator 调用。
3. 不得缩小 TASK-005J13/J14 已关闭的绕过范围。
4. 不新增第三方 parser 依赖。

## 五、必须新增反向测试

至少新增以下反向测试，每条都必须明确断言门禁失败：

1. `let defineProperty; ({ defineProperty } = Object); defineProperty(item, 'onClick', ...)`
2. `let dp; ({ defineProperty: dp } = Object); dp(item, 'onClick', ...)`
3. `let assign; ({ assign } = Object); assign(item, { onClick: openHelp })`
4. `let set; ({ set } = Reflect); set(item, 'onClick', openHelp)`
5. `const defineProperty = Object.defineProperty.bind(Object); defineProperty(item, 'onClick', ...)`
6. `const assign = Object.assign.bind(Object); assign(item, { onClick: openHelp })`
7. `const set = Reflect.set.bind(Reflect); set(item, 'onClick', openHelp)`
8. `Object.defineProperty.call(Object, item, 'onClick', { value: openHelp })`
9. `Object.defineProperty.apply(Object, [item, 'onClick', { value: openHelp }])`
10. `Object.assign.call(Object, item, { onClick: openHelp })`
11. `Object.assign.apply(Object, [item, { onClick: openHelp }])`
12. `Reflect.set.call(Reflect, item, 'onClick', openHelp)`
13. `Reflect.set.apply(Reflect, [item, 'onClick', openHelp])`
14. `const Obj = globalThis.Object; Obj.defineProperty(item, 'onClick', ...)`
15. `const R = window.Reflect; R.set(item, 'onClick', openHelp)`
16. `globalThis.Object.assign(item, { onClick: openHelp })`
17. `window.Reflect.set(item, 'onClick', openHelp)`
18. `.apply()` 第二参数非数组字面量时 fail closed

## 六、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J14 的既有测试。尤其必须保留：

- 第 131 份审计 6 个绕过样例。
- 第 132 份审计 5 个绕过样例。
- bracket callee、直接函数别名、解构别名、命名空间别名测试。
- Object.assign 变量 source / descriptor 检测测试。
- 动态 computed key、运行时动态 key、运行时显式 key 注入测试。

## 七、验证命令

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

## 八、验收标准

- 第 133 份审计列出的绕过全部被拦截。
- 赋值式解构别名全部被拦截。
- bind 别名全部被拦截。
- call/apply 等价调用全部被拦截。
- globalThis/window Object/Reflect 命名空间全部被拦截。
- TASK-005J13/J14 已关闭的绕过不回潮。
- 非 action 字段写入不被误杀。
- 纯读取动态 key 不被误杀。
- `npm run verify` 通过。
- 后端 style-profit API 定向回归通过。
- 未修改后端、workflow、`02_源码`、TASK-006 或运行生成物。

## 九、禁止事项

- 禁止开放 `POST /api/reports/style-profit/snapshots` 前端入口。
- 禁止新增 `createStyleProfitSnapshot`、`snapshot_create`、`idempotency_key` 等创建入口调用。
- 禁止引入新的第三方 parser 依赖。
- 禁止通过扩大白名单、跳过测试、缩小扫描范围来让门禁变绿。
- 禁止把 TASK-006 解锁或写入 TASK-006 工程实现内容。

## 十、交付物

- 更新后的 `check-style-profit-contracts.mjs`
- 更新后的 `test-style-profit-contracts.mjs`
- `TASK-005J15_RuntimeMutator高级别名门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
