# TASK-005J10 Style Profit 动态 Computed Key 全域 Fail Closed 门禁整改证据

## 1. 基本信息
- 任务编号：`TASK-005J10`
- 任务名称：Style Profit 动态 Computed Key 全域 Fail Closed 门禁整改
- 执行时间：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`6323646`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J10_StyleProfit动态ComputedKey全域FailClosed门禁整改证据.md`

## 3. 全域 Fail Closed 实现说明
### 3.1 核心收口
在 style-profit surface AST 扫描中，动态或未知 computed key 不再依赖 action-like 容器名（`actions/menu/button/toolbar/items` 等）判定风险。

实现调整：
- 对任意 `ObjectLiteralExpression`，只要出现 `dynamic_computed_key` 或 `unknown_key`，直接失败。
- 失败信息统一为：
  - `style-profit forbids dynamic or unknown computed keys in object literals; use explicit literal keys（款式利润前端禁止动态或无法静态确认的计算属性键，请使用显式字面量键）`

### 3.2 容器名依赖移除
- 删除了 dynamic key 判定中对 action-like 容器名/变量名的依赖路径。
- `items/rows/configs/columns/entries/options/list` 等中性命名不再成为豁免条件。

### 3.3 字面量 computed key 保持既有规则
以下仍作为 `literal_key`，继续按既有只读门禁与祖先链规则处理：
- `['onClick']`
- `["handler"]`
- `['label']`
- 跨行字符串字面量 computed key

### 3.4 Spread fail-closed 策略
- 在说明文案对象链上，只要存在 `SpreadAssignment` 即按风险 fail-closed。
- 不以容器名推断 spread 安全性，维持保守策略。

### 3.5 依赖边界
- 未新增任何依赖。
- 继续使用现有 `typescript` devDependency。

## 4. 新增反向测试（J10）
在 `test-style-profit-contracts.mjs` 新增并通过：
1. `items` 中性容器 + `[ACTION_KEY]` 失败。
2. `rows` 中性容器 + `[actionMap['onClick']]` 失败。
3. `configs` 中性容器 + `[getActionKey()]` 失败。
4. `columns` 中性容器 + `[labelKey]` 失败。
5. `unknownKeyFactory()` 作为 computed key 失败。
6. Vue `script setup` 中中性容器名 + dynamic key 失败。
7. 真实长距离（1200）+ `items` + `[ACTION_KEY]` 失败，并有距离断言。

## 5. 成功 fixture 保持
- 字符串字面量 computed key fixture 继续通过（或按既有语义门禁失败）。
- 纯说明对象（无 dynamic/unknown key）继续通过。
- `查看详情 / 查询 / 返回` 只读动作继续通过。
- Vue template 文本禁线既有成功 fixture 未回退。

## 6. 验证命令与结果
### 6.1 前端验证
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=79`）

3. `npm run verify`
- 结果：通过（生产契约 + style-profit 契约 + typecheck + build 全部通过）

4. `npm audit --audit-level=high`
- 结果：通过（`found 0 vulnerabilities`）

### 6.2 后端只读回归（未改后端代码）
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
- 结果：通过（`34 passed, 1 warning`）

2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

## 7. 扫描结果
### 7.1 全域 fail closed 覆盖扫描
命令：
- `rg -n "dynamic_computed_key|unknown_key|items|rows|configs|columns|ACTION_KEY|labelKey|unknownKeyFactory|style-profit forbids dynamic|全域|fail closed|ObjectLiteralExpression" scripts/check-style-profit-contracts.mjs scripts/test-style-profit-contracts.mjs`

结果：命中 J10 新增实现点与反向测试用例（符合预期）。

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
- commit：`6c46d19`
- message：`fix: fail closed dynamic style profit computed keys`

## 10. 结论
`TASK-005J10` 已完成：
- style-profit surface 下 dynamic/unknown computed key 实现全域 fail closed。
- 判定不再依赖 actions/menu/button/toolbar/items 等容器命名。
- 字符串字面量 computed key 与既有只读门禁不回退。
- 前端与后端只读回归通过。
- 未开放创建快照入口，未进入 `TASK-006`。
