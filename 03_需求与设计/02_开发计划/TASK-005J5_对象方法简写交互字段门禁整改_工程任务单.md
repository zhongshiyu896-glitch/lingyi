# TASK-005J5 对象方法简写交互字段门禁整改工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J5
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 19:22 CST
- 作者：技术架构师
- 前置审计：审计意见书第 123 份，`TASK-005J4` 有条件通过但存在高危对象方法简写绕过
- 当前有效前置：`TASK-005J4` 已修复引号键与真实长距离主路径，但对象方法简写 `onClick() {}` 仍可绕过
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V4.2；`ADR-118`

## 1. 任务目标

修复对象方法简写交互字段绕过问题。当前 `check-style-profit-contracts.mjs` 的交互字段识别只覆盖 `onClick:`、`handler:` 等“键: 值”形式，不识别 `onClick() {}`、`handler() {}`、`submit() {}` 等对象方法简写。真实长距离场景下，窗口检测失效，门禁会放行带利润说明文案的交互 action。

本任务只修复前端契约门禁和反向测试，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 123 份指出以下样例仍可绕过：

```ts
{
  label: '利润计算说明',
  filler: '<真实1200字符>',
  onClick() {
    openHelp()
  },
}
```

根因：`actionInteractiveKeyRegex` 只识别 `onClick:` / `handler:`，不识别对象方法简写 `onClick() {}` / `handler() {}` / `submit() {}`。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 只读页面小范围修正

仅当现有只读页面被新门禁误杀时，允许小范围修正只读文案或只读配置：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J5_对象方法简写交互字段门禁整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J5_对象方法简写交互字段门禁整改证据.md`（交付时新建）
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
8. 禁止恢复 substring 白名单豁免。
9. 禁止只识别 `key: value`，忽略对象方法简写。
10. 禁止用固定窗口替代对象成员级识别。
11. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 对象方法简写识别

门禁必须同时识别以下交互成员形式：

1. 属性赋值：`onClick: openHelp`。
2. 引号属性赋值：`"onClick": openHelp`、`'onClick': openHelp`。
3. 方法简写：`onClick() { openHelp() }`。
4. 异步方法简写：`async onClick() { await openHelp() }`。
5. 引号方法名：`"onClick"() { openHelp() }`、`'onClick'() { openHelp() }`。
6. 其他交互方法：`handler() {}`、`submit() {}`、`execute() {}`、`onSelect() {}`、`command() {}`。

### 5.2 祖先链规则保持不变

对象方法简写修复不得削弱 TASK-005J3/J4 的规则：

1. 子 `meta/props/extra/payload/children` 内出现利润说明类字段时，必须检查全部祖先对象。
2. 任一祖先对象存在交互属性或交互方法时，必须失败。
3. 裸键、单引号键、双引号键都必须识别。
4. 字段顺序不影响判断。
5. 字段距离不影响判断。
6. 真实长距离 fixture 必须继续保留。

## 6. 必补反向测试

必须在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs` 中补充以下失败用例：

### 6.1 label + 真实 1200 字符 filler + onClick 方法简写

```ts
const actions = [
  {
    label: '利润计算说明',
    filler: '<真实1200字符>',
    onClick() {
      openHelp()
    },
  },
]
```

预期：门禁失败。

### 6.2 双引号 label + 双引号 onClick 方法名

```ts
const actions = [
  {
    "label": "利润计算说明",
    "onClick"() {
      openHelp()
    },
  },
]
```

预期：门禁失败。

### 6.3 单引号 label + 单引号 handler 方法名

```ts
const actions = [
  {
    'label': '利润率计算规则',
    'handler'() {
      showRule()
    },
  },
]
```

预期：门禁失败。

### 6.4 async submit 方法简写

```ts
const actions = [
  {
    meta: {
      label: '利润快照来源说明',
    },
    async submit() {
      await submitProfit()
    },
  },
]
```

预期：门禁失败。

### 6.5 children 中后代 label + 祖先 onSelect 方法简写

```ts
const menu = [
  {
    onSelect() {
      selectMenu()
    },
    children: [
      {
        meta: {
          label: '利润计算说明',
        },
      },
    ],
  },
]
```

预期：门禁失败。

### 6.6 真实距离断言

真实长距离方法简写 fixture 必须断言 `label` 与 `onClick` 的真实字符距离超过 1200：

```js
assert.ok(Math.abs(content.indexOf('onClick()') - content.indexOf('利润计算说明')) > 1200)
```

## 7. 必保留成功测试

以下合法只读场景必须继续通过：

1. 纯说明对象，无任何祖先交互字段。
2. `查看详情` + `onClick: goDetail`。
3. `查询` + `onClick: loadRows`。
4. `返回` + `onClick: goBack`。
5. 纯只读帮助文案对象中包含 `label: '利润计算说明'`，但无交互属性和交互方法。

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

### 8.3 方法简写覆盖扫描

```bash
rg -n "onClick\s*\(|handler\s*\(|submit\s*\(|execute\s*\(|onSelect\s*\(|async\s+onClick|async\s+submit|['\"]onClick['\"]\s*\(|['\"]handler['\"]\s*\(|利润计算说明|利润率计算规则|利润快照来源说明|repeat\(1200\)|indexOf" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

### 8.4 业务禁线扫描

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

## 9. 交付证据要求

工程师必须新建：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J5_对象方法简写交互字段门禁整改证据.md`

证据文件必须包含：

1. 修改文件清单。
2. 对象方法简写识别实现说明。
3. 新增反向测试清单。
4. 真实长距离 fixture 生成方式与距离断言结果。
5. 成功 fixture 清单。
6. 所有验证命令和结果。
7. 禁改范围扫描结果。
8. commit hash。

## 10. 提交要求

### 10.1 白名单 staged

只允许 staged：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- 必要时允许的 style_profit 只读页面小范围修正文件
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J5_对象方法简写交互字段门禁整改证据.md`
- 本任务相关架构、计划、审计文档

### 10.2 推荐提交信息

```bash
git commit -m "fix: detect style profit action method shorthand"
```

## 11. 验收标准

1. `label: '利润计算说明'` + `onClick() {}` 必须失败。
2. `"label": "利润计算说明"` + `"onClick"() {}` 必须失败。
3. `'label': '利润率计算规则'` + `'handler'() {}` 必须失败。
4. `async submit() {}` 与后代利润说明 label 必须失败。
5. `children` 菜单树中祖先 `onSelect() {}` 必须失败。
6. 方法简写真实长距离 fixture 中 `label` 与 `onClick()` 距离必须超过 1200 字符。
7. 属性赋值、引号键、祖先链既有反向测试继续通过。
8. 纯说明对象无交互属性和交互方法时继续通过。
9. `查看详情/查询/返回` 等只读动作继续通过。
10. `npm run test:style-profit-contracts` 通过。
11. `npm run verify` 通过。
12. `npm audit --audit-level=high` 为 0 high vulnerabilities。
13. 后端 style-profit API 定向回归通过。
14. 未开放创建快照入口。
15. 未进入 TASK-006。
