# TASK-005J18 Runtime Mutator 源引用禁用门禁收口证据

## 1. 任务信息

- 任务编号：`TASK-005J18`
- 执行时间：`2026-04-14`
- 执行范围：仅前端契约门禁脚本与测试、J18 证据文档

## 2. 修改文件

1. `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
2. `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
3. `03_需求与设计/02_开发计划/TASK-005J18_RuntimeMutator源引用禁用门禁收口证据.md`

## 3. 实现摘要

### 3.1 源引用禁用收口

在 `analyzeStyleProfitAstContracts()` 中新增 runtime mutator 源引用失败通道：

- 新增统一失败消息：
  - `style-profit forbids runtime mutator source references; use object spread and readonly literal actions`
- 新增去重机制，避免同一表达式重复报错。
- 接入两类来源：
  1. `collectRuntimeAnalysisContext()` 收集的 `runtimeMutatorSourceFindings`（变量声明、解构、赋值等别名来源）
  2. `collectRuntimeMutatorSourceReferenceFindings()` 收集的直接源引用（identifier/property/element 解析到 mutator 源）

### 3.2 基础合法 fixture 对齐

- 为符合 J18“对象合并优先 spread、禁用 mutator 源引用”的约束，基线 fixture 将：
  - `Object.assign(readonlyUiState, { disabled: true })`
  - 调整为
  - `const readonlyUiStateNext = { ...readonlyUiState, disabled: true }`

### 3.3 J18 反向测试补充

新增并通过以下 J18 重点反向场景（节选）：

1. `getMutator()` 返回 `Object.defineProperty` 后调用
2. 箭头函数返回 `Object.assign` 后调用
3. IIFE 返回 `Object.defineProperty` 后调用
4. 内联数组/对象中转调用
5. 嵌套容器中转调用
6. `Object.freeze/Object.seal` 包装容器中转调用
7. 条件容器（数组/对象）中转调用
8. `globalThis.Object.assign` / `window.Reflect.set` 来源函数中转调用
9. holder 容器函数中转调用
10. 源引用存在但未调用仍失败：
   - `const dangerous = Object.defineProperty`
   - `const dangerous = { dp: Object.defineProperty }`

## 4. 验证命令与结果

### 4.1 前端契约门禁

在 `06_前端/lingyi-pc` 执行：

1. `npm run check:style-profit-contracts`
   - 结果：通过（`Style-profit contract check passed. Scanned files: 24`）
2. `npm run test:style-profit-contracts`
   - 结果：通过（`All style-profit contract fixture tests passed. scenarios=179`）
3. `npm run verify`
   - 结果：通过（production + style-profit 契约、typecheck、build 全通过）
4. `npm audit --audit-level=high`
   - 结果：`found 0 vulnerabilities`

### 4.2 后端只读回归

在 `07_后端/lingyi_service` 执行：

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`
   - 结果：`8 passed, 1 warning`
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过（无输出）

### 4.3 规则覆盖扫描

1. 源引用禁用实现与用例扫描：
   - 命令：
     - `rg -n "runtime mutator source references|getMutator\(\)|Object\.freeze|Object\.seal|dangerous = Object\.defineProperty|dangerous = \{ dp: Object\.defineProperty \}|holder = \[\(\) => Object\.assign\]" 06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs 06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
   - 结果：命中实现与新增用例。

2. 业务禁线扫描（src 范围）：
   - 命令：
     - `rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" 06_前端/lingyi-pc/src`
   - 结果：无输出（命令返回 1，表示未命中）。

## 5. 边界与合规

- 未修改后端代码：`07_后端/**`（仅执行只读回归）
- 未修改 `.github/**`
- 未修改 `02_源码/**`
- 未触碰 `TASK-006*`
- 未提交运行产物（`.pytest-postgresql-*.xml`、`dist`、`coverage`、`node_modules`）

## 6. 提交信息

- 提交 SHA：`<pending>`
- 提交信息：`<pending>`

## 7. 结论

`TASK-005J18` 已完成源码与测试整改：style-profit surface 已对 runtime mutator 源引用实施禁用收口，并通过前端契约门禁与后端只读回归验证。
