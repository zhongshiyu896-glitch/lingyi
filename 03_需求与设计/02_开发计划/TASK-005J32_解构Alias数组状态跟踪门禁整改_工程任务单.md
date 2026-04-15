# TASK-005J32 解构 Alias 数组状态跟踪门禁整改工程任务单

- 任务编号：TASK-005J32
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / destructuring alias array state tracking
- 前置审计：审计意见书第 150 份
- 更新时间：2026-04-15 10:38 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 中数组 / 对象解构 alias 未进入数组状态图导致的绕过。必须补齐 `ArrayBindingPattern / ObjectBindingPattern` 以及赋值式解构的 alias 跟踪，让解构出的 alias 与原数组共享同一 `array_id`；无法静态还原的解构来源必须标记为 `unknown/escaped` 并 fail closed。

本任务只修前端只读契约门禁，不开放款式利润快照创建入口，不进入 TASK-006。

## 二、背景问题

TASK-005J31 已修复函数声明提升与调用点副作用主路径，但审计官第 150 份审计复现数组/对象解构 alias 仍可绕过：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]
const [alias] = [args]
alias[0] = 'data:text/javascript,postMessage(1)'
new Worker(...args)
```

同类函数副作用场景也可绕过：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]
poison()
new Worker(...args)

function poison() {
  const [alias] = [args]
  alias[0] = 'data:text/javascript,postMessage(1)'
}
```

当前数组 alias 绑定只覆盖 `Identifier = Identifier`，未处理 `ArrayBindingPattern / ObjectBindingPattern`，导致解构 alias 写入没有污染原数组。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J32_解构Alias数组状态跟踪门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 ArrayBindingPattern 必须进入数组状态图

必须识别以下形式：

```ts
const [alias] = [args]
const [[alias]] = [[args]]
const [alias] = container
let alias
;[alias] = [args]
```

要求：

1. `const [alias] = [args]` 必须让 `alias` 指向 `args` 的同一 `array_id`。
2. 嵌套数组解构必须追踪到原数组。
3. 赋值式数组解构必须追踪 alias 或标记 unknown。
4. 解构源无法静态还原时，alias 必须标记为 unknown/escaped。
5. alias 后续元素写入、mutating method、逃逸必须污染原数组。

### 4.2 ObjectBindingPattern 必须进入数组状态图

必须识别以下形式：

```ts
const { value: alias } = { value: args }
const { args: alias } = holder
const { nested: { value: alias } } = { nested: { value: args } }
let alias
;({ value: alias } = { value: args })
```

要求：

1. 对象解构属性值可静态解析为 tracked array 时，alias 必须指向同一 `array_id`。
2. 对象解构重命名必须识别。
3. 嵌套对象解构必须识别。
4. 赋值式对象解构必须识别。
5. computed property、rest property、unknown holder 无法静态解析时必须 fail closed 或标记 alias unknown。

### 4.3 解构 alias 写入必须污染原数组

必须拦截以下形式：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]
const [alias] = [args]
alias[0] = 'data:text/javascript,postMessage(1)'
new Worker(...args)
```

要求：

1. 解构 alias 元素写入必须污染原数组。
2. 解构 alias mutating method 必须污染原数组。
3. 解构 alias 逃逸必须污染或标记原数组 escaped/unknown。
4. 解构 alias 重新赋值后必须切断旧关系或标记 unknown。

### 4.4 函数副作用中的解构 alias 必须按调用点生效

必须拦截以下形式：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]
poison()
new Worker(...args)

function poison() {
  const [alias] = [args]
  alias[0] = 'data:text/javascript,postMessage(1)'
}
```

要求：

1. 函数 side-effect summary 必须包含解构 alias 写入导致的数组污染。
2. 函数声明提升、函数表达式、箭头函数、函数别名、call/apply/bind 中的解构 alias 污染，必须按调用点生效。
3. 解构来源无法静态还原时，函数 summary 必须 conservative unknown。
4. 不允许函数内解构 alias 绕过数组状态跟踪。

### 4.5 Rest / default / computed 解构必须保守处理

必须处理以下形式：

