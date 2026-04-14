# TASK-005J6 计算属性键交互字段门禁整改证据

## 1. 基本信息
- 任务编号：`TASK-005J6`
- 任务名称：计算属性键交互字段门禁整改
- 执行时间：`2026-04-14`
- 执行目录：`/Users/hh/Desktop/领意服装管理系统`
- 提交前 HEAD：`96e4156`

## 2. 修改文件
- `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `03_需求与设计/02_开发计划/TASK-005J6_计算属性键交互字段门禁整改证据.md`

## 3. 计算属性键识别实现
### 3.1 新增交互计算属性键识别
在 `check-style-profit-contracts.mjs` 中新增并接入：
- `actionInteractiveComputedAssignmentPattern`
- `actionInteractiveComputedMethodPattern`

并合并进 `actionInteractiveMemberRegex`，从而识别：
- `['onClick']: openHelp`
- `["onClick"]: openHelp`
- `['onClick']() {}`
- `["handler"]() {}`
- `async ['submit']() {}`

### 3.2 新增利润说明字段计算属性键识别
在 `hasExplanationFieldForPhraseInSegment(...)` 中新增 `computedFieldRegex`，识别：
- `['label']: '利润计算说明'`
- `["label"]: "利润计算说明"`
- 同类 `title/text/name/tooltip/description` 计算属性键

### 3.3 祖先链规则保持
未回退 `TASK-005J3/J4/J5` 祖先对象链规则：
- 子节点出现利润说明字段时仍向上检查祖先对象
- 祖先存在交互字段（属性/方法/计算属性）即判定违规
- 距离和顺序不影响判定

## 4. 新增/保留反向测试与成功夹具
在 `test-style-profit-contracts.mjs` 中新增并通过：
1. `computed onClick assignment with real 1200 filler`
2. `double-quoted label with computed handler method`
3. `async computed submit method with descendant meta label`
4. `computed onClick with computed meta label`
5. `children descendant label with computed onSelect method`

并保留：
- 引号键、方法简写、祖先链、多行上下文、长距离反向用例
- `查看详情/查询/返回` 等只读成功夹具
- 纯说明对象（含计算属性 label 且无交互字段）通过

## 5. 真实长距离 fixture 与距离断言
本次继续使用真实长字符串：
- `const longFiller = 'x'.repeat(1200)`
- 将 `longFiller` 展开写入内容字符串后再检测

并保留/新增距离断言：
- `Math.abs(content.indexOf("['onClick']") - content.indexOf('利润计算说明')) > 1200`

## 6. 验证命令与结果
### 6.1 前端验证
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

1. `npm run check:style-profit-contracts`
- 结果：通过（`Style-profit contract check passed. Scanned files: 24`）

2. `npm run test:style-profit-contracts`
- 结果：通过（`All style-profit contract fixture tests passed. scenarios=53`）

3. `npm run verify`
- 结果：通过（含 `check/test` + `typecheck` + `build`）

4. `npm audit --audit-level=high`
- 结果：通过（`found 0 vulnerabilities`）

### 6.2 后端只读回归（未改后端代码）
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
- 结果：通过（`34 passed, 1 warning`）

2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
- 结果：通过

## 7. 扫描结果
### 7.1 计算属性键覆盖扫描
命令：
- `rg -n "\['onClick'\]|\[\"onClick\"\]|\['handler'\]|\[\"handler\"\]|\['submit'\]|\[\"submit\"\]|\['label'\]|\[\"label\"\]|\['meta'\]|\[\"meta\"\]|利润计算说明|利润率计算规则|利润快照来源说明|repeat\(1200\)|indexOf" 06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

结果：命中新增计算属性与长距离断言相关用例（符合预期）。

### 7.2 业务禁线扫描
命令：
- `rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" 06_前端/lingyi-pc/src`

结果：无命中（命令退出码 1，符合“src 业务文件不得命中写入口语义”）。

## 8. 禁改边界确认
- 未修改：`07_后端/**`（代码层面）
- 未修改：`.github/**`
- 未修改：`02_源码/**`
- 未修改：`TASK-006*`
- 未提交：`.pytest-postgresql-*.xml`

## 9. 提交信息
- commit：`<待回填>`
- message：`fix: detect computed style profit action keys`

## 10. 结论
`TASK-005J6` 已完成：
- 计算属性键交互字段识别已补齐
- 祖先链规则未回退
- 新增反向测试覆盖通过
- 前端契约/全量 verify/审计依赖回归均通过
- 未开放创建快照入口，未进入 `TASK-006`
