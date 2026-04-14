# TASK-005J16 Runtime Mutator Sink 变体门禁整改证据

## 1. 基本信息
- 任务编号：`TASK-005J16`
- 任务名称：Runtime Mutator Sink 变体门禁整改
- 执行日期：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`3e70b48`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J16_RuntimeMutatorSink变体门禁整改证据.md`

## 3. 整改实现

### 3.1 Runtime sink 变体识别
- 新增 `Reflect.apply` sink 解析：
  - `Reflect.apply(Object.defineProperty, Object, [...])`
  - `Reflect.apply(Object.defineProperties, Object, [...])`
  - `Reflect.apply(Object.assign, Object, [...])`
  - `Reflect.apply(Reflect.set, Reflect, [...])`
- 支持 bracket callee 与命名空间别名：
  - `Reflect['apply'](...)`
  - `const R = Reflect; R.apply(...)`
- `Reflect.apply` 第 3 参数不是数组字面量、包含 spread/omitted、或无法静态还原时，style-profit surface 内 fail closed。

### 3.2 解构 mutator source 变体识别
- 赋值式解构新增字符串/计算属性字面量支持：
  - `({ 'defineProperty': dp } = Object)`
  - `({ "assign": merge } = Object)`
  - `({ ['defineProperty']: dp } = Object)`
  - `({ ['set']: set } = Reflect)`
- 非字面量计算属性作为 mutator source（如 `({ [ACTION_KEY]: dp } = Object)`）在 style-profit surface 内 fail closed。

### 3.3 globalThis/window 解构命名空间识别
- 新增全局容器别名解析，支持：
  - `const { Object: Obj } = globalThis`
  - `const { Reflect: R } = window`
- 上述命名空间别名后续调用按 `Object.*` / `Reflect.*` 等价 sink 拦截。

### 3.4 失败路径统一 fail closed
- runtime mutator 参数不可还原（含 `apply` 参数形态异常）统一记为 fail closed 违规。
- 解构 source 键无法静态确认时记入 `runtimeAliasRiskFindings` 并 fail closed。

## 4. 新增反向测试（J16）
新增并通过以下 14 条反向测试：
1. `Reflect.apply(Object.defineProperty, Object, [item, 'onClick', { value: openHelp }])`
2. `Reflect.apply(Object.defineProperties, Object, [item, { onClick: { value: openHelp } }])`
3. `Reflect.apply(Object.assign, Object, [item, { onClick: openHelp }])`
4. `Reflect.apply(Reflect.set, Reflect, [item, 'onClick', openHelp])`
5. `Reflect['apply'](Object.defineProperty, Object, [item, 'onClick', { value: openHelp }])`
6. `const R = Reflect; R.apply(Object.assign, Object, [item, { onClick: openHelp }])`
7. `let dp; ({ 'defineProperty': dp } = Object); dp(item, 'onClick', ...)`
8. `let merge; ({ "assign": merge } = Object); merge(item, { onClick: openHelp })`
9. `let dp; ({ ['defineProperty']: dp } = Object); dp(item, 'onClick', ...)`
10. `let set; ({ ['set']: set } = Reflect); set(item, 'onClick', openHelp)`
11. `const { Object: Obj } = globalThis; Obj.defineProperty(item, 'onClick', ...)`
12. `const { Reflect: R } = window; R.set(item, 'onClick', openHelp)`
13. `Reflect.apply(..., args)` 第三参数非数组字面量 fail closed
14. `({ [ACTION_KEY]: dp } = Object)` 非字面量计算属性 mutator source fail closed

## 5. 验证命令与结果

### 5.1 前端
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=149`）

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

### 6.1 J16 覆盖扫描
命令：
- `rg -n "Reflect\.apply|Reflect\['apply'\]|...|runtimeAliasRiskFindings|reflect_apply" scripts/check-style-profit-contracts.mjs scripts/test-style-profit-contracts.mjs`

结果：命中 J16 新增实现与 14 条反向测试，符合预期。

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
- commit：`ddce4712ba7d06bac0de0920e6ad65aa8ab8bf04`
- message：`fix: close style profit runtime mutator sink variants`

## 9. 结论
`TASK-005J16` 已完成：
- Reflect.apply / Reflect['apply'] / Reflect 别名 sink 绕过已关闭。
- 字符串属性解构、计算属性解构、globalThis/window 解构命名空间绕过已关闭。
- 非字面量 computed mutator source 与不可还原 apply 参数按 fail closed 处理。
- TASK-005J13/J14/J15 已关闭绕过未回潮。
- 验证全部通过，未开放创建快照入口，未进入 `TASK-006`。