```ts
const [...aliases] = [args]
const [alias = args] = []
const { [key]: alias } = holder
const { value: alias = args } = holder
```

要求：

1. rest 解构如果无法证明只读和静态来源，必须标记 unknown/escaped。
2. default value 为 tracked array 时必须追踪；无法证明 default 是否生效时必须 fail closed。
3. computed property 无法静态解析时必须 fail closed。
4. 解构 source 或 binding pattern 复杂不可还原时，不得放行后续 Worker spread。

### 4.6 Reflect.construct 参数数组同样适用

必须同步处理：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]
const [alias] = [args]
alias[0] = 'data:text/javascript,postMessage(1)'
Reflect.construct(Worker, args)
```

要求：

1. Reflect.construct 参数数组必须复用同一数组状态图。
2. 解构 alias 污染原数组后，Reflect.construct 必须 fail closed。
3. NewExpression spread 与 Reflect.construct 参数数组不得有两套 alias 判断。

## 五、必须新增反向测试

至少新增以下反向测试，每条必须断言门禁失败：

1. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const [alias] = [args]; alias[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)`
2. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const [[alias]] = [[args]]; alias[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)`
3. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; let alias; [alias] = [args]; alias[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)`
4. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const { value: alias } = { value: args }; alias[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)`
5. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const { nested: { value: alias } } = { nested: { value: args } }; alias[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)`
6. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; let alias; ({ value: alias } = { value: args }); alias[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)`
7. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const [alias] = [args]; alias.splice(0, 1, 'data:text/javascript,postMessage(1)'); new Worker(...args)`
8. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const [alias] = [args]; mutate(alias); new Worker(...args)`
9. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; poison(); new Worker(...args); function poison(){ const [alias] = [args]; alias[0] = 'data:text/javascript,postMessage(1)' }`
10. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const poison = () => { const [alias] = [args]; alias[0] = 'data:text/javascript,postMessage(1)' }; poison(); new Worker(...args)`
11. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; function poison(){ const { value: alias } = { value: args }; alias[0] = 'data:text/javascript,postMessage(1)' }; poison(); new Worker(...args)`
12. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const [...aliases] = [args]; aliases[0][0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)` 必须 fail closed 或精确拦截
13. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const [alias = args] = []; alias[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)` 必须 fail closed 或精确拦截
14. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const { [key]: alias } = holder; alias[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)` 必须 fail closed
15. `const args = [new URL('./readonly-worker.ts', import.meta.url)]; const [alias] = [args]; alias[0] = 'data:text/javascript,postMessage(1)'; Reflect.construct(Worker, args)`
16. `const args = ['./readonly-worker.ts']; const [alias] = [args]; alias[0] = 'data:text/javascript,postMessage(1)'; new unknownCtor(...args)`

## 六、必须保留成功用例

至少保留或新增以下成功 fixture：

1. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; const [alias] = [args]; new Worker(...alias)`，仅在 alias 未写入、未逃逸、未变更时允许
2. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; const { value: alias } = { value: args }; new Worker(...alias)`，仅在 alias clean 时允许
3. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new Worker(...args)`
4. `const dateArgs = ['2026-04-15']; const [alias] = [dateArgs]; new Date(...alias)`
5. 普通非数组值解构不被误杀。
6. 普通 readonly 解构用于非构造场景不被误杀。

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J31 的既有测试。尤其必须保留：

- 第 131 份到第 150 份所有审计绕过样例。
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

- 第 150 份审计列出的数组/对象解构 alias 绕过全部被拦截。
- `ArrayBindingPattern / ObjectBindingPattern` 已进入数组状态图。
- 解构 alias 与原数组共享同一 `array_id` 或在无法还原时 fail closed。
- 解构 alias 写入、mutating method、逃逸会污染原数组。
- 函数 side-effect summary 能识别函数内解构 alias 污染，并按调用点生效。
- Reflect.construct 参数数组同样受解构 alias 状态影响。
- clean 解构 alias 成功用例不被误杀。
- TASK-005J13-J31 已关闭的绕过不回潮。
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
- `TASK-005J32_解构Alias数组状态跟踪门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
