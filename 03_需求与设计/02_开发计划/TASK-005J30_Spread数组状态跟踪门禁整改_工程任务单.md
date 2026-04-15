# TASK-005J30 Spread 数组状态跟踪门禁整改工程任务单

- 任务编号：TASK-005J30
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / spread array state tracking
- 前置审计：审计意见书第 148 份
- 更新时间：2026-04-15 09:27 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 中 spread 参数数组“值缓存”导致的绕过。将 `arrayLiteralVariableMap` 从静态字面量缓存升级为数组状态跟踪：数组声明后只要发生元素写入、别名写入、mutating method、逃逸传参或无法证明未变更，就必须将该数组标记为 tainted/unknown，并在 style-profit surface 内 fail closed。

本任务只修前端只读契约门禁，不开放款式利润快照创建入口，不进入 TASK-006。

## 二、背景问题

TASK-005J29 已修复 `new unknownCtor(...args)` spread 主绕过，但审计官第 148 份审计复现：`arrayLiteralVariableMap` 会继续信任变量声明时的数组字面量。若后续执行以下变更，门禁仍按最初安全数组放行，而运行时实际参数已变为高危 Worker URL：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]
args[0] = 'data:text/javascript,postMessage(1)'
new Worker(...args)

const alias = args
alias[0] = 'data:text/javascript,postMessage(1)'
new Worker(...args)

args.splice(0, 1, 'data:text/javascript,postMessage(1)')
new Worker(...args)

args.unshift('data:text/javascript,postMessage(1)')
new Worker(...args)
```

最高风险是 spread 参数归一化目前是“值缓存”而不是“状态跟踪”。数组别名、元素写入和 mutating method 会让静态缓存与运行时值脱节。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J30_Spread数组状态跟踪门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 数组变量必须有状态模型

必须将 `arrayLiteralVariableMap` 或等价结构升级为数组状态模型，至少包含：

1. `array_id`
2. `initial_elements`
3. `aliases`
4. `status = clean | tainted | escaped | unknown`
5. `mutation_reasons`
6. `declaration_position`
7. `last_safe_position`

要求：

1. 只有 `status=clean` 且使用点在 `last_safe_position` 之后无 mutation/escape 时，才允许静态展开。
2. `status=tainted/escaped/unknown` 的数组用于 `new Ctor(...args)` 或 `Reflect.construct(Ctor, args)` 时，必须 fail closed。
3. 不允许继续只按变量声明时的数组字面量缓存做判断。
4. 不允许用“未检测到 mutation”默认通过；无法证明未变更时必须 fail closed。

### 4.2 元素写入必须污染数组

必须检测并污染数组状态：

```ts
args[0] = 'data:text/javascript,postMessage(1)'
args['0'] = 'data:text/javascript,postMessage(1)'
args[i] = workerUrl
args.length = 0
```

要求：

1. 任何元素写入都必须标记数组为 tainted。
2. `length` 写入必须标记数组为 tainted。
3. 写入发生在别名上，也必须污染原数组。
4. 写入发生在 spread 使用点之前必须影响该使用点。

### 4.3 数组别名必须跟踪

必须检测并跟踪：

```ts
const alias = args
let alias = args
alias[0] = 'data:text/javascript,postMessage(1)'
new Worker(...args)
```

要求：

1. `const alias = args` 必须让 alias 指向同一 `array_id`。
2. 别名链 `a -> b -> c` 必须追踪。
3. 任一别名写入或 mutating method 调用都必须污染同一数组。
4. 别名重新赋值后必须切断旧关系或标记 unknown，不能继续误用旧缓存。

### 4.4 mutating method 必须污染数组

必须检测以下 mutating method：

- `push`
- `pop`
- `shift`
- `unshift`
- `splice`
- `sort`
- `reverse`
- `fill`
- `copyWithin`

要求：

1. `args.splice(...)` 必须污染数组。
2. `args.unshift(...)` 必须污染数组。
3. `alias.splice(...)` / `alias.unshift(...)` 必须污染原数组。
4. `args['splice'](...)`、`args[methodName](...)` 中无法静态证明安全时必须 fail closed。
5. method 调用使用 call/apply，例如 `Array.prototype.splice.call(args, ...)`，必须污染数组或 fail closed。

### 4.5 数组逃逸必须 fail closed

以下情况必须标记数组为 escaped/unknown：

```ts
mutate(args)
store.args = args
window.args = args
return args
export const args = [...]
Object.assign(target, { args })
```

要求：

1. 数组作为参数传给未知函数时，标记 escaped/unknown。
2. 数组赋值到对象属性、全局对象、导出变量时，标记 escaped/unknown。
3. 数组从函数返回时，调用方无法证明只读则 fail closed。
4. escaped/unknown 数组用于 spread 构造 Worker 或 unknown constructor 时必须 fail closed。

### 4.6 Reflect.construct 参数数组同样适用

必须同步处理：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]
args[0] = 'data:text/javascript,postMessage(1)'
Reflect.construct(Worker, args)
```

