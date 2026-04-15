# TASK-005J7 非字面量计算属性 Action 键禁用门禁工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J7
- 优先级：P2
- 版本：V1.0
- 更新时间：2026-04-14 19:51 CST
- 作者：技术架构师
- 前置审计：审计意见书第 125 份，`TASK-005J6` 通过但保留非字面量 computed action key 风险
- 当前有效 HEAD：`64a5254fe92f07edd3f4a959ad7dc0ef51871b03`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V4.4；`ADR-120`

## 1. 任务目标

将审计意见书第 125 份中的剩余风险转为明确前端约定和门禁：style-profit 业务面禁止使用非字面量 computed action key，例如 `[ACTION_KEY]: openHelp`、`[actionMap.onClick]()`、`[getActionKey()]: handler`。当前正则静态门禁已覆盖裸键、引号键、方法简写、字符串字面量计算属性键，但无法可靠解析运行时表达式键；因此本任务要求直接禁止此类写法，并补反向测试。

本任务只修复前端契约门禁、测试和证据，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 125 份结论为 `TASK-005J6` 通过，但指出以下风险：

1. 非字面量计算属性键仍属于正则静态门禁天然边界。
2. 示例：`[ACTION_KEY]: openHelp`、`[actionMap.onClick]()`。
3. 建议在 style-profit 前端约定中禁止非字面量 computed action key。
4. 如果未来确实要支持，应升级 TypeScript/Babel AST 解析，而不是继续叠正则窗口。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 前端约定文档

如仓库已有前端 README 或规范文件，可追加 style-profit 约定：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/README.md`

若没有合适位置，则只在证据文档记录该约定，不强制新增前端规范文件。

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J7_非字面量计算属性Action键禁用门禁_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J7_非字面量计算属性Action键禁用门禁证据.md`（交付时新建）
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
8. 禁止继续扩展固定窗口来处理非字面量 key。
9. 禁止允许 `[ACTION_KEY]`、`[actionMap.onClick]`、`[getActionKey()]` 等非字面量 action key 出现在 style-profit 业务面。
10. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 禁止非字面量 computed action key

在 style-profit 契约门禁中新增规则：只要 style-profit 业务面出现非字面量 computed key，且疑似 action / menu / toolbar / button / command 配置，必须失败。

必须禁止：

1. `[ACTION_KEY]: openHelp`
2. `[actionMap.onClick]: openHelp`
3. `[getActionKey()]: openHelp`
4. `[ACTION_KEY]() { openHelp() }`
5. `async [ACTION_KEY]() { await openHelp() }`
6. `[dynamicLabel]: '利润计算说明'`
7. `[metaKey]: { label: '利润计算说明' }`

允许保留：

1. 字符串字面量 computed key：`['onClick']`、`["handler"]`、`['label']`。
2. 不在 style-profit 业务面、且不属于 action/menu/toolbar/button/command 配置的普通非业务代码，除非已被全局禁线命中。

### 5.2 失败提示

门禁失败信息必须明确提示：

```text
style-profit forbids non-literal computed action keys; use explicit onClick/handler/command keys or quoted literal computed keys
```

中文可补充：

```text
款式利润前端禁止非字面量计算属性 action key，请使用显式键名
```

### 5.3 不升级 AST 的边界说明

本任务不要求引入 TypeScript/Babel AST 解析。当前决策是：

1. 短期：禁止非字面量 computed action key。
2. 中期：如果确需支持动态 action key，再单独立项升级 AST 解析。
3. 不允许在本任务中引入大规模解析器重构，避免门禁本身变成新风险。

## 6. 必补反向测试

必须在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs` 中补充以下失败用例：

### 6.1 [ACTION_KEY] 属性赋值

```ts
const ACTION_KEY = 'onClick'
const actions = [
  {
    label: '利润计算说明',
    [ACTION_KEY]: openHelp,
  },
]
```

预期：门禁失败。

### 6.2 [actionMap.onClick] 属性赋值

```ts
const actions = [
  {
    label: '利润计算说明',
    [actionMap.onClick]: openHelp,
  },
]
```

预期：门禁失败。

### 6.3 [getActionKey()] 属性赋值

```ts
const actions = [
  {
    label: '利润计算说明',
    [getActionKey()]: openHelp,
  },
]
```

预期：门禁失败。

### 6.4 [ACTION_KEY]() 方法简写

```ts
const actions = [
  {
    label: '利润计算说明',
    [ACTION_KEY]() {
      openHelp()
    },
  },
]
```

预期：门禁失败。

### 6.5 async [ACTION_KEY]() 方法简写

```ts
const actions = [
  {
    meta: {
      label: '利润快照来源说明',
    },
    async [ACTION_KEY]() {
      await submitProfit()
    },
  },
]
```

预期：门禁失败。

### 6.6 动态 label key

```ts
const actions = [
  {
    onClick: openHelp,
    [labelKey]: '利润计算说明',
  },
]
```

预期：门禁失败。

## 7. 必保留成功测试

以下合法场景必须继续通过：

1. 字符串字面量 computed action key：`['onClick']: openHelp`，在非利润写入口白名单场景中按既有规则处理。
2. 字符串字面量 computed label key：`['label']: '利润计算说明'`，无祖先交互字段时通过。
3. `查看详情` + `onClick: goDetail`。
4. `查询` + `onClick: loadRows`。
5. `返回` + `onClick: goBack`。
6. 纯说明对象，无任何交互字段。

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

### 8.3 非字面量 computed key 覆盖扫描

```bash
rg -n "\[ACTION_KEY\]|\[actionMap\.onClick\]|\[getActionKey\(\)\]|\[labelKey\]|non-literal computed|非字面量|computed action key|利润计算说明|利润快照来源说明" \
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

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J7_非字面量计算属性Action键禁用门禁证据.md`

证据文件必须包含：

1. 修改文件清单。
2. 非字面量 computed action key 禁用实现说明。
3. 新增反向测试清单。
4. 合法字面量 computed key 成功 fixture 清单。
5. 所有验证命令和结果。
6. 禁改范围扫描结果。
7. commit hash。
8. 是否引入 AST 解析：必须写“否，本任务仅禁用非字面量 computed key”。

## 10. 提交要求

### 10.1 白名单 staged

只允许 staged：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- 必要时允许的 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/README.md`
- 必要时允许的 style_profit 只读页面小范围修正文件
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J7_非字面量计算属性Action键禁用门禁证据.md`
- 本任务相关架构、计划、审计文档

### 10.2 推荐提交信息

```bash
git commit -m "fix: forbid dynamic style profit action keys"
```

## 11. 验收标准

1. `[ACTION_KEY]: openHelp` 在 style-profit action 配置中必须失败。
2. `[actionMap.onClick]: openHelp` 必须失败。
3. `[getActionKey()]: openHelp` 必须失败。
4. `[ACTION_KEY]() {}` 必须失败。
5. `async [ACTION_KEY]() {}` 必须失败。
6. `[labelKey]: '利润计算说明'` + 祖先交互字段必须失败。
7. `['onClick']`、`["handler"]`、`['label']` 等字符串字面量 computed key 既有测试继续通过或按既有利润门禁失败。
8. 纯说明对象无交互字段时继续通过。
9. `查看详情/查询/返回` 等只读动作继续通过。
10. `npm run test:style-profit-contracts` 通过。
11. `npm run verify` 通过。
12. `npm audit --audit-level=high` 为 0 high vulnerabilities。
13. 后端 style-profit API 定向回归通过。
14. 未引入 AST 解析大改。
15. 未开放创建快照入口。
16. 未进入 TASK-006。
