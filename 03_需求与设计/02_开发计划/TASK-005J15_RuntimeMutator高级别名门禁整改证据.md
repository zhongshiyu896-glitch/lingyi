# TASK-005J15 Runtime Mutator 高级别名门禁整改证据

## 1. 基本信息
- 任务编号：`TASK-005J15`
- 任务名称：Runtime Mutator 高级别名门禁整改
- 执行日期：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`ea6d94a`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J15_RuntimeMutator高级别名门禁整改证据.md`

## 3. 整改实现

### 3.1 赋值式解构别名识别
新增赋值表达式解构解析，支持：
- `let defineProperty; ({ defineProperty } = Object)`
- `let dp; ({ defineProperty: dp } = Object)`
- `let assign; ({ assign } = Object)`
- `let set; ({ set } = Reflect)`

解构结果统一映射到 runtime mutator：
- `Object.defineProperty`
- `Object.defineProperties`
- `Object.assign`
- `Reflect.set`

### 3.2 bind/call/apply 等价调用识别
新增 runtime 调用描述与参数归一化：
- 识别 `Object.defineProperty.bind(Object)`、`Object.assign.bind(Object)`、`Reflect.set.bind(Reflect)` 别名。
- 识别 `.call()` / `.apply()` 并恢复原 API 参数位。
- `.call()` 自动剥离第一个 `thisArg`。
- `.apply()` 第二参数必须是数组字面量；不可还原时在 style-profit surface 内 fail closed。

### 3.3 globalThis/window 命名空间识别
`resolveRuntimeNamespaceFromExpression` 扩展支持：
- `globalThis.Object` / `window.Object`
- `globalThis.Reflect` / `window.Reflect`
- 以及基于上述来源创建的命名空间别名（如 `const Obj = globalThis.Object`、`const R = window.Reflect`）。

### 3.4 既有门禁保持
未回退 TASK-005H ~ TASK-005J14：
- 动态 computed key / unknown key fail closed
- 运行时动态 key 注入 fail closed
- 运行时显式 key 注入 fail closed
- 解构别名、命名空间别名、变量 source / 多 source 检测保持有效

## 4. 新增反向测试（J15）
新增并通过以下 18 条反向测试：
1. `let defineProperty; ({ defineProperty } = Object); defineProperty(item, 'onClick', ...)`
2. `let dp; ({ defineProperty: dp } = Object); dp(item, 'onClick', ...)`
3. `let assign; ({ assign } = Object); assign(item, { onClick: openHelp })`
4. `let set; ({ set } = Reflect); set(item, 'onClick', openHelp)`
5. `const defineProperty = Object.defineProperty.bind(Object); defineProperty(...)`
6. `const assign = Object.assign.bind(Object); assign(...)`
7. `const set = Reflect.set.bind(Reflect); set(...)`
8. `Object.defineProperty.call(Object, item, 'onClick', ...)`
9. `Object.defineProperty.apply(Object, [item, 'onClick', ...])`
10. `Object.assign.call(Object, item, { onClick: ... })`
11. `Object.assign.apply(Object, [item, { onClick: ... }])`
12. `Reflect.set.call(Reflect, item, 'onClick', ...)`
13. `Reflect.set.apply(Reflect, [item, 'onClick', ...])`
14. `const Obj = globalThis.Object; Obj.defineProperty(...)`
15. `const R = window.Reflect; R.set(...)`
16. `globalThis.Object.assign(item, { onClick: ... })`
17. `window.Reflect.set(item, 'onClick', ...)`
18. `.apply()` 非数组字面量参数 fail closed（`Object.defineProperty.apply(Object, argsTuple)`）

## 5. 验证命令与结果

### 5.1 前端
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=135`）

3. `npm run verify`
- 结果：通过（production/style-profit contract + typecheck + build 全部通过）

4. `npm audit --audit-level=high`
- 结果：通过（`found 0 vulnerabilities`）

### 5.2 后端只读回归（未改后端）
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`
- 结果：通过（`8 passed, 1 warning`）

2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

## 6. 扫描结果

### 6.1 J15 覆盖扫描
命令：
- `rg -n "ObjectBindingPattern|resolveRuntimeNamespaceFromExpression|runtimeNamespaceAliasMap|bind\(|\.call\(|\.apply\(|globalThis\.Object|window\.Reflect|assignment-destructure|runtime apply with non-array args" scripts/check-style-profit-contracts.mjs scripts/test-style-profit-contracts.mjs`

结果：命中 J15 新增实现和反向用例，符合预期。

### 6.2 业务禁线扫描
命令：
- `rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|...|profitRecalculate" src`

结果：无命中（退出码 1，符合预期）。

## 7. 禁改范围确认
- 未修改：`07_后端/**`
- 未修改：`.github/**`
- 未修改：`02_源码/**`
- 未修改：`TASK-006*`
- 未提交：`.pytest-postgresql-*.xml`、`coverage`、`dist`、`node_modules`

## 8. 提交信息
- commit：`1aebc16a4df0c0af47946b9feb06c1b673bfeb1d`
- message：`fix: detect advanced runtime mutator aliases`

## 9. 结论
`TASK-005J15` 已完成：
- 赋值式解构、bind/call/apply、globalThis/window 命名空间绕过均被门禁拦截。
- `.apply()` 参数不可还原路径按 fail closed 处理。
- TASK-005J13/J14 已关闭绕过未回潮。
- 验证全部通过，未开放创建快照入口，未进入 `TASK-006`。
