# TASK-005J12 运行时显式 Action Key 注入门禁整改证据

## 1. 基本信息
- 任务编号：`TASK-005J12`
- 任务名称：运行时显式 Action Key 注入门禁整改
- 执行时间：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`f359fa7`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J12_运行时显式ActionKey注入门禁整改证据.md`

## 3. 显式 Action Key 运行时注入门禁实现
### 3.1 显式 action key 集合
在门禁中统一扩展交互键集合，至少覆盖：
- `onClick`
- `handler`
- `action`
- `command`
- `onSelect`
- `onCommand`
- `callback`
- `execute`
- `submit`
- `onConfirm`
- `onSubmit`
- `click`
- `open`

### 3.2 新增运行时显式注入检测（AST）
在 style-profit surface 内新增 `collectRuntimeExplicitActionInjectionFindings()`，覆盖：
- `ElementAccessExpression` 左值写入（字符串字面量 key 命中 action key 集合）
- `PropertyAccessExpression` 左值写入（属性名命中 action key 集合）
- `Object.defineProperty` 第二参数为显式 action key
- `Object.defineProperties` descriptor object 中显式 action key
- `Reflect.set` 第二参数为显式 action key
- `Object.assign` source object literal 中显式 action key

统一失败文案：
- `style-profit forbids runtime explicit action-key injection; use object-literal readonly actions only（款式利润前端禁止运行时显式 action key 注入）`

### 3.3 与 J11 动态注入规则并存
- `dynamic_computed_key / unknown_key` 的运行时注入 fail closed 保持（J11）。
- 本轮新增“显式字面量 action key 的运行时注入也 fail closed”（J12）。

### 3.4 边界不变
- 对象字面量中的合法只读 action 保持既有规则（不因 J12 一刀切）。
- 非 action 字段运行时写入不阻断（如 `item.disabled = true`）。
- 读取型 dynamic key（不构成写入）不阻断。

### 3.5 依赖边界
- 未新增第三方依赖。
- 继续使用现有 `typescript` devDependency。

## 4. 新增反向测试（J12）
在 `test-style-profit-contracts.mjs` 新增并通过：
1. `item['onClick'] = openHelp` 失败
2. `item.onClick = openHelp` 失败
3. `Object.defineProperty(item, 'onClick', { value: openHelp })` 失败
4. `Object.assign(item, { onClick: openHelp })` 失败
5. `Reflect.set(item, 'onClick', openHelp)` 失败
6. `Object.defineProperties(item, { onClick: { value: openHelp } })` 失败
7. `label='查看详情'` 也不豁免运行时显式注入（失败）
8. Vue `script setup` 显式注入失败
9. 真实长距离（1200）`Object.defineProperty(..., 'onClick', ...)` 失败并断言距离

## 5. 成功 fixture 保留
- 对象字面量合法只读 action：`{ label: '查看详情', onClick: goDetail }` 保持
- `{ label: '查询', onClick: loadRows }` 保持
- `{ label: '返回', onClick: goBack }` 保持
- 非 action 运行时写入：`item.disabled = true` 保持
- 非 action `Object.assign(item, { disabled: true })` 保持
- 读取型 `const value = item[ACTION_KEY]`（非写入）保持
- Vue template 只读说明文案成功 fixture 保持

## 6. 验证命令与结果
### 6.1 前端验证
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=96`）

3. `npm run verify`
- 结果：通过（production/style-profit contract + typecheck + build 全部通过）

4. `npm audit --audit-level=high`
- 结果：通过（`found 0 vulnerabilities`）

### 6.2 后端只读回归（未改后端代码）
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
- 结果：通过（`34 passed, 1 warning`）

2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

## 7. 扫描结果
### 7.1 显式 action key 注入覆盖扫描
命令：
- `rg -n "Object\.defineProperty|Object\.defineProperties|Reflect\.set|Object\.assign|PropertyAccessExpression|ElementAccessExpression|item\[['\"]onClick['\"]\]|item\.onClick|explicit action key|显式 action|运行时注入|fail closed" scripts/check-style-profit-contracts.mjs scripts/test-style-profit-contracts.mjs`

结果：命中显式注入实现与 J12 新增反向测试（符合预期）。

### 7.2 业务禁线扫描
命令：
- `rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|...|profitRecalculate" src`

结果：无命中（退出码 1，符合预期）。

## 8. 禁改范围确认
- 未修改：`07_后端/**`
- 未修改：`.github/**`
- 未修改：`02_源码/**`
- 未修改：`TASK-006*`
- 未提交：`.pytest-postgresql-*.xml`

## 9. 提交信息
- commit：`79fdc7a`
- message：`fix: detect explicit runtime style profit actions`

## 10. 结论
`TASK-005J12` 已完成：
- 在 style-profit surface 内，显式 action key 的运行时注入已纳入 fail closed。
- 不再因 label 为“查看详情/查询/返回”而放行运行时注入。
- 对象字面量中的合法只读 action 不误杀。
- 非 action 字段写入与读取型 dynamic key 不误杀。
- 前端与后端只读回归通过。
- 未开放创建快照入口，未进入 `TASK-006`。
