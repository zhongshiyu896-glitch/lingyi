# TASK-005J16 Runtime Mutator Sink 变体门禁整改工程任务单

- 任务编号：TASK-005J16
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改
- 前置审计：审计意见书第 134 份
- 更新时间：2026-04-14 22:36 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 对 runtime mutator sink 的剩余变体绕过，覆盖 `Reflect.apply`、字符串属性解构、计算属性解构、`globalThis/window` 解构命名空间，确保 style-profit surface 内任何等价调用 `Object.defineProperty/Object.assign/Reflect.set` 的路径都 fail closed。

## 二、背景问题

TASK-005J15 已关闭第 133 份审计中的赋值式解构基础形态、`bind/call/apply`、`globalThis/window` 命名空间别名，但审计官在第 134 份审计中复现以下 6 类绕过：

```ts
Reflect.apply(Object.defineProperty, Object, [item, 'onClick', { value: openHelp }])
Reflect.apply(Object.assign, Object, [item, { onClick: openHelp }])
Reflect.apply(Reflect.set, Reflect, [item, 'onClick', openHelp])

let dp
;({ 'defineProperty': dp } = Object)
dp(item, 'onClick', { value: openHelp })

let dp
;({ ['defineProperty']: dp } = Object)
dp(item, 'onClick', { value: openHelp })

const { Object: Obj } = globalThis
Obj.defineProperty(item, 'onClick', { value: openHelp })
```

这些路径仍等价于源 mutator API，必须继续拦截。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J16_RuntimeMutatorSink变体门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 Reflect.apply 必须识别

必须识别以下形式，并按第一个参数代表的源 API 解析：

```ts
Reflect.apply(Object.defineProperty, Object, [item, 'onClick', { value: openHelp }])
Reflect.apply(Object.defineProperties, Object, [item, { onClick: { value: openHelp } }])
Reflect.apply(Object.assign, Object, [item, { onClick: openHelp }])
Reflect.apply(Reflect.set, Reflect, [item, 'onClick', openHelp])
```

要求：

1. 第一个参数为 mutator API 时，第三个参数数组必须按源 API 参数位置解析。
2. 第三个参数不是数组字面量、含 spread、或无法静态还原时，在 style-profit surface 内 fail closed。
3. 支持 `Reflect['apply'](...)`。
4. 支持 namespace alias：`const R = Reflect; R.apply(...)`。

### 4.2 字符串属性解构必须识别

必须识别以下形式：

```ts
let dp
;({ 'defineProperty': dp } = Object)
dp(item, 'onClick', { value: openHelp })

let merge
;({ "assign": merge } = Object)
merge(item, { onClick: openHelp })
```

要求：字符串字面量属性名必须等价于同名裸属性。

### 4.3 计算属性解构必须识别

必须识别以下形式：

```ts
let dp
;({ ['defineProperty']: dp } = Object)
dp(item, 'onClick', { value: openHelp })

let set
;({ ['set']: set } = Reflect)
set(item, 'onClick', openHelp)
```

要求：

1. 字符串字面量计算属性必须解析为真实属性名。
2. 非字面量计算属性作为 mutator source 时，在 style-profit surface 内 fail closed。

### 4.4 globalThis/window 解构命名空间必须识别

必须识别以下形式：

```ts
const { Object: Obj } = globalThis
Obj.defineProperty(item, 'onClick', { value: openHelp })

const { Reflect: R } = window
R.set(item, 'onClick', openHelp)
```

要求：

1. `globalThis/window` 中解构出的 `Object/Reflect` 必须等价于 Object/Reflect 命名空间。
2. 后续点访问、括号访问、call/apply/bind 都必须沿用既有源 API 拦截逻辑。

### 4.5 不回潮要求

不得缩小 TASK-005J13/J14/J15 已关闭范围，包括：

- bracket callee
- 直接函数别名
- 变量 source/descriptor
- 声明式解构别名
- 命名空间别名
- 赋值式解构基础形态
- bind/call/apply
- globalThis/window 直接命名空间

## 五、必须新增反向测试

至少新增以下反向测试，每条都必须明确断言门禁失败：

1. `Reflect.apply(Object.defineProperty, Object, [item, 'onClick', { value: openHelp }])`
2. `Reflect.apply(Object.defineProperties, Object, [item, { onClick: { value: openHelp } }])`
3. `Reflect.apply(Object.assign, Object, [item, { onClick: openHelp }])`
4. `Reflect.apply(Reflect.set, Reflect, [item, 'onClick', openHelp])`
5. `Reflect['apply'](Object.defineProperty, Object, [item, 'onClick', { value: openHelp }])`
6. `const R = Reflect; R.apply(Object.assign, Object, [item, { onClick: openHelp }])`
7. `let dp; ({ 'defineProperty': dp } = Object); dp(item, 'onClick', ...)`
8. `let merge; ({ "assign": merge } = Object); merge(item, { onClick: openHelp })`
9. `let dp; ({ ['defineProperty']: dp } = Object); dp(item, 'onClick', ...)`
10. `let set; ({ ['set']: set } = Reflect); set(item, 'onClick', openHelp)`
11. `const { Object: Obj } = globalThis; Obj.defineProperty(item, 'onClick', ...)`
12. `const { Reflect: R } = window; R.set(item, 'onClick', openHelp)`
13. `Reflect.apply(..., args)` 中 `args` 不是数组字面量时 fail closed
14. `({ [ACTION_KEY]: dp } = Object)` 这类非字面量计算属性作为 mutator source 时 fail closed

## 六、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J15 的既有测试。尤其必须保留：

- 第 131 份审计 6 个绕过样例。
- 第 132 份审计 5 个绕过样例。
- 第 133 份审计 7 个绕过样例。
- bracket callee、直接函数别名、解构别名、命名空间别名、bind/call/apply、globalThis/window 测试。
- Object.assign 变量 source / descriptor 检测测试。

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

- 第 134 份审计列出的 6 类绕过全部被拦截。
- Reflect.apply 及 Reflect['apply'] 全部被拦截。
- 字符串属性解构、计算属性解构全部被拦截。
- globalThis/window 解构命名空间全部被拦截。
- TASK-005J13/J14/J15 已关闭的绕过不回潮。
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
- `TASK-005J16_RuntimeMutatorSink变体门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
