# TASK-005J17 Runtime Mutator 中转调用门禁整改证据

## 1. 基本信息
- 任务编号：`TASK-005J17`
- 任务名称：Runtime Mutator 中转调用门禁整改
- 执行日期：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`1d5359f`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J17_RuntimeMutator中转调用门禁整改证据.md`

## 3. 整改实现

### 3.1 callee 归一化（逗号表达式）
- 新增 `normalizeRuntimeCalleeExpression()`。
- 对 `CallExpression.callee` 递归剥离括号并处理 `CommaToken`，始终取最后表达式。
- 关闭绕过：
  - `;(0, Object.defineProperty)(...)`
  - `;(0, Object.assign)(...)`
  - `;(0, Reflect.set)(...)`

### 3.2 条件表达式命名空间解析与 fail closed
- `resolveRuntimeNamespaceFromExpression()` 新增 `ConditionalExpression` 支持：仅当两分支都可静态解析且一致时才映射。
- 新增 `runtimeUnknownNamespaceAliasMap`：条件分支不可一致还原时记录为不可信命名空间别名。
- 调用点使用该别名访问 mutator 成员时 fail closed。
- 支持条件分支来源：`Object/Reflect/globalThis.Object/window.Object/globalThis.Reflect/window.Reflect`。

### 3.3 数组容器中转调用解析
- 新增 `runtimeArrayMethodContainerMap` 和 `analyzeRuntimeMutatorArrayLiteral()`。
- 支持同文件简单数组字面量到源 mutator 的索引映射。
- 数字字面量索引按位置解析；索引越界/动态索引/数组含 spread 或无法还原时 fail closed。

### 3.4 对象容器中转调用解析
- 新增 `runtimeObjectMethodContainerMap` 和 `analyzeRuntimeMutatorObjectLiteral()`。
- 支持点访问和字符串字面量括号访问映射到源 mutator。
- 计算属性、spread、动态属性或无法还原时 fail closed。

### 3.5 统一 runtime sink 解析上下文
- `resolveRuntimeMethodFromExpression()` 与 `resolveRuntimeCallDescriptor()` 扩展为读取：
  - 命名空间别名
  - 未可信命名空间别名
  - 数组容器映射
  - 对象容器映射
- 对中转调用不可静态确认路径，统一返回 unresolved 并触发 fail closed。

## 4. 新增反向测试（J17）
新增并通过以下 14 条：
1. `;(0, Object.defineProperty)(item, 'onClick', { value: openHelp })`
2. `;(0, Object.assign)(item, { onClick: openHelp })`
3. `;(0, Reflect.set)(item, 'onClick', openHelp)`
4. `const Obj = true ? Object : Object; Obj.defineProperty(item, 'onClick', ...)`
5. `const R = condition ? Reflect : Reflect; R.set(item, 'onClick', openHelp)`
6. `const Obj = condition ? globalThis.Object : window.Object; Obj.assign(item, { onClick: openHelp })`
7. `const mutators = [Object.defineProperty]; mutators[0](item, 'onClick', ...)`
8. `const mutators = [Object.assign, Reflect.set]; mutators[1](item, 'onClick', openHelp)`
9. `const mutators = [Object.defineProperty]; mutators[index](...)` fail closed
10. `const mutators = [Object.defineProperty, ...extra]; mutators[0](...)` fail closed
11. `const mutators = { dp: Object.defineProperty }; mutators.dp(...)`
12. `const mutators = { assign: Object.assign }; mutators['assign'](...)`
13. `const mutators = { set: Reflect.set }; mutators[key](...)` fail closed
14. `const mutators = { dp: Object.defineProperty, ...extra }; mutators.dp(...)` fail closed

## 5. 验证命令与结果

### 5.1 前端
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=163`）

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

### 6.1 J17 覆盖扫描
命令：
- `rg -n "CommaToken|normalizeRuntimeCalleeExpression|ConditionalExpression|runtimeUnknownNamespaceAliasMap|runtimeArrayMethodContainerMap|runtimeObjectMethodContainerMap|..." scripts/check-style-profit-contracts.mjs scripts/test-style-profit-contracts.mjs`

结果：命中 J17 新增实现与反向用例，符合预期。

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
- commit：`<待回填>`
- message：`fix: detect style profit runtime mutator relay calls`

## 9. 结论
`TASK-005J17` 已完成：
- 逗号表达式 callee、条件表达式命名空间、数组容器中转、对象容器中转绕过全部关闭。
- 无法静态还原的中转路径统一 fail closed。
- TASK-005J13/J14/J15/J16 已关闭绕过未回潮。
- 验证全部通过，未开放创建快照入口，未进入 `TASK-006`。
