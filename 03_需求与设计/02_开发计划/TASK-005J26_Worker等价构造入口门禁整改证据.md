# TASK-005J26 Worker 等价构造入口门禁整改证据

## 1. 变更范围

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

未修改：`/07_后端/**`、`/.github/**`、`/02_源码/**`、`TASK-006*`。

## 2. 核心实现说明

### 2.1 Worker constructor descriptor 统一化

在 `check-style-profit-contracts.mjs` 中将 Worker 构造器解析统一为 descriptor：

- `constructorName`（`Worker` / `SharedWorker`）
- `boundArgs`（支持 `Worker.bind(...)` 预绑定参数）
- `unresolved`（无法静态确认时 fail closed）

覆盖入口：

- `new Worker(...)`
- `new Alias(...)`
- `new (Worker.bind(...))(... )`
- `new BoundWorker(... )`
- `Reflect.construct(WorkerOrAlias, argsArray)` 及其别名/解构/括号成员等价调用

### 2.2 Reflect.construct 归一校验

新增 `Reflect.construct` 方法识别，并在动态模块加载检查中接入统一调用归一流程：

- 支持 `Reflect.construct`、`const rc = Reflect.construct`、`const { construct } = Reflect`、`Reflect['construct']`
- 对第二参数数组执行静态还原：
  - 数组字面量可解析则继续
  - 非数组字面量、`spread`、无法静态还原则 `fail closed`
- 构造器可解析为 Worker/SharedWorker 时，URL 校验复用同一套 `classifyWorkerSourceArgument`

### 2.3 bind 预绑定 URL 生效

`Worker.bind(null, preboundUrl)` 场景下，构造实参按 `boundArgs + runtimeArgs` 归一后校验 URL，避免仅检查 `new` 调用参数导致绕过。

### 2.4 运行时数组参数映射

新增数组字面量变量映射（`arrayLiteralVariableMap`）用于解析：

- `const args = ['data:...']; Reflect.construct(Worker, args)`
- `const args = [workerUrl]; Reflect.construct(Worker, args)`

不可静态还原时 fail closed。

## 3. 新增/强化测试

`test-style-profit-contracts.mjs` 新增 J26 反向用例（节选）：

1. `new (Worker.bind(null))('data:...')`
2. `new (SharedWorker.bind(null))('data:...')`
3. `const BW = Worker.bind(null); new BW('data:...')`
4. `const BW = Worker.bind(null, 'data:...'); new BW(...)`
5. `Reflect.construct(Worker, ['data:...'])`
6. `Reflect.construct(SharedWorker, ['data:...'])`
7. `const rc = Reflect.construct; rc(Worker, ['data:...'])`
8. `const { construct } = Reflect; construct(Worker, ['data:...'])`
9. `Reflect['construct'](Worker, ['data:...'])`
10. `Reflect.construct(Worker, [workerUrl])`（不可静态证明）
11. `const args = ['data:...']; Reflect.construct(Worker, args)`
12. `Reflect.construct(Worker, [...args])`（spread）
13. `Reflect.construct(unknownCtor, ['data:...'])`
14. `Reflect.construct(Worker, ['data:...'], SafeCtor)`

同时把以下成功用例加入基础通过夹具，确保不误杀：

- `const BW = Worker.bind(null); new BW(new URL('./readonly-worker.ts', import.meta.url), { type: 'module' })`
- `Reflect.construct(Worker, [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }])`
- `Reflect.construct(Date, [])`

## 4. 验证命令与结果

### 前端

- `npm run check:style-profit-contracts`：通过
- `npm run test:style-profit-contracts`：通过（`scenarios=324`）
- `npm run verify`：通过（含 production/style-profit contract、typecheck、build）
- `npm audit --audit-level=high`：`found 0 vulnerabilities`

### 后端只读回归

- `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`：`8 passed`
- `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`：通过

## 5. 禁改边界核对

本次仅修改前端契约脚本与测试脚本，并新增本证据文件；未改后端业务代码、未改 workflow、未触碰 `TASK-006`。

## 6. 提交信息

- 代码提交：`3d15229`（`fix: harden worker equivalent constructor sinks`）
- 证据提交：`1fd3f0f`（`docs: add task 005j26 worker sink evidence`）
