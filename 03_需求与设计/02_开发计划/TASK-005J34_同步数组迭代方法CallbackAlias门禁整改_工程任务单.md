# TASK-005J34 同步数组迭代方法 Callback Alias 门禁整改工程任务单

- 任务编号：TASK-005J34
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / synchronous array iteration callback alias tracking
- 前置审计：审计意见书第 152 份
- 更新时间：2026-04-15 12:00 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 中同步数组迭代方法 callback 参数 alias 跟踪不完整的问题。TASK-005J33 已覆盖 `forEach/map/some/every/filter/find`，但 `reduce/reduceRight/flatMap/findIndex/findLast/findLastIndex` 仍未进入 callback 参数解构 alias 跟踪，导致 callback 先污染 Worker 参数数组、门禁仍放行。

本任务要求把同步数组迭代方法从简单白名单升级为 method descriptor map，按方法定义 callback 当前元素参数位置；无法静态还原 iterable、callback 或元素来源时必须 fail closed。

本任务只修前端只读契约门禁，不开放款式利润快照创建入口，不进入 TASK-006。

## 二、背景问题

审计意见书第 152 份确认 TASK-005J33 主路径已通过，但以下同步 callback sink 仍可绕过：

```ts
const args = ['./readonly-worker.ts']

[[args]].findIndex(([alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return false
})

new Worker(...args)
```

```ts
const args = ['./readonly-worker.ts']

[[args]].reduce((acc, [alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return acc
}, 0)

new Worker(...args)
```

根因：当前 `runtimeArrayIterationMethodNameSet` 只覆盖 `forEach/map/some/every/filter/find`，且没有按方法描述 callback 参数位置。`reduce/reduceRight` 的当前元素参数是 callback 第 2 个参数，不能按普通方法第 1 个参数处理。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J34_同步数组迭代方法CallbackAlias门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 同步数组迭代方法必须改为 descriptor map

禁止继续只维护简单 method name set。必须改为类似以下语义的 descriptor：

| 方法 | 是否同步执行 callback | 当前元素参数位置 | 备注 |
| --- | --- | --- | --- |
| `forEach` | 是 | 0 | callback 第 1 个参数是 item |
| `map` | 是 | 0 | callback 第 1 个参数是 item |
| `some` | 是 | 0 | callback 第 1 个参数是 item |
| `every` | 是 | 0 | callback 第 1 个参数是 item |
| `filter` | 是 | 0 | callback 第 1 个参数是 item |
| `find` | 是 | 0 | callback 第 1 个参数是 item |
| `findIndex` | 是 | 0 | callback 第 1 个参数是 item |
| `findLast` | 是 | 0 | callback 第 1 个参数是 item |
| `findLastIndex` | 是 | 0 | callback 第 1 个参数是 item |
| `flatMap` | 是 | 0 | callback 第 1 个参数是 item |
| `reduce` | 是 | 1 | callback 第 2 个参数是 currentValue |
| `reduceRight` | 是 | 1 | callback 第 2 个参数是 currentValue |

要求：

1. `applyRuntimeIterationCallbackSummaryAtCall()` 必须按 descriptor 获取 callback 当前元素参数位置。
2. `reduce/reduceRight` 必须把 iterable element 绑定到 callback 第 2 个参数，而不是 accumulator。
3. 其他同步迭代方法继续绑定 callback 第 1 个参数。
4. descriptor 无法识别或 callback/iterable 无法静态证明安全时，必须 fail closed 或标记相关 tracked arrays unknown。
5. 不允许用扩大白名单但不处理参数位的方式通过测试。

### 4.2 reduce/reduceRight 必须精确处理当前元素参数

必须拦截：

```ts
const args = ['./readonly-worker.ts']

[[args]].reduce((acc, [alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return acc
}, 0)

new Worker(...args)
```

要求：

1. callback 第 1 个参数 `acc` 不得被误认为 current item。
2. callback 第 2 个参数 `[alias]` 必须绑定到 iterable element `[args]`。
3. alias 写入必须污染原数组 `args`。
4. `new Worker(...args)` 必须 fail closed。
5. `reduceRight` 与 `reduce` 同口径。

### 4.3 flatMap/findIndex/findLast/findLastIndex 必须与 find 同口径

必须拦截：

```ts
const args = ['./readonly-worker.ts']

[[args]].flatMap(([alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return []
})

new Worker(...args)
```

```ts
const args = ['./readonly-worker.ts']

[[args]].findIndex(([alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return false
})

new Worker(...args)
```

要求：

1. `flatMap/findIndex/findLast/findLastIndex` callback 第 1 个参数必须作为 current item 绑定。
2. callback 参数解构 alias 必须进入数组状态图。
3. alias 写入、mutating method、逃逸必须污染原数组。
4. 这些方法与 `forEach/map/find` 的 fail-closed 规则一致。

### 4.4 未知同步迭代来源必须 fail closed

必须处理：

```ts
const args = ['./readonly-worker.ts']

collection.reduce((acc, [alias]) => {
  alias[0] = 'data:text/javascript,postMessage(1)'
  return acc
}, 0)

new Worker(...args)
```

要求：

