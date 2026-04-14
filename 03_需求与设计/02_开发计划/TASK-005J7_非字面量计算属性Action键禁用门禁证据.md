# TASK-005J7 非字面量计算属性 Action 键禁用门禁证据

## 1. 基本信息
- 任务编号：`TASK-005J7`
- 任务名称：非字面量计算属性 Action 键禁用门禁
- 执行时间：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`64a5254`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J7_非字面量计算属性Action键禁用门禁证据.md`

## 3. 非字面量 computed action key 禁用实现
在 `check-style-profit-contracts.mjs` 新增规则：

1. 新增检测正则：
- `computedPropertyKeyRegex = /\[\s*([^\]\n]+?)\s*\]\s*(?::|\([^)]*\)\s*\{)/g`

2. 新增字面量判定函数：
- `isLiteralComputedKey(computedExpr)`
- 仅 `['onClick']` / `["handler"]` / `['label']` 这类字符串字面量计算键通过

3. 在 `styleProfitSurface` 分支内执行禁用：
- 若命中非字面量计算键（如 `[ACTION_KEY]`、`[actionMap.onClick]`、`[getActionKey()]`、`[labelKey]`），立即失败

4. 失败提示：
- `style-profit forbids non-literal computed action keys; use explicit onClick/handler/command keys or quoted literal computed keys（款式利润前端禁止非字面量计算属性 action key）`

## 4. 新增反向测试
在 `test-style-profit-contracts.mjs` 新增以下失败用例（均通过“预期失败”断言）：

1. `[ACTION_KEY]: openHelp`
2. `[actionMap.onClick]: openHelp`
3. `[getActionKey()]: openHelp`
4. `[ACTION_KEY]() {}`
5. `async [ACTION_KEY]() {}`
6. `[labelKey]: '利润计算说明'`（祖先存在交互字段）

## 5. 合法字面量 computed key 成功 fixture
保留并补充合法成功夹具：
- `readonlyHelpComputed`：`['label']: '利润计算说明'`（无交互字段）
- `readonlyActionsComputed`：`['label'] + ['onClick']` 的只读导航动作（查看详情/查询/返回）

## 6. 关键边界声明
- 本任务**未引入 AST 解析**（未引入 TypeScript/Babel 解析器重构）
- 本任务采用短期策略：**禁用非字面量 computed key**
- 若未来需支持动态 computed key，需单独立项做 AST 级静态分析

## 7. 验证命令与结果
### 7.1 前端验证
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=59`）

3. `npm run verify`
- 结果：通过（含 production/style-profit 契约检查、typecheck、build）

4. `npm audit --audit-level=high`
- 结果：通过（`found 0 vulnerabilities`）

### 7.2 后端只读回归（未改后端代码）
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
- 结果：通过（`34 passed, 1 warning`）

2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

## 8. 扫描结果
### 8.1 非字面量 computed key 覆盖扫描
命令：
- `rg -n "\[ACTION_KEY\]|\[actionMap\.onClick\]|\[getActionKey\(\)\]|\[labelKey\]|non-literal computed|非字面量|computed action key|利润计算说明|利润快照来源说明" 06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs 06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`

结果：命中新增 J7 反向用例与门禁报错文本（符合预期）。

### 8.2 业务禁线扫描
命令：
- `rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" 06_前端/lingyi-pc/src`

结果：无命中（命令退出码 1，符合预期）。

## 9. 禁改边界确认
- 未修改：`07_后端/**`（代码层面）
- 未修改：`.github/**`
- 未修改：`02_源码/**`
- 未修改：`TASK-006*`
- 未提交：`.pytest-postgresql-*.xml`

## 10. 提交信息
- commit：`<待回填>`
- message：`fix: forbid dynamic style profit action keys`

## 11. 结论
`TASK-005J7` 已完成：
- style-profit 业务面已禁止非字面量 computed action key
- J7 要求的 6 条反向测试已覆盖并通过
- 字符串字面量 computed key 合法场景保持通过
- 前端契约、verify、audit 与后端只读回归均通过
- 未开放创建快照入口，未进入 `TASK-006`
