# TASK-005J5 对象方法简写交互字段门禁整改证据

## 1. 任务与提交信息

- 任务：TASK-005J5
- 目标：修复对象方法简写交互字段（`onClick() {}` 等）绕过
- 提交前 HEAD：`f0b5de0`
- 功能提交后 HEAD：`191dceeaa0500e3cbc1fd6c56b5ef4232fd29847`
- 功能提交信息：`fix: detect style profit action method shorthand`

## 2. 修改文件

1. `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
2. `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

## 3. 对象方法简写识别实现

在 `check-style-profit-contracts.mjs` 中完成：

1. 交互成员检测从“仅 key:value”升级为“属性赋值 + 方法简写”双模式。
2. 支持交互成员：
   - `onClick`
   - `handler`
   - `action`
   - `command`
   - `onSelect`
   - `onCommand`
   - `callback`
   - `execute`
   - `submit`
3. 支持格式：
   - 裸键赋值：`onClick: openHelp`
   - 引号键赋值：`"onClick": openHelp` / `'onClick': openHelp`
   - 方法简写：`onClick() {}`
   - 异步方法：`async submit() {}`
   - 引号方法名：`"onClick"() {}` / `'handler'() {}`
4. 祖先链规则保持：
   - 后代出现利润说明字段时，检查全部祖先对象；
   - 任一祖先存在交互成员（属性或方法）即失败。

## 4. 新增反向测试（必须失败）

在 `test-style-profit-contracts.mjs` 新增并通过以下反向用例：

1. `label + 真实1200字符 filler + onClick() {}`
2. `"label" + "onClick"() {}`
3. `'label' + 'handler'() {}`
4. `meta.label + async submit() {}`
5. `children` 树中后代 `label` + 祖先 `onSelect() {}`

同时保留并通过既有场景：
- 属性赋值交互键场景（裸键/引号键/混合键）
- 祖先链场景（meta/props/extra/payload/children）
- J3/J4 反向测试全集

## 5. 真实长距离 fixture 与断言

保留并继续通过以下真实距离断言：

1. `Math.abs(content.indexOf('"label"') - content.indexOf('"onClick"')) > 1200`
2. `Math.abs(content.indexOf('onClick()') - content.indexOf('利润计算说明')) > 1200`

且保留 `assertDistanceGreaterThan(...)` 校验，确保不是源码文本伪距离。

## 6. 成功 fixture（继续通过）

1. 纯说明对象（无交互属性和交互方法）
2. 查看详情：`{ label: '查看详情', onClick: goDetail }`
3. 查询：`{ label: '查询', onClick: loadRows }`
4. 返回：`{ label: '返回', onClick: goBack }`
5. 只读帮助文案对象：`label: '利润计算说明'` + `description`（无交互成员）

## 7. 验证命令与结果

### 7.1 前端验证

1. `npm run check:style-profit-contracts`
   - 结果：通过（`Style-profit contract check passed. Scanned files: 24`）
2. `npm run test:style-profit-contracts`
   - 结果：通过（`All style-profit contract fixture tests passed. scenarios=48`）
3. `npm run verify`
   - 结果：通过（production/style-profit 契约、typecheck、build 全通过）
4. `npm audit --audit-level=high`
   - 结果：通过（`found 0 vulnerabilities`）

### 7.2 后端只读回归（未改后端）

1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：`34 passed, 1 warning`
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过

### 7.3 方法简写覆盖扫描

执行：

```bash
rg -n "onClick\s*\(|handler\s*\(|submit\s*\(|execute\s*\(|onSelect\s*\(|async\s+onClick|async\s+submit|['\"]onClick['\"]\s*\(|['\"]handler['\"]\s*\(|利润计算说明|利润率计算规则|利润快照来源说明|repeat\(1200\)|indexOf" \
  06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

结果：命中新增方法简写场景及真实距离断言。

### 7.4 业务禁线扫描

执行：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  06_前端/lingyi-pc/src
```

结果：无命中。

## 8. 提交摘要

`git show --stat --oneline --name-only 191dcee`：

```text
191dcee fix: detect style profit action method shorthand
06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs
06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

## 9. 结论

1. 对象方法简写交互字段绕过已修复。
2. 祖先链检测对属性赋值、引号键、方法简写、异步方法均生效。
3. 真实长距离 fixture 与断言有效保留。
4. 未开放创建快照入口。
5. 未进入 TASK-006。