1. 如果 `collection` 无法静态还原，但 callback 中存在参数解构 alias 写入并且作用域内存在 tracked Worker args，必须 fail closed。
2. 不得把未知 collection 当作“不相关”直接放行。
3. 如果确实能证明 callback 不写入、不逃逸、不污染 tracked arrays，可保留成功用例。

### 4.5 必须保留 TASK-005J33 已通过路径

不得回退以下已通过路径：

1. `for...of` 绑定进入数组状态图。
2. 函数声明参数解构进入数组状态图。
3. 箭头函数参数解构进入数组状态图。
4. 函数表达式参数解构进入数组状态图。
5. `forEach/map/some/every/filter/find` callback 参数解构进入数组状态图。
6. `Reflect.construct` 与 `new Worker(...args)` 使用同一数组状态图。

## 五、必须新增反向测试

每条必须断言门禁失败：

1. `[[args]].findIndex(([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return false }) ; new Worker(...args)`
2. `[[args]].findLast(([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return false }) ; new Worker(...args)`
3. `[[args]].findLastIndex(([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return false }) ; new Worker(...args)`
4. `[[args]].flatMap(([alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return [] }) ; new Worker(...args)`
5. `[[args]].reduce((acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0) ; new Worker(...args)`
6. `[[args]].reduceRight((acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0) ; new Worker(...args)`
7. `[[args]].reduce((acc, { value: alias }) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0) ; new Worker(...args)`，其中 iterable item 为 `{ value: args }`
8. `collection.reduce((acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0); new Worker(...args)`，collection 无法静态证明安全时必须 fail closed
9. `[[args]].flatMap(([alias]) => { alias.splice(0, 1, 'data:text/javascript,postMessage(1)'); return [] }); new Worker(...args)`
10. `[[args]].findIndex(([alias]) => { escape(alias); return false }); new Worker(...args)`，escape 无法证明安全时必须 fail closed
11. `[[args]].reduce((acc, [alias]) => { alias[0] = '/runtime/style-profit-worker.js'; return acc }, 0); new unknownCtor(...args)`
12. `[[args]].reduce((acc, [alias]) => { alias[0] = 'data:text/javascript,postMessage(1)'; return acc }, 0); Reflect.construct(Worker, args)`

## 六、必须保留成功用例

至少保留或新增以下成功 fixture：

1. `[[args]].findIndex(([alias]) => readonly(alias)); new Worker(...args)`，仅当 readonly 明确安全且 alias 未写入/逃逸时允许。
2. `[[args]].flatMap(([alias]) => { readonly(alias); return [] }); new Worker(...args)`，仅当 readonly 明确安全时允许。
3. `[[args]].reduce((acc, [alias]) => { readonly(alias); return acc }, 0); new Worker(...args)`，仅当 readonly 明确安全时允许。
4. `const nums = [[1]]; nums.reduce((acc, [n]) => acc + n, 0)` 不得被误杀。
5. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new Worker(...args)` 必须继续通过。

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J33 的既有测试。尤其必须保留：

- 第 131 份到第 152 份所有审计绕过样例。
- TASK-005J33 已关闭的 `for...of`、函数参数、回调参数解构主路径。
- `forEach/map/some/every/filter/find` callback 参数解构门禁。
- NewExpression spread 参数归一化测试。
- Reflect.construct 参数数组测试。
- unknown constructor URL 严格门禁测试。
- Worker.bind、Reflect.construct、函数返回 Worker、IIFE 返回 Worker 测试。
- Worker alias、namespace alias、conditional alias、container alias 测试。
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
.venv/bin/python -m pytest -q tests/test_style_profit_api.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 九、验收标准

- 第 152 份审计列出的 `reduce/reduceRight/flatMap/findIndex/findLast/findLastIndex` 绕过全部被拦截。
- 同步数组迭代方法不再使用简单白名单，而是 method descriptor map。
- `reduce/reduceRight` 正确使用 callback 第 2 个参数作为 current item。
- `flatMap/findIndex/findLast/findLastIndex` 正确使用 callback 第 1 个参数作为 current item。
- 未知 iterable/callback/source 无法静态还原时 fail closed。
- clean 只读同步迭代成功用例不被误杀。
- TASK-005J13-J33 已关闭的绕过不回潮。
- `npm run verify` 通过。
- 后端 style-profit API 定向回归通过。
- 未修改后端、workflow、`02_源码`、TASK-006 或运行生成物。

## 十、禁止事项

- 禁止开放 `POST /api/reports/style-profit/snapshots` 前端入口。
- 禁止新增 `createStyleProfitSnapshot`、`snapshot_create`、`idempotency_key` 等创建入口调用。
- 禁止引入新的第三方 parser 依赖。
- 禁止通过扩大白名单但不处理参数位来让门禁变绿。
- 禁止跳过、删除或降级既有门禁测试。
- 禁止把 TASK-006 解锁或写入 TASK-006 工程实现内容。

## 十一、交付物

- 更新后的 `check-style-profit-contracts.mjs`
- 更新后的 `test-style-profit-contracts.mjs`
- `TASK-005J34_同步数组迭代方法CallbackAlias门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
