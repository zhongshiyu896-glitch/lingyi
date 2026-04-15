# TASK-005J29 NewExpression Spread 参数归一化门禁整改工程任务单

- 任务编号：TASK-005J29
- 模块：款式利润报表 / 前端只读契约门禁
- 优先级：P0
- 任务类型：审计阻断整改 / new 与 Reflect.construct 参数归一化
- 前置审计：审计意见书第 147 份
- 更新时间：2026-04-15 09:05 CST
- 作者：技术架构师

## 一、任务目标

修复 `check-style-profit-contracts.mjs` 中 `new unknownCtor(...args)` 的 spread 参数绕过。将 `NewExpression` 与 `Reflect.construct` 的参数处理统一为 invocation arguments descriptor，确保 spread/rest/数组中转/变量参数无法静态证明安全时，在 style-profit surface 内 fail closed。

本任务只修前端只读契约门禁，不开放款式利润快照创建入口，不进入 TASK-006。

## 二、背景问题

TASK-005J28 已修复 ordinary unknown constructor URL 参数，但审计官第 147 份审计复现 `new unknownCtor(...args)` 仍可绕过。原因是 `NewExpression` 路径直接把 `SpreadElement` 当作第一参数传入，而 `classifyUnknownWorkerConstructTargetSourceStrict()` 未处理 `SpreadElement`，最终落到 `blocked: false`。

当前最高风险是：`new` 与 `Reflect.construct` 的参数归一化口径不一致。`Reflect.construct` 已对参数数组做解析/不可还原 fail closed，但 `new` 路径没有同等处理，后续 spread/rest 形态会继续形成绕过面。

## 三、涉及文件

允许修改：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J29_NewExpressionSpread参数归一化门禁整改证据.md`

禁止修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/**/TASK-006*`
- `.pytest-postgresql-*.xml`、coverage、dist、node_modules 等运行生成物

## 四、实现要求

### 4.1 建立统一 invocation arguments descriptor

必须新增或改造参数归一化逻辑，使以下入口都先生成统一 invocation arguments descriptor：

1. `new Ctor(arg1, arg2)`
2. `new Ctor(...args)`
3. `new Ctor(arg1, ...rest)`
4. `Reflect.construct(Ctor, [arg1, arg2])`
5. `Reflect.construct(Ctor, args)`
6. `Reflect.construct(Ctor, [...args])`

要求：

1. descriptor 必须明确 `first_arg_expression`、`options_expression`、`has_spread`、`arg_confidence`、`source_trace`。
2. `arg_confidence` 可为 `static`、`static_url_like`、`unknown`、`unsafe_spread`。
3. `new` 与 `Reflect.construct` 必须复用同一个参数归一化函数，不得维护两套规则。
4. `SpreadElement` 不能直接进入 URL 分类函数；必须先归一或 fail closed。
5. 参数无法静态还原时，在 style-profit surface 内必须 fail closed。

### 4.2 NewExpression spread 必须 fail closed 或静态展开

必须处理以下形式：

```ts
const args = ['/runtime/style-profit-worker.js', { type: 'module' }]
new unknownCtor(...args)

const args = [workerUrl, { type: 'module' }]
new unknownCtor(...args)
```

要求：

1. 简单 `const args = ['literal', options]` 可静态展开时，按展开后的第一参数做 URL-like 判定。
2. 展开后第一参数为 URL-like，且 constructor unknown 时 fail closed。
3. `args` 来源不可静态解析、可变、被重写、来自函数返回、来自条件表达式、含 spread 时 fail closed。
4. `new unknownCtor(...args)` 不得因为第一参数 AST 是 `SpreadElement` 而放行。

### 4.3 混合参数与多 spread 必须 fail closed

必须处理以下形式：

```ts
new unknownCtor('/runtime/style-profit-worker.js', ...rest)
new unknownCtor(...args, { type: 'module' })
new unknownCtor(...prefix, ...suffix)
```

要求：

1. 第一显式参数是 URL-like 时，即使后续有 spread，也必须 fail closed。
2. 第一参数来自 spread 且无法静态展开时，必须 fail closed。
3. 多 spread、条件 spread、函数返回 spread、数组拼接 spread 一律 fail closed，除非能完全静态还原且还原结果安全。
4. 不允许用“未找到第一参数”作为通过条件。

