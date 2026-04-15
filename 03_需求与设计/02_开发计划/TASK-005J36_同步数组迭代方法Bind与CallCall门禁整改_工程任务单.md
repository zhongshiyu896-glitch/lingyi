# TASK-005J36 同步数组迭代方法 Bind 与 CallCall 门禁整改工程任务单

- 任务编号：TASK-005J36
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / bound iteration function and call.call descriptor
- 前置审计：审计意见书第 154 份
- 更新时间：2026-04-15 13:33 CST
- 作者：技术架构师

## 一、任务目标

修复同步数组迭代方法 `bind` 预绑定与 `call.call` 中转未进入 TASK-005J35 iteration descriptor 的问题。J35 已覆盖 direct / `.call` / `.apply` / `Reflect.apply` 主路径，但 `Array.prototype.reduce.bind(...)` 生成的 bound function，以及 `Function.prototype.call.call(Array.prototype.reduce, ...)`、`Array.prototype.reduce.call.call(...)` 仍可同步执行 callback、污染 Worker 参数数组并绕过门禁。

本任务要求将 direct / `.call` / `.apply` / `Reflect.apply` / `.bind` / `call.call` 全部归一到同一个 `IterationInvocationDescriptor`。无法静态还原 bound target、thisArg、boundArgs、后续 args 或 call.call 目标时，只要作用域内存在 tracked Worker args，必须 fail closed。

本任务只修前端只读契约门禁，不开放款式利润快照创建入口，不进入 TASK-006。

## 二、背景问题

审计意见书第 154 份确认 J35 已修复 direct / `.call` / `.apply` / `Reflect.apply` 主路径，但以下写法仍返回通过：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]

const reduceBound = Array.prototype.reduce.bind([[args]])
reduceBound((acc, [alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return acc
}, 0)

new Worker(...args)
```

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]

const reduceBound = Array.prototype.reduce.bind([[args]], (acc, [alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return acc
}, 0)
reduceBound()

new Worker(...args)
```

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]

Function.prototype.call.call(
  Array.prototype.reduce,
  [[args]],
  (acc, [alias]) => {
    alias[0] = 'data:text/javascript,postMessage(1)'
    return acc
  },
  0,
)

new Worker(...args)
```

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]

Array.prototype.reduce.call.call(
  Array.prototype.reduce,
  [[args]],
  (acc, [alias]) => {
    alias[0] = 'data:text/javascript,postMessage(1)'
    return acc
  },
  0,
)

new Worker(...args)
```

根因：J35 的 `resolveRuntimeArrayIterationCallDescriptor()` 覆盖 direct / call / apply / Reflect.apply，但没有建立 bound iteration function summary，也没有把 `Function.prototype.call.call(...)`、`Array.prototype.<method>.call.call(...)` 还原成真实迭代方法调用。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J36_同步数组迭代方法Bind与CallCall门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 IterationInvocationDescriptor 必须统一覆盖六类入口

必须把以下入口统一归一为同一个 descriptor：

1. direct call：`arr.reduce(callback, initialValue)`
2. `.call`：`Array.prototype.reduce.call(arr, callback, initialValue)`
3. `.apply`：`Array.prototype.reduce.apply(arr, [callback, initialValue])`
4. `Reflect.apply`：`Reflect.apply(Array.prototype.reduce, arr, [callback, initialValue])`
5. `.bind`：`Array.prototype.reduce.bind(arr, ...boundArgs)(...laterArgs)`
6. `call.call`：`Function.prototype.call.call(Array.prototype.reduce, arr, callback, initialValue)`、`Array.prototype.reduce.call.call(Array.prototype.reduce, arr, callback, initialValue)`

Descriptor 至少包含：

| 字段 | 含义 |
| --- | --- |
| `methodName` | 同步数组迭代方法名 |
| `iterableExpression` | 被迭代对象 |
| `callbackExpression` | callback，可能来自 boundArgs 或 laterArgs |
| `initialValueExpression` | reduce/reduceRight initialValue，可能来自 boundArgs 或 laterArgs |
| `argumentMode` | `direct/call/apply/reflect_apply/bind/call_call` |
| `boundArgs` | bind 阶段预绑定参数 |
| `laterArgs` | bound function 调用阶段补充参数 |

要求：

1. 所有入口必须共用 J34/J35 的 method descriptor map。
2. 所有入口必须共用 current item 参数位规则。
3. 所有入口必须共用数组状态图与 callback side-effect summary。
4. 无法静态还原目标、thisArg、boundArgs、laterArgs 或 argsArray 时，对含 tracked Worker args 的场景 fail closed。
5. 不允许只补 `reduce.bind` 单点，也不允许为 bind/call.call 复制一套独立污染逻辑。

