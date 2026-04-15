# TASK-005J8 跨行非字面量计算属性 Action 键门禁整改工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J8
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 20:07 CST
- 作者：技术架构师
- 前置审计：审计意见书第 126 份，`TASK-005J7` 有条件通过但存在高危跨行 computed key 绕过
- 当前有效前置：`TASK-005J7` 已能拦截普通非字面量 computed key，但 `[actionMap\n  .onClick]: openHelp` 仍可绕过
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V4.5；`ADR-121`

## 1. 任务目标

修复跨行非字面量 computed action key 绕过问题。当前 `check-style-profit-contracts.mjs` 已禁止普通 `[ACTION_KEY]`、`[actionMap.onClick]`、`[getActionKey()]`，但由于 computed key 捕获组排除了换行，表达式内部换行后仍可绕过，例如 `[actionMap\n  .onClick]: openHelp`。

本任务必须让 computed key 捕获支持跨行表达式，并继续区分“字符串字面量 computed key 可按既有规则处理”和“非字面量 computed key 必须失败”。本任务只修复前端契约门禁、测试和证据，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 126 份指出：

1. TASK-005J7 当前能拦截普通非字面量 computed key。
2. 但表达式内部换行仍可绕过：`[actionMap\n  .onClick]: openHelp`。
3. 根因是 `check-style-profit-contracts.mjs` 中 computed key 捕获组排除了换行。
4. 建议改为跨行捕获整个 `[...]` 表达式，并补对应反向测试。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 只读页面小范围修正

仅当现有只读页面被新门禁误杀时，允许小范围修正只读文案或只读配置：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J8_跨行非字面量计算属性Action键门禁整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J8_跨行非字面量计算属性Action键门禁整改证据.md`（交付时新建）
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
8. 禁止继续使用只匹配单行的 computed key 捕获组。
9. 禁止把跨行 computed key 放回固定窗口判断。
10. 禁止引入 AST 解析大改。
11. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 跨行 computed key 捕获

门禁必须能捕获完整跨行 `[...]` 表达式，至少覆盖：

1. `[actionMap\n  .onClick]: openHelp`
2. `[\n  ACTION_KEY\n]: openHelp`
3. `[getActionKey(\n  'profit'\n)]: openHelp`
4. `[actionMap\n  .onClick]() { openHelp() }`
5. `async [\n  ACTION_KEY\n]() { await submitProfit() }`

### 5.2 非字面量判断规则

跨行 computed key 捕获后，必须做规范化判断：

1. 去除首尾空白。
2. 保留内部换行语义，但允许用于判断时压缩空白。
3. 如果表达式整体是字符串字面量，例如 `'onClick'`、`"handler"`，则继续按 TASK-005J6 既有规则处理。
4. 如果表达式不是字符串字面量，例如 `ACTION_KEY`、`actionMap . onClick`、`getActionKey('profit')`，则在 style-profit action/menu/toolbar/button/command 语境下必须失败。

### 5.3 祖先链规则保持不变

跨行 computed key 修复不得削弱 TASK-005J3/J4/J5/J6/J7 的规则：

1. 子 `meta/props/extra/payload/children` 内出现利润说明类字段时，必须检查全部祖先对象。
2. 任一祖先对象存在交互属性、交互方法、字符串字面量 computed key 或非字面量 computed key 时，必须按规则处理。
3. 裸键、单引号键、双引号键、方法简写、计算属性键都必须识别。
4. 字段顺序不影响判断。
5. 字段距离不影响判断。
6. 真实长距离 fixture 必须继续保留。

## 6. 必补反向测试

必须在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs` 中补充以下失败用例：

### 6.1 跨行 [actionMap . onClick] 属性赋值

```ts
const actions = [
  {
    label: '利润计算说明',
    [actionMap
      .onClick]: openHelp,
  },
]
```

预期：门禁失败。

### 6.2 跨行 [ACTION_KEY] 属性赋值

```ts
const actions = [
  {
    label: '利润计算说明',
    [
      ACTION_KEY
    ]: openHelp,
  },
]
```

