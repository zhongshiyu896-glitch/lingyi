# TASK-005J22 Timer call/apply 等价调用门禁整改证据

## 1. 修改文件
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J22_TimerCallApply等价调用门禁整改证据.md

## 2. 门禁实现摘要
- 将 timer 检测接入统一 runtime call descriptor 归一逻辑：
  - `resolveRuntimeCallDescriptor(..., methodSet)` 增加方法集参数。
  - `collectRuntimeCodegenTimerCallFindings()` 改为使用 `resolveRuntimeCallDescriptor(..., runtimeTimerMethodSet)` + `normalizeRuntimeCallArguments()`。
- 已覆盖 timer 等价调用：
  - `setTimeout/setInterval.call(...)`
  - `setTimeout/setInterval.apply(...)`
  - `Reflect.apply(timer, thisArg, args)`
  - `Reflect['apply'](...)`
  - timer 别名/解构别名/命名空间别名后的 `.call/.apply`
- 参数语义已按调用方式统一归一：
  - `.call()`：第 2 个参数为 callback。
  - `.apply()`：第 2 个参数数组第 1 项为 callback。
  - `Reflect.apply()`：第 3 个参数数组第 1 项为 callback。
- fail closed 行为：
  - apply 参数不可静态还原（非数组字面量、spread、空洞）=> fail closed。
  - callback 为字符串字面量/模板字面量/字符串拼接/无法证明非字符串 => fail closed。
- 兼容性收口：
  - 保留 runtime mutator 源引用禁用。
  - 对 `Reflect.apply(timer, ..., [safeCallback, delay])` 增加窄口放行，避免误杀只读合法 timer 回调场景。

## 3. J22 新增反向测试（18 条）
已新增并通过：
1. `setTimeout.call(window, "...")`
2. `setInterval.call(globalThis, "...")`
3. `window.setTimeout.call(window, "...")`
4. `globalThis.setInterval.call(globalThis, "...")`
5. `setTimeout['call'](window, "...")`
6. `setTimeout.apply(window, ["...", 0])`
7. `setInterval.apply(globalThis, ["...", 0])`
8. `window.setTimeout.apply(window, ["...", 0])`
9. `globalThis.setInterval.apply(globalThis, ["...", 0])`
10. `setTimeout['apply'](window, ["...", 0])`
11. `setTimeout.apply(window, args)`（args 无法静态还原）
12. `setTimeout.apply(window, [code, 0])`（code 无法证明非字符串）
13. `Reflect.apply(setTimeout, window, ["...", 0])`
14. `Reflect.apply(window.setTimeout, window, ["...", 0])`
15. `Reflect.apply(globalThis.setInterval, globalThis, ["...", 0])`
16. `Reflect['apply'](setTimeout, window, ["...", 0])`
17. `const delay = setTimeout; delay.call(window, "...")`
18. `const delay = setTimeout; delay.apply(window, ["...", 0])`

## 4. J22 成功用例保留
基础 fixture 已显式保留并通过：
- `setTimeout.call(window, () => refresh(), 100)`
- `setTimeout.apply(window, [() => refresh(), 100])`
- `Reflect.apply(setTimeout, window, [refresh, 100])`
- `setInterval.call(window, refresh, 1000)`
- `setInterval.apply(window, [refresh, 1000])`

## 5. 回归要求核对
- TASK-005H ~ TASK-005J21 既有反向测试未删除、未降级。
- `test-style-profit-contracts` 场景数从 237 增至 255（新增 18 条 J22 反向用例）。

## 6. 验证命令与结果
### 前端
- `npm run check:style-profit-contracts`：通过（Scanned files: 24）
- `npm run test:style-profit-contracts`：通过（`All style-profit contract fixture tests passed. scenarios=255`）
- `npm run verify`：通过（production/style-profit 契约 + typecheck + build 全通过）
- `npm audit --audit-level=high`：通过（`found 0 vulnerabilities`）

### 后端只读回归
- `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`：`8 passed, 1 warning`
- `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`：通过

## 7. 禁改边界核对
- 未修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- 未修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`
- 未修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 未修改任何 `TASK-006*`
- 未提交 `.pytest-postgresql-*.xml`、`coverage`、`dist`、`node_modules` 等运行生成物

## 8. 提交信息
- commit hash：待提交后回填
- commit message：`fix: harden style profit timer call apply sinks`
