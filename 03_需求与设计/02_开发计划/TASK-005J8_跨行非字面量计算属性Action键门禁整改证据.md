# TASK-005J8 跨行非字面量计算属性 Action 键门禁整改证据

## 1. 基本信息
- 任务编号：`TASK-005J8`
- 任务名称：跨行非字面量计算属性 Action 键门禁整改
- 执行时间：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`c428cd8`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J8_跨行非字面量计算属性Action键门禁整改证据.md`

## 3. 跨行 computed key 捕获实现
### 3.1 捕获规则增强
在 `check-style-profit-contracts.mjs` 中将 computed key 捕获升级为支持跨行表达式：
- `computedPropertyKeyRegex` 支持以下结构：
  - `[actionMap\n  .onClick]: ...`
  - `[\n  ACTION_KEY\n]: ...`
  - `[getActionKey(\n  'profit'\n)]: ...`
  - `[actionMap\n  .onClick]()`
  - `async [\n  ACTION_KEY\n]()`

### 3.2 非字面量判断规范化
新增/沿用规范化逻辑：
- `normalizeComputedKeyExpr(computedExpr)`：压缩空白并 `trim`
- `isLiteralComputedKey(computedExpr)`：仅字符串字面量 computed key 判定为合法
  - 合法示例：`['onClick']`、`["handler"]`、`['label']`
  - 非法示例：`ACTION_KEY`、`actionMap . onClick`、`getActionKey('profit')`

### 3.3 失败提示
跨行非字面量命中时返回：
- `style-profit forbids non-literal computed action keys; use explicit onClick/handler/command keys or quoted literal computed keys（款式利润前端禁止非字面量计算属性 action key）`

### 3.4 祖先链与既有规则保持
未回退 TASK-005J3/J4/J5/J6/J7：
- 子节点说明字段仍沿祖先对象链检查交互字段
- 顺序与距离不影响判定
- 裸键/引号键/方法简写/计算属性键仍全部覆盖

## 4. 新增反向测试（J8）
在 `test-style-profit-contracts.mjs` 新增并通过：
1. 跨行 `[actionMap .onClick]` 属性赋值失败
2. 跨行 `[
   ACTION_KEY
 ]` 属性赋值失败
3. 跨行 `[getActionKey('profit')]` 属性赋值失败
4. 跨行 computed 方法 `[actionMap .onClick]()` 失败
5. async 跨行 computed 方法 `async [ACTION_KEY]()` + 后代 label 失败
6. 真实长距离（1200）跨行 computed key 失败，并断言 `label` 与 `[actionMap` 距离 > 1200

## 5. 合法成功 fixture（J8）
继续通过的合法场景：
- 字符串字面量 computed key：`['onClick']` / `["handler"]` / `['label']`
- 跨行字符串字面量 computed key：
  - `[
     'label'
   ]: '利润计算说明'`
- 纯说明对象（无交互字段）
- 查看详情 / 查询 / 返回等只读动作

## 6. 验证命令与结果
### 6.1 前端验证
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=65`）

3. `npm run verify`
- 结果：通过（contract checks + typecheck + build）

4. `npm audit --audit-level=high`
- 结果：通过（`found 0 vulnerabilities`）

### 6.2 后端只读回归（未改后端代码）
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
- 结果：通过（`34 passed, 1 warning`）

2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

## 7. 扫描结果
### 7.1 跨行 computed key 覆盖扫描
命令：
- `rg -n "actionMap|ACTION_KEY|getActionKey|跨行|non-literal computed|非字面量|computed action key|利润计算说明|利润快照来源说明|repeat\(1200\)|indexOf" scripts/test-style-profit-contracts.mjs scripts/check-style-profit-contracts.mjs`

结果：命中 J8 新增跨行反向用例、长距离断言与门禁文案（符合预期）。

### 7.2 业务禁线扫描
命令：
- `rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|...|profitRecalculate" 06_前端/lingyi-pc/src`

结果：无命中（退出码 1，符合“src 业务文件不得命中写入口语义”）。

## 8. 禁改边界确认
- 未修改：`07_后端/**`（代码层面）
- 未修改：`.github/**`
- 未修改：`02_源码/**`
- 未修改：`TASK-006*`
- 未提交：`.pytest-postgresql-*.xml`

## 9. 任务边界声明
- 本任务**未引入 AST 解析**（未进行 TypeScript/Babel 解析器大改）
- 仅增强跨行 computed key 捕获与非字面量禁用门禁

## 10. 提交信息
- commit：`ac09a5b`
- message：`fix: detect multiline computed style profit action keys`

## 11. 结论
`TASK-005J8` 已完成：
- 跨行非字面量 computed key 绕过已关闭
- 合法跨行字符串字面量 computed key 未被误杀
- 前端/后端回归通过
- 未开放创建快照入口，未进入 `TASK-006`