预期：门禁失败。

### 6.3 跨行 [getActionKey()] 属性赋值

```ts
const actions = [
  {
    label: '利润计算说明',
    [getActionKey(
      'profit'
    )]: openHelp,
  },
]
```

预期：门禁失败。

### 6.4 跨行 computed 方法简写

```ts
const actions = [
  {
    label: '利润计算说明',
    [actionMap
      .onClick]() {
      openHelp()
    },
  },
]
```

预期：门禁失败。

### 6.5 async 跨行 computed 方法简写 + 后代 label

```ts
const actions = [
  {
    meta: {
      label: '利润快照来源说明',
    },
    async [
      ACTION_KEY
    ]() {
      await submitProfit()
    },
  },
]
```

预期：门禁失败。

### 6.6 真实长距离跨行 computed key

```ts
const actions = [
  {
    label: '利润计算说明',
    filler: '<真实1200字符>',
    [actionMap
      .onClick]: openHelp,
  },
]
```

预期：门禁失败，并断言 `label` 与 `[actionMap` 的真实距离超过 1200。

## 7. 必保留成功测试

以下合法场景必须继续通过：

1. 字符串字面量 computed key：`['onClick']`、`["handler"]`、`['label']`。
2. 跨行字符串字面量 computed key，如：

```ts
const actions = [
  {
    [
      'label'
    ]: '利润计算说明',
    description: '只读说明',
  },
]
```

3. 纯说明对象，无任何祖先交互字段。
4. `查看详情` + `onClick: goDetail`。
5. `查询` + `onClick: loadRows`。
6. `返回` + `onClick: goBack`。

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

### 8.3 跨行 computed key 覆盖扫描

```bash
rg -n "actionMap|ACTION_KEY|getActionKey|跨行|non-literal computed|非字面量|computed action key|利润计算说明|利润快照来源说明|repeat\(1200\)|indexOf" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs
```

### 8.4 业务禁线扫描

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

## 9. 交付证据要求

工程师必须新建：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J8_跨行非字面量计算属性Action键门禁整改证据.md`

证据文件必须包含：

1. 修改文件清单。
2. 跨行 computed key 捕获实现说明。
3. 字符串字面量与非字面量 computed key 的判断规则。
4. 新增反向测试清单。
5. 合法跨行字符串字面量 computed key 成功 fixture。
6. 真实长距离 fixture 生成方式与距离断言结果。
7. 所有验证命令和结果。
8. 禁改范围扫描结果。
9. commit hash。
10. 是否引入 AST 解析：必须写“否，本任务仅增强跨行 computed key 捕获，不引入 AST”。

## 10. 提交要求

### 10.1 白名单 staged

只允许 staged：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- 必要时允许的 style_profit 只读页面小范围修正文件
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J8_跨行非字面量计算属性Action键门禁整改证据.md`
- 本任务相关架构、计划、审计文档

### 10.2 推荐提交信息

```bash
git commit -m "fix: detect multiline computed style profit action keys"
```

## 11. 验收标准

1. `[actionMap\n  .onClick]: openHelp` 必须失败。
2. `[\n  ACTION_KEY\n]: openHelp` 必须失败。
3. `[getActionKey(\n  'profit'\n)]: openHelp` 必须失败。
4. `[actionMap\n  .onClick]()` 必须失败。
5. `async [\n  ACTION_KEY\n]()` 必须失败。
6. 真实长距离跨行 computed key fixture 中 `label` 与 `[actionMap` 距离必须超过 1200 字符。
7. 跨行字符串字面量 computed key 继续按既有规则通过或失败，不得被误判为非字面量。
8. 纯说明对象无交互字段时继续通过。
9. `查看详情/查询/返回` 等只读动作继续通过。
10. `npm run test:style-profit-contracts` 通过。
11. `npm run verify` 通过。
12. `npm audit --audit-level=high` 为 0 high vulnerabilities。
13. 后端 style-profit API 定向回归通过。
14. 未引入 AST 解析大改。
15. 未开放创建快照入口。
16. 未进入 TASK-006。
