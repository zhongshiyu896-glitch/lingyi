# TASK-005J36 同步数组迭代方法 Bind 与 CallCall 门禁整改证据

## 1. 任务信息
- 任务编号：TASK-005J36
- 任务目标：将同步数组迭代方法 `direct/call/apply/Reflect.apply/bind/call.call` 统一归一到同一条 iteration invocation descriptor 路径，避免 bind 与 call.call 中转绕过。
- 本次仅整改前端门禁脚本与测试脚本；未进入 TASK-006。

## 2. 修改文件
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J36_同步数组迭代方法Bind与CallCall门禁整改证据.md`

## 3. 实现说明（J36）

### 3.1 统一 IterationInvocationDescriptor
在 `check-style-profit-contracts.mjs` 中重构并扩展了数组迭代调用归一逻辑，统一输出 descriptor（包括 `methodName/iterableExpression/callbackExpression/initialValueExpression/argumentMode/boundArgs/laterArgs`），并让以下入口共用一套解析和污染传播逻辑：
- `direct`
- `.call`
- `.apply`
- `Reflect.apply`
- `.bind`
- `call.call`

### 3.2 bind 预绑定与调用阶段参数合并
新增 bind 归一处理能力：
- 识别 `Array.prototype.<method>.bind(thisArg, ...boundArgs)` 形成的调用别名。
- 在调用 `boundFn(...laterArgs)` 时合并 `boundArgs + laterArgs` 再映射回统一 descriptor。
- `reduce/reduceRight` 继续按 callback 第 2 个参数作为 current item；`findIndex/flatMap/findLast/findLastIndex` 继续按 callback 第 1 个参数作为 current item。

### 3.3 call.call 中转归一
新增 call.call 解析能力：
- 识别 `Function.prototype.call.call(Array.prototype.<method>, thisArg, ...args)`。
- 识别 `Array.prototype.<method>.call.call(Array.prototype.<method>, thisArg, ...args)`。
- 统一还原为迭代方法调用 descriptor 后执行既有 callback 副作用传播和数组状态污染判定。

### 3.4 解析失败 fail closed
对 bind/call.call 目标、thisArg、boundArgs、laterArgs 或参数数组无法静态还原的场景，按 style-profit surface 既有策略 fail closed（在存在 tracked Worker args 风险时阻断）。

## 4. 新增/覆盖测试（J36）
在 `scripts/test-style-profit-contracts.mjs` 新增并通过以下反向测试（示例）：
- `Array.prototype.reduce.bind([[args]])(...)`
- `Array.prototype.reduce.bind([[args]], callback, 0)()`
- `Array.prototype.reduce.bind([[args]], callback)` + later initialValue
- `reduceRight.bind / findIndex.bind / flatMap.bind`
- `Function.prototype.call.call(Array.prototype.reduce, ...)`
- `Array.prototype.reduce.call.call(Array.prototype.reduce, ...)`
- `Function.prototype.call.call(Array.prototype.findIndex, ...)`
- `Function.prototype.call.call(Array.prototype.flatMap, ...)`
- bind unresolved iterable / dynamic bound args / call alias unresolved 的 fail closed 场景
- bind 污染后进入 `new unknownCtor(...args)` 与 `Reflect.construct(Worker, args)` 场景

同时保留并通过既有只读合法场景（包含 read-only callback 场景）。

## 5. 验证命令与结果

### 5.1 前端
在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：
- `npm run check:style-profit-contracts`：通过
- `npm run test:style-profit-contracts`：通过（`All style-profit contract fixture tests passed. scenarios=475`）
- `npm run verify`：通过（含 `check + test + typecheck + build`）
- `npm audit --audit-level=high`：`found 0 vulnerabilities`

### 5.2 后端定向回归
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：
- `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
  - 结果：`34 passed, 1 warning in 0.86s`
- `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
  - 结果：通过（无错误输出）

## 6. 扫描结果

### 6.1 J36 覆盖扫描（脚本内命中）
已命中 bind/call.call/descriptor 关键实现与测试条目（含 `argumentMode: 'bind'`、`argumentMode: 'call_call'`、J36 新增 fixture 名称）。

### 6.2 业务禁线扫描
对前端 `src` 执行业务禁线关键词扫描：未命中新增违规创建/生成/重算入口（命令返回无匹配）。

## 7. 禁改边界与风险控制
- 未修改后端业务代码、`.github`、`02_源码`、`TASK-006*`。
- 未开放 `POST /api/reports/style-profit/snapshots` 入口。
- 未新增 `createStyleProfitSnapshot/snapshot_create/idempotency_key` 创建链路。
- 未引入新的第三方 parser 依赖。

## 8. 当前提交信息
- 当前 HEAD：`5db1f1a8813f7821f9aefebc80f7d5bbc9e27057`
- 本次工作区状态：已完成代码与测试整改，尚未在本步骤执行提交（commit hash 暂无新增）。

