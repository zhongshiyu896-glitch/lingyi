# TASK-005J29 NewExpression Spread 参数归一化门禁整改证据

## 1. 变更范围

本次仅修改以下文件：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J29_NewExpressionSpread参数归一化门禁整改证据.md`

未修改：`/07_后端/**`、`/.github/**`、`/02_源码/**`、`TASK-006*`、`.pytest-postgresql-*.xml`。

## 2. 核心实现说明

### 2.1 NewExpression 与 Reflect.construct 参数归一化统一

在 `check-style-profit-contracts.mjs` 新增统一参数归一化流程：

- `resolveRuntimeInvocationArgumentsFromNodes(...)`
- `resolveRuntimeSpreadArgumentElements(...)`
- `resolveRuntimeInvocationArgConfidence(...)`

并让以下入口复用同一套参数解析口径：

1. `new Ctor(arg1, arg2)`
2. `new Ctor(...args)`
3. `new Ctor(arg1, ...rest)`
4. `Reflect.construct(Ctor, [arg1, arg2])`
5. `Reflect.construct(Ctor, args)`
6. `Reflect.construct(Ctor, [...args])`

### 2.2 invocation descriptor 字段补齐

`constructor invocation descriptor` 已统一携带：

- `url_expression`
- `options_expression`
- `has_spread`
- `arg_confidence`（`static` / `static_url_like` / `unknown` / `unsafe_spread`）
- `source_trace`

`new` 与 `Reflect.construct` 均走 `applyConstructorInvocationDescriptor(...)`，不再分叉处理 spread。

### 2.3 SpreadElement 不再直接进入 URL 分类

以前 `new unknownCtor(...args)` 会把 `SpreadElement` 直接传入 unknown URL 分类，导致漏判。

本次改为：

- 可静态展开的 spread（字面量数组、可追踪数组变量）先展开再判定。
- 不可静态还原（动态变量、函数返回、条件表达式、多层 spread 不可还原）直接 `unresolved_args -> fail closed`。

### 2.4 unknown constructor + spread URL-like 严格阻断

已收口以下场景：

- `new unknownCtor(...['/runtime/style-profit-worker.js', { type: 'module' }])`
- `new unknownCtor(...args)`（args 为 URL-like）
- `new unknownCtor('/runtime/style-profit-worker.js', ...rest)`
- `new unknownCtor(...[])` 在 unknown 场景下 fail closed
- `Reflect.construct(unknownCtor, [...args])` 与 `new unknownCtor(...args)` 同口径

### 2.5 safe known constructor spread 白名单维持

保持 safe known constructor（`Date`/`URL`/`Error` 等）不误杀：

- `new Date(...dateArgs)` 通过
- `new URL(...urlArgs)` 通过

unknown constructor 不得借用该白名单。

## 3. 新增/强化测试（节选）

`test-style-profit-contracts.mjs` 新增并通过 J29 关键失败用例：

1. `const args = ['/runtime/style-profit-worker.js', { type: 'module' }]; new unknownCtor(...args)`
2. `const args = ['./readonly-worker.ts', { type: 'module' }]; new unknownCtor(...args)`
3. `const args = [workerUrl, { type: 'module' }]; new unknownCtor(...args)`
4. `const args = [blobWorkerUrl, { type: 'module' }]; new unknownCtor(...args)`
5. `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new unknownCtor(...args)`
6. `new unknownCtor(...['/runtime/style-profit-worker.js', { type: 'module' }])`
7. `new unknownCtor('/runtime/style-profit-worker.js', ...rest)`
8. `new unknownCtor(...args, { type: 'module' })`（args 不可静态还原）
9. `new unknownCtor(...getArgs())`
10. `new unknownCtor(...(condition ? safeArgs : unsafeArgs))`
11. `new unknownCtor(...[...args])`
12. `new (getWorker())(...['/runtime/style-profit-worker.js', { type: 'module' }])`
13. `Reflect.construct(unknownCtor, [...args])`（args 不可静态还原）
14. `Reflect.construct(unknownCtor, [['/runtime/style-profit-worker.js'][0]])`
15. `Reflect.construct(getWorker(), [...['/runtime/style-profit-worker.js', { type: 'module' }]])`
16. `new unknownCtor(...[])`（unknown 场景 fail closed）

同时保留成功 fixture：

- `const args = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new Worker(...args)`
- `const W = Worker; new W(...args)`
- `const dateArgs = ['2026-04-15']; new Date(...dateArgs)`
- `const urlArgs = ['./readonly-worker.ts', import.meta.url]; new URL(...urlArgs)`

## 4. 验证命令与结果

### 前端

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

1. `npm run check:style-profit-contracts`：通过（`Scanned files: 24`）
2. `npm run test:style-profit-contracts`：通过（`All style-profit contract fixture tests passed. scenarios=369`）
3. `npm run verify`：通过（production/style-profit contracts、typecheck、build 全通过）
4. `npm audit --audit-level=high`：通过（`found 0 vulnerabilities`）

### 后端只读回归

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`：`8 passed, 1 warning`
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`：通过

## 5. 禁改边界扫描摘要

- 本次代码提交仅包含前端契约脚本与测试脚本。
- 未触碰后端代码、workflow、`02_源码`、`TASK-006*`。
- `.pytest-postgresql-*.xml` 仍为运行产物，未纳入提交。

## 6. 提交信息

- 代码提交：`461f151`（`fix: normalize spread args for style profit constructor gate`）
- 文档提交：见本证据文件所在 docs 提交。
