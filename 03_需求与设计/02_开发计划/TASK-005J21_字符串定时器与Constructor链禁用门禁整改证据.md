# TASK-005J21 字符串定时器与 Constructor 链禁用门禁整改证据

## 1. 修改文件
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs
- /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J21_字符串定时器与Constructor链禁用门禁整改证据.md

## 2. 门禁实现摘要
- 扩展 runtime codegen 分类：新增 `Global.setTimeout`、`Global.setInterval`（仅用于调用实参审计，不作为源引用一刀切禁用）。
- 新增字符串 timer 入口 fail-closed 检测：
  - 命中 `setTimeout/setInterval`（含 `window/globalThis`、别名、解构别名、间接调用、动态成员静态可折叠）后，第一参数为字符串字面量 / 模板字面量 / 字符串拼接即失败。
  - 第一参数为变量但无法静态证明为函数回调时失败。
- 新增 `constructor` 链收口：
  - 将成员名 `constructor` 归一到 codegen 源（`Global.Function`）处理。
  - 覆盖 `.constructor(...)`、`['constructor'](...)`、`.constructor.constructor(...)`、容器/别名/条件表达式源引用。
- 保留并通过既有 TASK-005H~TASK-005J20 门禁，不回退。

## 3. J21 新增反向测试（20 条）
已新增并通过：
1. `setTimeout("...")`
2. `setInterval("...")`
3. `window.setTimeout("...")`
4. `globalThis.setInterval("...")`
5. ``setTimeout(`...`)``
6. `setTimeout('a' + 'b')`
7. `const code = "..."; setTimeout(code)`
8. `const delay = setTimeout; delay("...")`
9. `const { setTimeout: delay } = window; delay("...")`
10. `;(0, setTimeout)("...")`
11. `window['set' + 'Timeout']("...")`
12. `(() => {}).constructor('...')(... )`
13. `[]['filter']['constructor']('...')(... )`
14. `({}).constructor.constructor('...')(... )`
15. `({})['constructor']['constructor']('...')(... )`
16. `const Ctor = (() => {}).constructor`（未调用）
17. `const holder = { make: ({}).constructor.constructor }`（未调用）
18. `const holder = [Function.prototype.constructor]`（未调用）
19. `const make = condition ? ({}).constructor.constructor : Function`
20. `Object.freeze({ make: ({}).constructor.constructor })`

## 4. 成功用例保留
基础 fixture 已显式保留并通过：
- `setTimeout(() => refresh(), 100)`
- `setInterval(refresh, 1000)`
- `record['constructor_name']`
- `const text = 'constructor disabled'`
- `new Date()`
- `const next = { ...base, status: 'readonly' }`

## 5. 验证命令与结果
### 前端
- `npm run check:style-profit-contracts`：通过
- `npm run test:style-profit-contracts`：通过（`scenarios=237`）
- `npm run verify`：通过
- `npm audit --audit-level=high`：通过（`found 0 vulnerabilities`）

### 后端只读回归
- `.venv/bin/python -m pytest -q tests/test_style_profit_api.py`：`8 passed, 1 warning`
- `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`：通过

## 6. 禁改边界核对
- 未修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- 未修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`
- 未修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 未修改任何 `TASK-006*`
- 未提交 `.pytest-postgresql-*.xml`、`dist`、`coverage`、`node_modules` 生成物

## 7. 提交信息
- commit hash：60dce4a05b9c3b8cd039f3d067e4676284dac7d3
- commit message：`fix: ban style profit timer strings and constructor chains`
