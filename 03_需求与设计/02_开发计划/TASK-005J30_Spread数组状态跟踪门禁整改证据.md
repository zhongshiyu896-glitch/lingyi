# TASK-005J30 Spread 数组状态跟踪门禁整改证据

## 1. 变更范围

本次仅修改以下文件：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J30_Spread数组状态跟踪门禁整改证据.md`

未修改：`/07_后端/**`、`/.github/**`、`/02_源码/**`、`TASK-006*`、`.pytest-postgresql-*.xml`。

## 2. 核心实现说明

### 2.1 数组缓存升级为状态跟踪

`collectRuntimeAnalysisContext(...)` 新增数组状态模型（并保留原 `arrayLiteralVariableMap` 兼容回退）：

- `runtimeArrayStateMap`
- `runtimeArrayAliasMap`
- 数组状态字段：
  - `array_id`
  - `initial_elements`
  - `aliases`
  - `status`（`clean | tainted | escaped | unknown`）
  - `mutation_reasons`
  - `mutation_events`
  - `declaration_position`
  - `last_safe_position`

并新增别名绑定/解绑、状态注册、状态污染、逃逸标记等辅助函数，避免继续只信任“声明时数组字面量快照”。

### 2.2 污染规则落地

以下行为会将数组标记为 `tainted/unknown/escaped`：

1. 元素写入：`args[0] = ...`、`args['0'] = ...`
2. `length` 写入：`args.length = ...`
3. mutating method：`push/pop/shift/unshift/splice/sort/reverse/fill/copyWithin`
4. 别名链写入：`const alias = args; alias[0] = ...`
5. `Array.prototype.splice.call(args, ...)` 等 call/apply 变体
6. 动态方法名调用：`args[methodName](...)` -> `unknown`
7. 逃逸：作为调用参数传递、赋值到对象属性、`return args`、`export` 场景

### 2.3 使用点按状态判定，无法证明安全即 fail closed

`resolveRuntimeSpreadArgumentElements(...)` 与 `resolveRuntimeArgumentArrayElements(...)` 统一接入数组状态读取：

- 使用点状态 `clean`：允许静态展开数组元素
- 使用点状态 `tainted/escaped/unknown`：返回 `unresolved`，并由动态模块加载门禁 fail closed

这使 `new Ctor(...args)` 与 `Reflect.construct(Ctor, args)` 都依赖同一个数组状态模型，不再出现一边收紧、一边漏判。

## 3. J30 新增反向测试（节选）

`test-style-profit-contracts.mjs` 新增并通过以下 J30 场景（均预期失败）：

1. `args[0]` 写入后 `new Worker(...args)`
2. `args['0']` 写入后 `new Worker(...args)`
3. 别名写入 `alias[0]` 后 `new Worker(...args)`
4. `alias.splice(...)` 后 `new Worker(...args)`
5. `args.splice(...)` 后 `new Worker(...args)`
6. `args.unshift(...)` 后 `new Worker(...args)`
7. `args.push(...)` 后 `new Worker(...args)`
8. `args.reverse()` 后 `new Worker(...args)`
9. `args.fill(...)` 后 `new Worker(...args)`
10. `mutate(args)` 逃逸后 `new Worker(...args)`
11. `store.args = args` 逃逸后 `new Worker(...args)`
12. `Array.prototype.splice.call(args, ...)` 后 `new Worker(...args)`
13. `args[methodName](...)` 后 `new Worker(...args)`
14. `args[0]` 写入后 `Reflect.construct(Worker, args)`
15. 别名写入后 `new unknownCtor(...args)`
16. `args = getArgs()` 重绑定后 `new Worker(...args)`

同时保持成功 fixture：

- `const spreadWorkerArgs = [new URL('./readonly-worker.ts', import.meta.url), { type: 'module' }]; new Worker(...spreadWorkerArgs)`
- `const spreadWorkerAlias = spreadWorkerArgs; new Worker(...spreadWorkerAlias)`（未写入、未逃逸）
- `Reflect.construct(Worker, spreadWorkerArgs)`（clean 数组）
- `new Date(...dateArgs)`
- `new URL(...urlArgs)`

## 4. 验证命令与结果

### 前端

在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

1. `npm run check:style-profit-contracts`：通过（`Style-profit contract check passed. Scanned files: 24`）
2. `npm run test:style-profit-contracts`：通过（`All style-profit contract fixture tests passed. scenarios=385`）
3. `npm run verify`：通过（production/style-profit contracts、typecheck、build 全通过）
4. `npm audit --audit-level=high`：通过（`found 0 vulnerabilities`）

### 后端只读回归

在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`：`8 passed, 1 warning`
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`：通过

## 5. 禁改边界扫描摘要

- 提交范围仅前端契约脚本、测试脚本与 J30 证据文档。
- 未触碰后端、workflow、`02_源码`、`TASK-006*`。
- `.pytest-postgresql-*.xml` 仍为运行产物，未纳入提交。

## 6. 提交信息

- 代码提交：5b4acfe（fix: track spread array state in style profit gate）
- 证据提交：本文件所在提交（docs）
