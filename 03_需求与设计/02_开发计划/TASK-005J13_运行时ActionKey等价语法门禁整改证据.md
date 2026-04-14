# TASK-005J13 运行时 ActionKey 等价语法门禁整改证据

## 1. 基本信息
- 任务编号：`TASK-005J13`
- 任务名称：运行时 ActionKey 等价语法门禁整改
- 执行日期：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`6b3f7e2`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J13_运行时ActionKey等价语法门禁整改证据.md`

## 3. 实现摘要

### 3.1 等价语法调用识别
在 `check-style-profit-contracts.mjs` 中新增统一 runtime 调用解析，覆盖：
- `Object.defineProperty(...)`
- `Object['defineProperty'](...)`
- `Object["defineProperty"](...)`
- `Object.defineProperties(...)`
- `Object['defineProperties'](...)`
- `Object.assign(...)`
- `Object['assign'](...)`
- `Reflect.set(...)`
- `Reflect['set'](...)`

### 3.2 本地别名调用识别
新增别名上下文收集，识别并拦截：
- `const defineProperty = Object.defineProperty; defineProperty(...)`
- `const assign = Object.assign; assign(...)`
- `const set = Reflect.set; set(...)`

### 3.3 Object.assign 变量 source 追踪
新增 `Object.assign` source 分析：
- 支持同文件简单对象字面量变量追踪：`const action = { onClick: ... }`。
- `Object.assign(item, base, action, extra)` 对每个 source 单独检查。
- source 为动态、无法解析、含 spread 时，在 style-profit surface 内 fail closed。

### 3.4 fail closed 边界
- 运行时显式 action key 注入（`onClick/handler/command/submit/...`）统一拦截。
- 运行时 dynamic/unknown key 注入继续拦截。
- 非 action 字段运行时写入不误杀（例如 `item.disabled = true`）。
- 纯读取动态 key 不误杀（例如 `const v = item[ACTION_KEY]`，且不构成写入/入口）。

## 4. 新增反向测试（J13）
`test-style-profit-contracts.mjs` 新增并通过以下反向用例：
1. `Object['defineProperty'](item, 'onClick', { value: openHelp })`
2. `Reflect['set'](item, 'onClick', openHelp)`
3. `Object['assign'](item, { onClick: openHelp })`
4. `const defineProperty = Object.defineProperty; defineProperty(item, 'onClick', ...)`
5. `const assign = Object.assign; assign(item, { onClick: openHelp })`
6. `const set = Reflect.set; set(item, 'onClick', openHelp)`
7. `const action = { onClick: openHelp }; Object.assign(item, action)`
8. `const action = { handler: openHelp }; Object['assign'](item, action)`
9. `Object.assign(item, base, action, extra)` 中 `action` 含 action key
10. `Object.assign(item, actionSource)`（无法解析 source）fail closed

## 5. 验证命令与结果

### 5.1 前端
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=106`）

3. `npm run verify`
- 结果：通过（包含 production/style-profit contract、typecheck、build）

4. `npm audit --audit-level=high`
- 结果：通过（`found 0 vulnerabilities`）

### 5.2 后端只读回归（未修改后端代码）
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`
- 结果：通过（`8 passed, 1 warning`）

2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

## 6. 扫描结果

### 6.1 等价语法与别名覆盖扫描
命令：
- `rg -n "Object\\['defineProperty'\\]|Object\\[\"defineProperty\"\\]|Object\\['assign'\\]|Object\\[\"assign\"\\]|Reflect\\['set'\\]|Reflect\\[\"set\"\\]|defineProperty\\s*=\\s*Object\\.defineProperty|assign\\s*=\\s*Object\\.assign|set\\s*=\\s*Reflect\\.set|Object\\.assign\\(item, action\\)|Object\\.assign\\(item, base, action, extra\\)|actionSource|runtime explicit action-key injection" scripts/check-style-profit-contracts.mjs scripts/test-style-profit-contracts.mjs`

结果：命中 J13 新增实现与反向用例，符合预期。

### 6.2 业务禁线扫描
命令：
- `rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|...|profitRecalculate" src`

结果：无命中（退出码 1，符合预期）。

## 7. 禁改范围确认
- 未修改：`07_后端/**`
- 未修改：`.github/**`
- 未修改：`02_源码/**`
- 未修改：`TASK-006*`
- 未提交：`.pytest-postgresql-*.xml`、`dist`、`coverage`、`node_modules`

## 8. 提交信息
- commit：`<待回填>`
- message：`fix: close style profit runtime action-key syntax gaps`

## 9. 结论
TASK-005J13 已完成：
- 运行时显式 action key 注入的等价语法（括号访问、别名调用、变量 source 合并、多 source 合并）已纳入门禁并 fail closed。
- 无法解析或含 spread 的 `Object.assign` source 在 style-profit surface 内 fail closed。
- 非 action 字段写入与纯读取场景不误杀。
- 前端契约验证、全量 verify、后端只读回归全部通过。
- 未开放创建快照入口，未进入 `TASK-006`。
