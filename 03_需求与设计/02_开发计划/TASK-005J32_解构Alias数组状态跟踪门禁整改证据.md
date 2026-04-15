# TASK-005J32 解构 Alias 数组状态跟踪门禁整改证据

## 1. 任务范围
- 任务编号：TASK-005J32
- 目标：修复 `ArrayBindingPattern / ObjectBindingPattern` 与赋值式解构 alias 未进入数组状态图导致的绕过；确保解构 alias 写入会污染原数组并触发 style-profit fail closed。
- 严格边界：未改后端、未改 `.github`、未改 `02_源码`、未触达 TASK-006。

## 2. 实际修改文件
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J32_解构Alias数组状态跟踪门禁整改证据.md`

## 3. 门禁实现说明
### 3.1 collectRuntimeAnalysisContext 解构 alias 接入
- 新增并接入以下能力：
  - `resolveRuntimeStaticArrayLiteral()` / `resolveRuntimeStaticObjectLiteral()`
  - `resolveRuntimeObjectPropertyExpressionByKey()`
  - `bindRuntimeArrayAliasesFromBindingPattern()`
  - `bindRuntimeArrayAliasesFromAssignmentPattern()`
  - `markRuntimeTrackedArraysUnknownForDestructure()`
- 变量声明阶段新增：
  - `ArrayBindingPattern / ObjectBindingPattern` 都进入 alias 绑定流程，不再仅支持 `Identifier = Identifier`。
- 赋值阶段新增：
  - `ArrayLiteralExpression / ObjectLiteralExpression` 左值（赋值式解构）进入 alias 绑定流程。
- 无法静态还原的解构来源统一 conservative：相关 tracked array 标记 `unknown`，后续 Worker/unknownCtor spread 使用 fail closed。

### 3.2 函数副作用汇总支持解构 alias
- 在 `analyzeRuntimeFunctionSummary()` 内新增函数级解构 alias 追踪：
  - `bindRuntimeFunctionAliasesFromBindingPattern()`
  - `bindRuntimeFunctionAliasesFromAssignmentPattern()`
  - 函数级静态字面量映射（array/object）
- 支持识别函数体中的：
  - 数组解构、对象解构、嵌套解构、赋值式解构
- 副作用仍按调用点生效（J31 语义保持）：
  - 函数内解构 alias 写入会污染外层 `args` 对应 array state。

## 4. 新增反向测试（J32）
在 `scripts/test-style-profit-contracts.mjs` 新增 16 条失败用例，覆盖：
- `const [alias] = [args]`、`const [[alias]] = [[args]]`
- `[alias] = [args]`
- `const { value: alias } = { value: args }`
- `const { nested: { value: alias } } = { nested: { value: args } }`
- `({ value: alias } = { value: args })`
- 解构 alias 上 `splice` / `mutate(alias)`
- 函数内解构 alias 污染（hoisted function / arrow / function）
- `const [...aliases] = [args]`（rest）
- `const [alias = args] = []`（default）
- `const { [key]: alias } = holder`（computed）
- `Reflect.construct(Worker, args)` 下解构 alias 污染
- `new unknownCtor(...args)` 下解构 alias 污染

## 5. 成功 fixture（防误杀）
在基础 fixture 新增并通过：
- `const [spreadWorkerArrayDestructureAlias] = [spreadWorkerArgs]; new Worker(...spreadWorkerArrayDestructureAlias)`
- `const { value: spreadWorkerObjectDestructureAlias } = { value: spreadWorkerArgs }; new Worker(...spreadWorkerObjectDestructureAlias)`
- `const [dateArgsAlias] = [dateArgs]; new Date(...dateArgsAlias)`

## 6. 验证命令与结果
### 6.1 前端
```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```
结果摘要：
- `check:style-profit-contracts` 通过（`Style-profit contract check passed. Scanned files: 24`）
- `test:style-profit-contracts` 通过（`All style-profit contract fixture tests passed. scenarios=417`）
- `npm run verify` 全通过（含 production contracts、style-profit contracts、typecheck、vite build）
- `npm audit --audit-level=high`：`found 0 vulnerabilities`

### 6.2 后端只读回归
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```
结果摘要：
- `8 passed, 1 warning`（仅 pytest_asyncio deprecation warning）
- `py_compile` 无输出（通过）

## 7. 扫描结果
### 7.1 J32 用例覆盖扫描
已命中新增用例关键词（`const [alias] = [args]`、`const [[alias]] = [[args]]`、`{ value: alias }`、`Reflect.construct(Worker, args)` 等）并存在于 `scripts/test-style-profit-contracts.mjs`。

### 7.2 业务禁线扫描
执行：
```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" src
```
结果：无命中（exit code 1，符合“src 业务文件不得命中禁线”预期）。

## 8. 提交信息
- 代码提交：`1eaed2b`
  `fix: track style profit destructure array aliases`
