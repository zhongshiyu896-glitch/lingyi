# TASK-005J28 Unknown Constructor 字符串 URL 严格门禁整改工程任务单

- 任务编号：TASK-005J28
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / unknown constructor URL 口径收紧
- 前置审计：审计意见书第 146 份
- 更新时间：2026-04-15 08:42 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 中 unknown constructor 分支对普通字符串 Worker URL 的放行问题。将 known Worker 与 unknown constructor 的 URL 判定统一：在 style-profit surface 内，无法证明是安全非 Worker 构造器时，任何字符串路径、普通本地 worker 字符串、变量 URL、模板 URL、函数返回 URL、Blob URL 标记变量都必须 fail closed。

本任务只修前端只读契约门禁，不开放款式利润快照创建入口，不进入 TASK-006。

## 二、背景问题

TASK-005J27 已修复函数返回 Worker/SharedWorker + 高危协议主路径，但审计官第 146 份审计复现以下绕过：

```ts
function getWorker() {
  if (ready) return Worker
  return Worker
}

new (getWorker())('/runtime/style-profit-worker.js', { type: 'module' })
```

直接 `new Worker('./readonly-worker.ts')` 已会被拦截为非规范入口，但复杂函数返回 Worker 后，constructor 被降级为 unknown，unknown constructor 分支仍放行普通字符串路径，导致绕开 Worker 专用 URL 规则。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J28_UnknownConstructor字符串URL严格门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 unknown constructor 不得放行普通字符串路径

必须修改 `classifyUnknownWorkerConstructTargetSourceStrict()` 或等价逻辑，使 unknown constructor 在 style-profit surface 内不再放行以下 URL 参数：

1. `'/runtime/style-profit-worker.js'`
2. `'./readonly-worker.ts'`
3. `'../workers/readonly-worker.ts'`
4. `'worker.js'`
5. `'data:text/javascript,postMessage(1)'`
6. `'blob:https://example.test/worker'`
7. `'https://example.test/worker.js'`
8. 模板字符串路径
9. URL 变量
10. 函数返回 URL
11. Blob URL 标记变量

要求：

1. unknown constructor + 任意 URL-like 第一参数必须 fail closed。
2. URL-like 包括字符串路径、协议 URL、模板 URL、变量 URL、`new URL(...)` 表达式、函数返回 URL、Blob URL 标记变量。
3. 不允许再用“本地字符串路径”作为 unknown constructor 的成功条件。
4. 不允许通过缩小 style-profit surface 扫描范围规避该规则。

### 4.2 known Worker 与 unknown constructor 的 URL 判定必须同口径

要求：

1. `new Worker('./readonly-worker.ts')` 失败。
2. `new (unknownCtor)('./readonly-worker.ts')` 在 style-profit surface 内也失败。
3. `new Worker('/runtime/style-profit-worker.js')` 失败。
4. `new (unknownCtor)('/runtime/style-profit-worker.js')` 在 style-profit surface 内也失败。
5. 唯一允许的 Worker URL 形式仍是 `new URL('./readonly-worker.ts', import.meta.url)` 且构造器必须可证明为 Worker/SharedWorker 或明确安全的 Worker alias。
6. constructor 解析失败时不得比 known Worker 更宽松。

### 4.3 复杂函数返回必须 fail closed

必须处理以下形式：

```ts
function getWorker() {
  if (ready) return Worker
  return Worker
}

new (getWorker())('/runtime/style-profit-worker.js', { type: 'module' })
```

要求：

1. 多语句函数、多 return 函数、带条件控制流函数如果无法静态证明返回安全非 Worker 构造器，则 constructor_confidence 必须为 unknown。
2. constructor_confidence=unknown 且 URL-like 第一参数存在时必须 fail closed。
3. 两个分支都返回 Worker 但当前解析器无法证明时，也必须 fail closed，不能降级放行。
4. 若解析器能证明两个分支都返回 Worker，则必须按 known Worker URL 规则拦截普通字符串路径。

### 4.4 明确 safe known constructor 白名单