### 4.4 unknown constructor 与 spread URL 判定同口径

要求：

1. `new unknownCtor(...['/runtime/style-profit-worker.js'])` 失败。
2. `new unknownCtor(...['./readonly-worker.ts'])` 失败。
3. `new unknownCtor(...[new URL('./readonly-worker.ts', import.meta.url)])` 失败，因为 constructor unknown。
4. `new unknownCtor(...[workerUrl])` 失败。
5. `new unknownCtor(...[blobWorkerUrl])` 失败。
6. `Reflect.construct(unknownCtor, [...args])` 与 `new unknownCtor(...args)` 同口径。

### 4.5 safe known constructor spread 白名单必须显式

允许保留明确安全的非 Worker 构造器 spread 用法，例如：

```ts
const args = ['2026-04-15']
new Date(...args)
```

要求：

1. 只有 constructor 明确解析为 safe known constructor 时，才允许其 spread 参数通过。
2. safe known constructor 白名单必须集中定义。
3. unknown constructor 不得借用 safe known constructor 的 spread 放行规则。
4. `new URL(...args)` 只在 constructor 明确为 `URL` 且参数可静态验证时允许；不得被误判为 Worker 构造或 unknown constructor 放行。

## 五、必须新增反向测试

至少新增以下反向测试，每条必须断言门禁失败：

1. `const args = ['/runtime/style-profit-worker.js', { type: 'module' }]; new unknownCtor(...args)`
2. `const args = ['./readonly-worker.ts', { type: 'module' }]; new unknownCtor(...args)`
3. `const args = [workerUrl, { type: 'module' }]; new unknownCtor(...args)`
4. `const args = [blobWorkerUrl, { type: 'module' }]; new unknownCtor(...args)`，其中 `blobWorkerUrl` 为 Blob URL 标记变量
5. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new unknownCtor(...args)`
6. `new unknownCtor(...['/runtime/style-profit-worker.js', { type: 'module' }])`
7. `new unknownCtor('/runtime/style-profit-worker.js', ...rest)`
8. `new unknownCtor(...args, { type: 'module' })`，其中 `args` 不可静态还原
9. `new unknownCtor(...getArgs())`
10. `new unknownCtor(...(condition ? safeArgs : unsafeArgs))`
11. `new unknownCtor(...[...args])`
12. `new (getWorker())(...['/runtime/style-profit-worker.js', { type: 'module' }])`
13. `Reflect.construct(unknownCtor, [...args])`，其中 `args` 不可静态还原
14. `Reflect.construct(unknownCtor, [['/runtime/style-profit-worker.js'][0]])`
15. `Reflect.construct(getWorker(), [...['/runtime/style-profit-worker.js', { type: 'module' }]])`
16. `new unknownCtor(...[])` 如 constructor unknown 且无法证明安全用途，必须 fail closed 或由明确安全白名单证明

## 六、必须保留成功用例

至少保留或新增以下成功 fixture：

1. `new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
2. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new Worker(...args)`
3. `const W = Worker; const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new W(...args)`
4. `Reflect.construct(Worker, [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }])`
5. `const dateArgs = ['2026-04-15']; new Date(...dateArgs)`
6. `new Error('readonly message')`
7. `const urlArgs = ['./readonly-worker.ts', import.meta.url]; new URL(...urlArgs)` 不被误杀为 Worker 构造。

## 七、必须保留回归测试

不得删除、跳过、降级 TASK-005H 到 TASK-005J28 的既有测试。尤其必须保留：

- 第 131 份到第 147 份所有审计绕过样例。
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

- 第 147 份审计列出的 `new unknownCtor(...args)` spread 绕过被拦截。
- `NewExpression` 与 `Reflect.construct` 复用同一套参数归一化逻辑。
- `SpreadElement` 不再直接进入 URL 分类函数。
- 参数不可静态还原时，在 style-profit surface 内 fail closed。
- unknown constructor 不再通过 spread/rest/数组中转放行 URL-like 参数。
- safe known constructor spread 白名单集中、明确、可测试。
- 静态本地 Worker 成功用例不被误杀。
- TASK-005J13-J28 已关闭的绕过不回潮。
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
- `TASK-005J29_NewExpressionSpread参数归一化门禁整改证据.md`
- 验证命令摘要
- 禁改边界扫描摘要
