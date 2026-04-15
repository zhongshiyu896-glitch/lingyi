# TASK-005J28 Unknown Constructor 字符串 URL 严格门禁整改证据

## 1. 变更范围

本次仅修改以下文件：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J28_UnknownConstructor字符串URL严格门禁整改证据.md`

未修改：`/07_后端/**`、`/.github/**`、`/02_源码/**`、`TASK-006*`、`.pytest-postgresql-*.xml`。

## 2. 核心实现说明

### 2.1 unknown constructor 字符串/URL-like 参数严格 fail closed

在 `check-style-profit-contracts.mjs` 的 `classifyUnknownWorkerConstructTargetSourceStrict()` 中收紧规则：

- 过去：unknown constructor 对普通字符串路径（例如 `'./readonly-worker.ts'`）可放行。
- 现在：unknown constructor + URL-like 第一参数一律拦截。

拦截范围包括：

1. 任意静态字符串（本地路径/协议 URL/拼接可折叠字符串）
2. Blob URL 标记变量
3. `new URL('./readonly-worker.ts', import.meta.url)` 表达式（在 unknown ctor 下也拦截）
4. 模板字符串、变量、函数返回、属性访问、元素访问、条件表达式、二元拼接等无法证明安全来源

### 2.2 known Worker 与 unknown constructor 判定同口径

保持 known Worker 规则不变（仅允许 canonical `new URL(..., import.meta.url)` 形式），同时把 unknown constructor 收紧到“不比 known Worker 更宽松”：

- `new Worker('./readonly-worker.ts')`：拦截
- `new unknownCtor('./readonly-worker.ts')`：拦截
- `new Worker('/runtime/style-profit-worker.js')`：拦截
- `new unknownCtor('/runtime/style-profit-worker.js')`：拦截

### 2.3 Reflect.construct unknown 分支同步收紧

`Reflect.construct(unknownCtor, args)` 与 `new unknownCtor(...)` 共用同口径 URL-like 判定：

- 第一参数数组项为字符串路径、变量 URL、模板 URL、函数返回 URL、Blob URL 标记变量、`new URL(...)` 时全部拦截。
- 第三个 `newTarget` 参数不构成豁免。

### 2.4 safe known constructor 白名单集中定义

`runtimeKnownSafeConstructorNameSet` 继续集中管理，并补充了：

- `RegExp`
- `Map`
- `Set`

safe known constructor 仅用于构造器本身识别，不会给 unknown constructor 借白名单放行。

### 2.5 本任务未新增依赖

继续复用现有 `typescript` AST 分析能力，未引入新第三方依赖。

## 3. 新增/强化反向测试（节选）

`test-style-profit-contracts.mjs` 已新增并通过 J28 关键失败用例（均应失败）：

1. `function getWorker(){ if (ready) return Worker; return Worker }; new (getWorker())('/runtime/style-profit-worker.js')`
2. `function getWorker(){ if (ready) return Worker; return Worker }; new (getWorker())('./readonly-worker.ts')`
3. `const getWorker = () => condition ? Worker : unknownCtor; new (getWorker())('/runtime/style-profit-worker.js')`
4. `new unknownCtor('/runtime/style-profit-worker.js', { type: 'module' })`
5. `new unknownCtor('./readonly-worker.ts', { type: 'module' })`
6. `new unknownCtor(workerUrl, { type: 'module' })`
7. `` new unknownCtor(`/runtime/${name}.js`, { type: 'module' }) ``
8. `new unknownCtor(getWorkerUrl(), { type: 'module' })`
9. `new unknownCtor(blobWorkerUrl, { type: 'module' })`（blobWorkerUrl 为 Blob URL 标记变量）
10. `Reflect.construct(unknownCtor, ['/runtime/style-profit-worker.js', { type: 'module' }])`
11. `Reflect.construct(getWorker(), ['/runtime/style-profit-worker.js', { type: 'module' }])`
12. `Reflect.construct(unknownCtor, [workerUrl])`
13. `Reflect.construct(unknownCtor, [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }])`
14. `Reflect.construct(unknownCtor, ['/runtime/style-profit-worker.js'], SafeCtor)`

同时补了 known Worker 非 canonical 字符串路径回归失败用例：

- `new Worker('./readonly-worker.ts', { type: 'module' })`
- `new Worker('/runtime/style-profit-worker.js', { type: 'module' })`

## 4. 保留成功 fixture（节选）

以下成功场景保持通过：

1. `new Worker(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
2. `const W = Worker; new W(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
3. `const getWorker = () => Worker; new (getWorker())(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
4. `Reflect.construct(Worker, [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }])`
5. `new Date('2026-04-15')`
6. `new URL('./readonly-worker.ts', import.meta.url)`
7. `new Error('readonly message')`

## 5. 验证命令与结果

### 前端

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

1. `npm run check:style-profit-contracts`：通过（`Scanned files: 24`）
2. `npm run test:style-profit-contracts`：通过（`All style-profit contract fixture tests passed. scenarios=353`）
3. `npm run verify`：通过（production/style-profit contracts、typecheck、build 全通过）
4. `npm audit --audit-level=high`：通过（`found 0 vulnerabilities`）

### 后端只读回归

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`：`8 passed, 1 warning`
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`：通过

## 6. 禁改边界扫描摘要

- 本次代码提交仅包含前端契约脚本与测试脚本。
- 未触碰后端代码、workflow、`02_源码`、`TASK-006*`。
- `.pytest-postgresql-*.xml` 仍为运行产物，未纳入提交。

## 7. 提交信息

- 代码提交：`9fd4be4`（`fix: harden unknown constructor worker url gate`）
- 文档提交：`f51ecf7`（`docs: add task 005j28 strict gate evidence`）
