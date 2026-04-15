# TASK-005J33 循环与参数解构 Alias 门禁整改证据

## 1. 任务范围与边界
- 任务编号：`TASK-005J33`
- 目标：修复 `for...of`、函数参数解构、回调参数解构未进入数组状态图导致的 style-profit 绕过。
- 本次仅修改前端门禁脚本与测试脚本，并新增本证据文档。
- 未开放快照创建入口；未进入 `TASK-006`。

## 2. 修改文件
1. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
2. `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
3. `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J33_循环与参数解构Alias门禁整改证据.md`

## 3. 门禁实现说明（J33）
### 3.1 for...of 绑定接入数组状态图
- 在 runtime 分析中新增 `ForOfStatement` 处理。
- 对如下绑定形式进行 alias 绑定并追踪到同一 `array_id`：
  - `for (const alias of [args])`
  - `for (const [alias] of [[args]])`
  - `for (const { value: alias } of [{ value: args }])`
  - 赋值式 initializer 模式。
- iterable 或绑定模式无法静态还原时，按 `ForOf.*` 原因将相关数组标记 `unknown`（fail closed）。

### 3.2 函数参数 BindingPattern 接入副作用汇总
- 扩展函数 side-effect summary，新增参数 alias 绑定与状态字段：
  - `parameter_alias_bindings`
  - `captures_parameter_aliases`
  - `mutates_parameter_aliases`
  - `escapes_parameter_aliases`
- 支持函数参数中的：
  - `Identifier`
  - `ArrayBindingPattern`
  - `ObjectBindingPattern`
  - 嵌套 pattern
- 在调用点按实参完成参数路径绑定（非按函数体源码位置），再将污染/逃逸落到实际数组状态。

### 3.3 回调参数解构接入（forEach/map/some/every/filter/find）
- 新增迭代方法集合：`forEach/map/some/every/filter/find`。
- 对静态可还原集合应用回调 summary + 参数绑定。
- 集合/回调不可解析时在存在潜在副作用下按 conservative unknown 处理（fail closed）。

### 3.4 调用时机与误杀修正
- 仅在未应用已知函数 summary 时执行通用 `CallArgumentEscape`，避免对已知安全调用重复污染。
- 对参数绑定无法解析的 unknown 升级增加“存在 tracked candidate”门槛，减少无关标识符触发的误杀。

## 4. 新增 J33 反向测试（节选）
已在 `scripts/test-style-profit-contracts.mjs` 新增并通过以下场景（均应失败）：
1. `for...of` alias 污染后 `new Worker(...args)`
2. `for...of` 嵌套数组解构 alias 污染
3. `for...of` 对象解构 alias 污染
4. unresolved iterable `for...of` fail closed
5. 函数参数数组解构污染
6. tuple 参数传入 + 参数解构污染
7. 函数参数对象解构污染
8. 箭头函数参数解构污染
9. 函数表达式参数解构污染
10. `forEach(([alias]) => ...)` 污染
11. `forEach(({ value: alias }) => ...)` 污染
12. unresolved collection callback fail closed
13. 污染后 `Reflect.construct(Worker, args)`
14. 参数解构污染后 `new unknownCtor(...args)`

## 5. 验证命令与结果
### 5.1 前端
在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc` 执行：

```bash
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

结果：
- `check:style-profit-contracts` 通过（`Style-profit contract check passed. Scanned files: 24`）
- `test:style-profit-contracts` 通过（`All style-profit contract fixture tests passed. scenarios=431`）
- `verify` 通过（production/style-profit contracts + typecheck + build 全通过）
- `npm audit --audit-level=high` 结果：`found 0 vulnerabilities`

### 5.2 后端定向回归（只跑，不改后端）
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 执行：

```bash
.venv/bin/python -m pytest -q tests/test_style_profit_api.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

结果：
- `pytest`：`8 passed, 1 warning in 0.68s`
- `py_compile`：通过（无输出即成功）

## 6. 审计复现与禁线扫描
### 6.1 J33 用例覆盖扫描
执行：

```bash
rg -n "for \(const alias of \[args\]\)|for \(const \[alias\] of \[\[args\]\]\)|for \(const \{ value: alias \} of \[\{ value: args \}\]\)|function poison\(\[alias\]\)|poison\(\[args\]\)|forEach\(\(\[alias\]\)|collection\.forEach\(\(\[alias\]\)" scripts/test-style-profit-contracts.mjs
```

结果：命中多处新增 J33 反向测试（含 for...of、参数解构、回调参数解构、Reflect.construct/unknownCtor 场景）。

### 6.2 业务禁线扫描（src）
执行：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" src
```

结果：无命中（`rg` exit code 1）。

## 7. 禁改边界确认
- 未修改 `/07_后端/**`、`/.github/**`、`/02_源码/**`、`TASK-006*`。
- 未引入第三方 parser 依赖。
- 未新增 `POST /api/reports/style-profit/snapshots` 前端调用。

## 8. 提交信息
- 当前基线 HEAD（提交前）：`3713668`
- 计划提交信息：`fix: track style profit loop and param destructure aliases`
- commit hash：`ff671f9`