### 4.2 必须识别 bind 返回的 bound iteration function

必须拦截：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]

const reduceBound = Array.prototype.reduce.bind([[args]])
reduceBound((acc, [alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return acc
}, 0)

new Worker(...args)
```

要求：

1. `Array.prototype.reduce.bind([[args]])` 必须生成 bound iteration function summary。
2. summary 必须记录 `methodName=reduce` 与 bound thisArg `[[args]]`。
3. `reduceBound(callback, initialValue)` 调用时，必须合并 bound thisArg 与 laterArgs。
4. callback 第 2 个参数 `[alias]` 必须按 reduce current item 绑定 iterable element。
5. alias 写入必须污染原数组 `args`。
6. `new Worker(...args)` 必须 fail closed。

### 4.3 必须识别 bind 预绑定 callback 和 initialValue

必须拦截：

```ts
const args = [new URL('./readonly-worker.ts', import.meta.url)]

const reduceBound = Array.prototype.reduce.bind([[args]], (acc, [alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return acc
}, 0)
reduceBound()

new Worker(...args)
```

要求：

1. bind 阶段预绑定 callback 和 initialValue 必须进入 descriptor。
2. 调用阶段没有 laterArgs 时，仍必须执行 callback summary。
3. callback 污染必须影响后续 Worker spread。
4. 预绑定参数数组无法静态还原时必须 fail closed。

### 4.4 必须识别 call.call 中转

必须拦截：

```ts
Function.prototype.call.call(
  Array.prototype.reduce,
  [[args]],
  callback,
  0,
)
```

以及：

```ts
Array.prototype.reduce.call.call(
  Array.prototype.reduce,
  [[args]],
  callback,
  0,
)
```

要求：

1. `Function.prototype.call.call(target, thisArg, ...args)` 必须还原为 `target.call(thisArg, ...args)`。
2. `target=Array.prototype.reduce` 时，必须进入 iteration descriptor。
3. `Array.prototype.reduce.call.call(Array.prototype.reduce, thisArg, ...args)` 必须同口径处理。
4. target、thisArg、args 无法静态还原时 fail closed。
5. `reduce/reduceRight` 仍按 callback 第 2 个参数作为 current item。

### 4.5 必须覆盖其他同步迭代方法

bind 和 call.call 不能只覆盖 reduce。至少覆盖：

- `reduce`
- `reduceRight`
- `flatMap`
- `findIndex`
- `findLast`
- `findLastIndex`
- J34/J35 已纳入 descriptor 的其他同步方法

要求：

1. `findIndex.bind([[args]])(([alias]) => ...)` 必须 fail closed。
2. `flatMap.bind([[args]])(([alias]) => ...)` 必须 fail closed。
3. `Function.prototype.call.call(Array.prototype.findIndex, [[args]], callback)` 必须 fail closed。
4. `Function.prototype.call.call(Array.prototype.flatMap, [[args]], callback)` 必须 fail closed。

### 4.6 必须保留 J35 主路径

不得回退以下已通过路径：

1. direct call。
2. `.call`。
3. `.apply`。
4. `Reflect.apply`。
5. 字面量 bracket key。
6. method target 无法还原 fail closed。
7. apply 参数数组无法还原 fail closed。
8. clean readonly 等价调用成功用例。

## 五、必须新增反向测试

每条必须断言门禁失败：

1. `const reduceBound = Array.prototype.reduce.bind([[args]]); reduceBound((acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0); new Worker(...args)`
2. `const reduceBound = Array.prototype.reduce.bind([[args]], (acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0); reduceBound(); new Worker(...args)`
3. `const reduceBound = Array.prototype.reduce.bind([[args]], (acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }); reduceBound(0); new Worker(...args)`
4. `const reduceRightBound = Array.prototype.reduceRight.bind([[args]]); reduceRightBound((acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0); new Worker(...args)`
5. `const findIndexBound = Array.prototype.findIndex.bind([[args]]); findIndexBound(([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return false }); new Worker(...args)`
6. `const flatMapBound = Array.prototype.flatMap.bind([[args]]); flatMapBound(([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return [] }); new Worker(...args)`
7. `Function.prototype.call.call(Array.prototype.reduce, [[args]], (acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0); new Worker(...args)`
8. `Array.prototype.reduce.call.call(Array.prototype.reduce, [[args]], (acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0); new Worker(...args)`
9. `Function.prototype.call.call(Array.prototype.findIndex, [[args]], ([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return false }); new Worker(...args)`
10. `Function.prototype.call.call(Array.prototype.flatMap, [[args]], ([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return [] }); new Worker(...args)`
11. `const bound = Array.prototype.reduce.bind(collection); bound((acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0); new Worker(...args)`，collection 无法静态证明安全时必须 fail closed
12. `const bound = Array.prototype.reduce.bind([[args]], ...dynamicArgs); bound(); new Worker(...args)`，dynamicArgs 无法静态展开时必须 fail closed
13. `const call = Function.prototype.call.call; call(Array.prototype.reduce, [[args]], (acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0); new Worker(...args)`，无法静态证明 call alias 时必须 fail closed
14. `Array.prototype.reduce.bind([[args]], (acc, [alias]) => { alias[0] = '/runtime/style-profit-worker.js'; return acc }, 0)(); new unknownCtor(...args)`
15. `Array.prototype.reduce.bind([[args]], (acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0)(); Reflect.construct(Worker, args)`

## 六、必须保留成功用例

至少保留或新增以下成功 fixture：

1. `const reduceBound = Array.prototype.reduce.bind([[args]]); reduceBound((acc, [alias]) => { readonly(alias); return acc }, 0); new Worker(...args)`，仅当 readonly 明确安全时允许。
2. `const findIndexBound = Array.prototype.findIndex.bind([[args]]); findIndexBound(([alias]) => { readonly(alias); return false }); new Worker(...args)`，仅当 readonly 明确安全时允许。
3. `Function.prototype.call.call(Array.prototype.reduce, [[args]], (acc, [alias]) => { readonly(alias); return acc }, 0); new Worker(...args)`，仅当 readonly 明确安全时允许。
4. `const reduceBound = Array.prototype.reduce.bind([[1]]); reduceBound((acc, [n]) => acc + n, 0)` 不得被误杀。
5. J35 的 direct/call/apply/Reflect.apply 成功用例必须继续通过。

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J35 的既有测试。尤其必须保留：

- 第 131 份到第 154 份所有审计绕过样例。
- J35 的 direct/call/apply/Reflect.apply 等价调用门禁。
- J34 的同步迭代 method descriptor 和参数位测试。
- J33 的 `for...of`、函数参数、回调参数解构主路径。
- NewExpression spread 参数归一化测试。
- Reflect.construct 参数数组测试。
- unknown constructor URL 严格门禁测试。
- Worker.bind、Reflect.construct、函数返回 Worker、IIFE 返回 Worker 测试。
- runtime mutator、dynamic import、Blob URL、timer、constructor、eval/Function 全部既有测试。

## 八、验证命令

工程师必须执行并在证据文件中贴摘要：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high

cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 九、验收标准

- 第 154 份审计列出的 `bind` 预绑定和 `call.call` 中转绕过全部被拦截。
- direct/call/apply/Reflect.apply/bind/call.call 共用同一个 `IterationInvocationDescriptor`。
- bound function summary 能记录 `methodName`、bound thisArg、bound callback、bound initialValue。
- boundArgs 与 laterArgs 能正确合并。
- `reduce/reduceRight` 在 bind/call.call 中仍正确使用 callback 第 2 个参数作为 current item。
- `flatMap/findIndex/findLast/findLastIndex` 在 bind/call.call 中仍正确使用 callback 第 1 个参数作为 current item。
- target、thisArg、boundArgs、laterArgs、call.call 参数无法静态还原时 fail closed。
- clean readonly bind/call.call 成功用例不被误杀。
- TASK-005J13-J35 已关闭的绕过不回潮。
- `npm run verify` 通过。
- 后端 style-profit API 只读回归通过。
- 未修改后端、workflow、`02_源码`、TASK-006 或运行生成物。

## 十、禁止事项

- 禁止开放 `POST /api/reports/style-profit/snapshots` 前端入口。
- 禁止新增 `createStyleProfitSnapshot`、`snapshot_create`、`idempotency_key` 等创建入口调用。
- 禁止引入新的第三方 parser 依赖。
- 禁止只补 `reduce.bind` 单点而不建立统一 descriptor。
- 禁止通过扩大白名单但不处理 bind/call.call 参数映射来让门禁变绿。
- 禁止跳过、删除或降级既有门禁测试。
- 禁止把 TASK-006 解锁或写入 TASK-006 工程实现内容。

## 十一、交付物

- 更新后的 `check-style-profit-contracts.mjs`
- 更新后的 `test-style-profit-contracts.mjs`
- `TASK-005J36_同步数组迭代方法Bind与CallCall门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
