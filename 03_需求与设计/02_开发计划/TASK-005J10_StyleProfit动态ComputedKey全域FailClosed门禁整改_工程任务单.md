# TASK-005J10 Style Profit 动态 Computed Key 全域 Fail Closed 门禁整改工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J10
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 20:45 CST
- 作者：技术架构师
- 前置审计：审计意见书第 128 份，`TASK-005J9` 有条件通过但存在高危中性容器名绕过
- 当前有效 HEAD：`6323646a3fa15cb55676af9baee850adea36afac`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V4.7；`ADR-123`

## 1. 任务目标

修复 AST 化后仍依赖 `actions/menu/button` 等 action-like 容器名导致的绕过。当前 `TASK-005J9` 已能识别 `[actionMap['onClick']]`、模板字符串 key、spread 风险，但如果对象命名为中性名称，例如 `items`，动态 computed key 仍会通过。

本任务要求：在 style-profit surface 内，对所有 `dynamic_computed_key / unknown_key` 全域 fail closed，不再依赖变量名、数组名或容器名是否为 `actions/menu/button/toolbar`。只要对象字面量中出现动态或未知 computed key，即视为门禁失败；字符串字面量 computed key 继续按既有规则处理。

本任务只修复前端契约门禁、测试和证据，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 128 份指出以下样例仍可绕过：

```ts
const ACTION_KEY = 'onClick'
const items = [
  {
    label: '查看详情',
    [ACTION_KEY]: goDetail,
  },
]
```

根因：AST 逻辑仍依赖 `actions/menu/button` 等 action-like 容器名。对象变量名为 `items` 这类中性名称时，动态 computed key 未被 fail closed。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 前端约定文档