要求：

1. Reflect.construct 的参数数组必须使用同一数组状态模型。
2. clean 数组可按静态元素展开。
3. tainted/escaped/unknown 数组必须 fail closed。
4. NewExpression spread 与 Reflect.construct 参数数组不能有两套状态判断。

## 五、必须新增反向测试

至少新增以下反向测试，每条必须断言门禁失败：

1. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)`
2. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args['0'] = 'data:text/javascript,postMessage(1)'; new Worker(...args)`
3. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; const alias = args; alias[0] = 'data:text/javascript,postMessage(1)'; new Worker(...args)`
4. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; const alias = args; alias.splice(0, 1, 'data:text/javascript,postMessage(1)'); new Worker(...args)`
5. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args.splice(0, 1, 'data:text/javascript,postMessage(1)'); new Worker(...args)`
6. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args.unshift('data:text/javascript,postMessage(1)'); new Worker(...args)`
7. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args.push('extra'); new Worker(...args)` 必须 fail closed
8. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args.reverse(); new Worker(...args)`
9. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args.fill('data:text/javascript,postMessage(1)'); new Worker(...args)`
10. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; mutate(args); new Worker(...args)`
11. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; store.args = args; new Worker(...args)`
12. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; Array.prototype.splice.call(args, 0, 1, 'data:text/javascript,postMessage(1)'); new Worker(...args)`
13. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args[methodName]('data:text/javascript,postMessage(1)'); new Worker(...args)` 必须 fail closed
14. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args[0] = 'data:text/javascript,postMessage(1)'; Reflect.construct(Worker, args)`
15. `const args = ['./readonly-worker.ts', { type: 'module' }]; const alias = args; alias[0] = 'data:text/javascript,postMessage(1)'; new unknownCtor(...args)`
16. `let args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; args = getArgs(); new Worker(...args)` 必须 fail closed

## 六、必须保留成功用例

至少保留或新增以下成功 fixture：

1. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new Worker(...args)`
2. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; Reflect.construct(Worker, args)`
3. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; const alias = args; new Worker(...alias)`，仅在 alias 未写入、未逃逸、未变更时允许
4. `const dateArgs = ['2026-04-15']; new Date(...dateArgs)`
5. `const urlArgs = ['./readonly-worker.ts', import.meta.url]; new URL(...urlArgs)` 不被误杀为 Worker 构造。
6. 普通 readonly 数组用于非构造场景不被误杀。

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J29 的既有测试。尤其必须保留：

- 第 131 份到第 148 份所有审计绕过样例。
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

- 第 148 份审计列出的数组写入、别名写入、splice、unshift 绕过全部被拦截。
- `arrayLiteralVariableMap` 不再是纯值缓存，已升级为数组状态跟踪或等价机制。
- 数组元素写入、别名写入、mutating method、逃逸传参都会污染数组或 fail closed。
- NewExpression spread 与 Reflect.construct 参数数组使用同一数组状态模型。
- tainted/escaped/unknown 数组用于 Worker/unknown constructor 构造时 fail closed。
- clean readonly 数组成功用例不被误杀。
- TASK-005J13-J29 已关闭的绕过不回潮。
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
- `TASK-005J30_Spread数组状态跟踪门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