允许保留少量明确安全的非 Worker 构造器白名单，例如：

- `Date`
- `Error`
- `RegExp`
- `URL`
- `Map`
- `Set`

要求：

1. 只有明确解析为 safe known constructor 时，才允许其自身合法参数通过。
2. `new URL('./readonly-worker.ts', import.meta.url)` 不得被误判为 Worker 构造；它只是 Worker URL 参数表达式。
3. unknown constructor 不得借用 safe known constructor 白名单。
4. 白名单必须集中定义，并有测试证明不会让 `unknownCtor('/runtime/style-profit-worker.js')` 通过。

### 4.5 Reflect.construct 同步收紧

必须同步处理：

```ts
Reflect.construct(unknownCtor, ['/runtime/style-profit-worker.js'])
Reflect.construct(getWorker(), ['/runtime/style-profit-worker.js'])
```

要求：

1. Reflect.construct 的 unknown constructor 分支与 `new unknownCtor(...)` 同口径。
2. 参数数组第一项为普通字符串路径时 fail closed。
3. 参数数组第一项为变量 URL、模板 URL、函数返回 URL、Blob URL 标记变量时 fail closed。
4. Reflect.construct 第三个参数不得豁免 unknown constructor URL 判定。

## 五、必须新增反向测试

至少新增以下反向测试，每条必须断言门禁失败：

1. `function getWorker() { if (ready) return Worker; return Worker } new (getWorker())('/runtime/style-profit-worker.js', { type: 'module' })`
2. `function getWorker() { if (ready) return Worker; return Worker } new (getWorker())('./readonly-worker.ts', { type: 'module' })`
3. `const getWorker = () => condition ? Worker : unknownCtor; new (getWorker())('/runtime/style-profit-worker.js', { type: 'module' })`
4. `new unknownCtor('/runtime/style-profit-worker.js', { type: 'module' })`
5. `new unknownCtor('./readonly-worker.ts', { type: 'module' })`
6. `new unknownCtor(workerUrl, { type: 'module' })`
7. ``new unknownCtor(`/runtime/${name}.js`, { type: 'module' })``
8. `new unknownCtor(getWorkerUrl(), { type: 'module' })`
9. `new unknownCtor(blobWorkerUrl, { type: 'module' })`，其中 `blobWorkerUrl` 为 Blob URL 标记变量
10. `Reflect.construct(unknownCtor, ['/runtime/style-profit-worker.js', { type: 'module' }])`
11. `Reflect.construct(getWorker(), ['/runtime/style-profit-worker.js', { type: 'module' }])`
12. `Reflect.construct(unknownCtor, [workerUrl, { type: 'module' }])`
13. `Reflect.construct(unknownCtor, [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }])` 必须 fail closed，因为 constructor unknown
14. `Reflect.construct(unknownCtor, ['/runtime/style-profit-worker.js'], SafeCtor)` 不得被第三参数豁免

## 六、必须保留成功用例

至少保留或新增以下成功 fixture：

1. `new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
2. `const W = Worker; new W(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
3. `const getWorker = () => Worker; new (getWorker())(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
4. `Reflect.construct(Worker, [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }])`
5. `new Date('2026-04-15')`
6. `new URL('./readonly-worker.ts', import.meta.url)` 不被误杀为 Worker 构造。
7. `new Error('readonly message')` 不被误杀。

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J27 的既有测试。尤其必须保留：

- 第 131 份到第 146 份所有审计绕过样例。
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

- 第 146 份审计列出的普通字符串 Worker URL 绕过被拦截。
- unknown constructor 不再放行普通本地字符串路径。
- known Worker 与 unknown constructor 的 URL 判定同口径，unknown 不得更宽松。
- Reflect.construct unknown constructor 分支同步收紧。
- safe known constructor 白名单集中、明确、可测试。
- 静态本地 Worker 成功用例不被误杀。
- TASK-005J13-J27 已关闭的绕过不回潮。
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
- `TASK-005J28_UnknownConstructor字符串URL严格门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