如需记录门禁边界，可追加：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/README.md`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J10_StyleProfit动态ComputedKey全域FailClosed门禁整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J10_StyleProfit动态ComputedKey全域FailClosed门禁整改证据.md`（交付时新建）
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/当前 sprint 任务清单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/03_技术决策记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/架构师会话日志.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录/审计官会话日志.md`

## 4. 禁止修改文件与行为

1. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/**`。
2. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/.github/**`。
3. 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`。
4. 禁止创建或修改任何 `TASK-006*` 文件。
5. 禁止提交 `.pytest-postgresql-*.xml`。
6. 禁止新增 `POST /api/reports/style-profit/snapshots` 的前端调用。
7. 禁止开放创建/生成/重算利润快照入口。
8. 禁止继续依赖 `actions/menu/button/toolbar/items` 等容器名判断动态 computed key 是否危险。
9. 禁止把 `label: '查看详情'`、`label: '查询'`、`label: '返回'` 作为动态 computed key 的豁免理由。
10. 禁止新增第三方 parser 依赖；继续使用已有 `typescript` devDependency。
11. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 Style-profit surface 内动态 key 全域 fail closed

在 style-profit 契约门禁中，凡进入 style-profit surface 的源码或 fixture，只要任一 `ObjectLiteralExpression` 出现以下对象成员，必须失败：

1. `dynamic_computed_key`
2. `unknown_key`
3. AST 无法安全归类的 computed key
4. SpreadAssignment 无法安全解析且对象中存在 label/title/name/text/description/tooltip 等展示字段

不得再要求对象变量名必须叫 `actions`、`menus`、`buttons`、`toolbar` 才触发失败。

### 5.2 字符串字面量 computed key 继续按既有规则处理

以下仍属于 `literal_key`，不得误判为 dynamic：

1. `['onClick']`
2. `["handler"]`
3. `['label']`
4. `[
  'label'
]`
5. `[
  "onClick"
]`

这些 key 是否失败，继续按既有 style-profit 只读门禁、祖先链和语义禁线判断。

### 5.3 中性容器名不得豁免

以下变量名或对象名不得影响判断结果：

1. `items`
2. `rows`
3. `configs`
4. `columns`
5. `entries`
6. `options`
7. `list`
8. 任意未知命名

只要对象字面量里出现 dynamic / unknown computed key，即 fail closed。

### 5.4 失败提示

门禁失败信息必须明确提示：

```text
style-profit forbids dynamic or unknown computed keys in object literals; use explicit literal keys
```

中文可补充：

```text
款式利润前端禁止动态或无法静态确认的计算属性键，请使用显式字面量键
```

## 6. 必补反向测试

必须在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs` 中补充以下失败用例：

### 6.1 中性 items 容器 + [ACTION_KEY]

```ts
const ACTION_KEY = 'onClick'
const items = [
  {
    label: '查看详情',
    [ACTION_KEY]: goDetail,
  },
]
```

预期：门禁失败。

### 6.2 中性 rows 容器 + [actionMap['onClick']]

```ts
const rows = [
  {
    label: '查询',
    [actionMap['onClick']]: loadRows,
  },
]
```

预期：门禁失败。

### 6.3 中性 configs 容器 + [getActionKey()]

```ts
const configs = [
  {
    label: '返回',
    [getActionKey()]: goBack,
  },
]
```

预期：门禁失败。

### 6.4 中性 columns 容器 + dynamic label key

```ts
const columns = [
  {
    [labelKey]: '利润计算说明',
    description: '只读说明',
  },
]
```

预期：门禁失败。

### 6.5 unknown computed key fail closed

```ts
const items = [
  {
    label: '查看详情',
    [unknownKeyFactory()]: goDetail,
  },
]
```

预期：门禁失败。

### 6.6 Vue script setup 中中性容器名

```vue
<script setup lang="ts">
const ACTION_KEY = 'onClick'
const items = [
  {
    label: '查看详情',
    [ACTION_KEY]: goDetail,
  },
]
</script>
```

预期：门禁失败。

### 6.7 真实长距离 + 中性容器名

```ts
const items = [
  {
    label: '查看详情',
    filler: '<真实1200字符>',
    [ACTION_KEY]: goDetail,
  },
]
```

预期：门禁失败，并断言 `label` 与 `[ACTION_KEY]` 的真实距离超过 1200。

## 7. 必保留成功测试

以下合法场景必须继续通过：

1. 字符串字面量 computed key：`['onClick']`、`["handler"]`、`['label']`。
2. 跨行字符串字面量 computed key。
3. 纯说明对象，无 dynamic / unknown computed key。
4. `查看详情` + `onClick: goDetail`。
5. `查询` + `onClick: loadRows`。
6. `返回` + `onClick: goBack`。
7. Vue template 只读说明文案成功 fixture。

## 8. 验证命令

### 8.1 前端验证

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

### 8.2 后端只读回归

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

### 8.3 全域 fail closed 覆盖扫描

```bash
rg -n "dynamic_computed_key|unknown_key|items|rows|configs|columns|ACTION_KEY|labelKey|unknownKeyFactory|style-profit forbids dynamic|全域|fail closed|ObjectLiteralExpression" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

### 8.4 业务禁线扫描

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

## 9. 交付证据要求

工程师必须新建：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J10_StyleProfit动态ComputedKey全域FailClosed门禁整改证据.md`

证据文件必须包含：

1. 修改文件清单。
2. dynamic / unknown computed key 全域 fail closed 实现说明。
3. 删除或绕开 action-like 容器名依赖的说明。
4. 新增反向测试清单。
5. 合法字符串字面量 computed key 成功 fixture 清单。
6. 真实长距离 fixture 生成方式与距离断言结果。
7. 所有验证命令和结果。
8. 禁改范围扫描结果。
9. commit hash。
10. 是否新增依赖：必须写“否，继续使用现有 typescript devDependency”。

## 10. 提交要求

### 10.1 白名单 staged

只允许 staged：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- 必要时允许的 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/README.md`
- 必要时允许的 style_profit 只读页面小范围修正文件
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J10_StyleProfit动态ComputedKey全域FailClosed门禁整改证据.md`
- 本任务相关架构、计划、审计文档

### 10.2 推荐提交信息

```bash
git commit -m "fix: fail closed dynamic style profit computed keys"
```

## 11. 验收标准

1. `const items = [{ label: '查看详情', [ACTION_KEY]: goDetail }]` 必须失败。
2. `const rows = [{ label: '查询', [actionMap['onClick']]: loadRows }]` 必须失败。
3. `const configs = [{ label: '返回', [getActionKey()]: goBack }]` 必须失败。
4. `const columns = [{ [labelKey]: '利润计算说明' }]` 必须失败。
5. Vue script setup 中中性容器名 + dynamic computed key 必须失败。
6. 真实长距离 + 中性容器名 + dynamic computed key 必须失败，且距离断言超过 1200。
7. 门禁不再依赖 `actions/menu/button/toolbar` 等容器名才判定 dynamic key 风险。
8. 字符串字面量 computed key 既有测试继续通过或按既有利润门禁失败。
9. Vue script / script setup 中的对象必须被 AST 扫描覆盖。
10. Vue template 文本禁线既有测试不回退。
11. `npm run test:style-profit-contracts` 通过。
12. `npm run verify` 通过。
13. `npm audit --audit-level=high` 为 0 high vulnerabilities。
14. 后端 style-profit API 定向回归通过。
15. 未新增第三方 parser 依赖。
16. 未开放创建快照入口。
17. 未进入 TASK-006。
