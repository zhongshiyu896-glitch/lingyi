# TASK-005J3 Action 祖先对象链门禁整改工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J3
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 18:48 CST
- 作者：技术架构师
- 前置审计：审计意见书第 121 份，`TASK-005J2` 有条件通过但存在高危嵌套 metadata 绕过
- 当前有效前置：`TASK-005J2` 官方门禁与回归通过，但审计临时 fixture 复现父 action + 子 meta label 绕过
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V4.0；`ADR-116`

## 1. 任务目标

修复 action 对象检测中的祖先链绕过问题。当前 `check-style-profit-contracts.mjs` 会按最小子对象先处理 `meta: { label: '利润计算说明' }`，并把它误判为只读 label；但该 `meta` 位于带 `onClick` 的父 action 对象内，实际仍属于可点击入口。TASK-005J3 必须新增祖先对象链检测：任一子对象、meta、payload、extra、props、children 节点内出现利润说明类 label 时，必须向上检查全部祖先对象，只要祖先存在交互字段，就按交互入口失败。

本任务只修复前端契约门禁和反向测试，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 121 份指出：

1. TASK-005J2 官方门禁和回归均通过。
2. 但审计临时 fixture 复现：父对象存在 `onClick`，子对象 `meta` 内存在 `label: '利润计算说明'` 时仍可绕过。
3. 根因是脚本按最小子对象先放行只读 label，没有检查所有祖先 action 对象。
4. 该绕过属于高危，因为真实前端常把菜单、toolbar、操作按钮的文案放在 `meta/props/extra` 中。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 只读页面小范围修正

仅当现有只读页面被新门禁误杀时，允许小范围修正只读文案或只读配置：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J3_Action祖先对象链门禁整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J3_Action祖先对象链门禁整改证据.md`（交付时新建）
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
9. 禁止把祖先链检测退化为固定字符窗口检测。
10. 禁止只检查最小子对象后直接放行。
11. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 祖先对象链检测

必须实现祖先对象链检测，至少覆盖以下模式：

1. 父 action 对象有 `onClick`，子 `meta` 内有 `label: '利润计算说明'`。
2. 父 action 对象有 `handler`，子 `props` 内有 `label: '利润率计算规则'`。
3. 父 action 对象有 `command`，子 `extra` 内有 `label: '利润快照来源说明'`。
4. 父 action 对象有 `onSelect`，子 `payload` 内有 `title: '利润计算说明'`。
5. `children` 菜单树中，祖先节点存在交互字段，后代节点存在利润说明 label/title。
6. 多级嵌套对象中，利润说明 label 与祖先交互字段间隔超过 300、500、1000 字符仍必须失败。

### 5.2 交互字段集合

祖先链检测必须至少识别以下交互字段：

1. `onClick`
2. `handler`
3. `action`
4. `command`
5. `onSelect`
6. `onCommand`
7. `callback`
8. `execute`
9. `submit`
10. `to` 或 `path` 指向非详情只读导航且语义为创建/生成/重算/计算入口时

### 5.3 利润说明字段集合

祖先链检测必须至少识别以下字段中的利润说明文案：

1. `label`
2. `title`
3. `text`
4. `name`
5. `tooltip`
6. `description`
7. `meta.label`
8. `meta.title`
9. `props.label`
10. `extra.label`

### 5.4 不允许的实现方式

1. 不允许只用 `content.slice(index - 300, index + 300)` 判断。
2. 不允许只解析最小 `{ label: ... }` 子对象。
3. 不允许将 `meta/props/extra/payload` 默认视为只读安全对象。
4. 不允许对 `利润计算说明`、`利润率计算规则`、`利润快照来源说明` 做 substring 白名单。
5. 不允许新增全文件 ignore 或目录 ignore。

## 6. 必补反向测试

必须在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs` 中补充以下失败用例：

### 6.1 父 onClick + 子 meta label

```ts
const actions = [
  {
    key: 'profit-help',
    onClick: openHelp,
    meta: {
      label: '利润计算说明',
    },
  },
]
```

预期：门禁失败。

### 6.2 父 handler + 子 props label

```ts
const actions = [
  {
    handler: showRule,
    props: {
      label: '利润率计算规则',
    },
  },
]
```

预期：门禁失败。

### 6.3 父 command + 子 extra label

```ts
const menus = [
  {
    command: 'open-profit-source-help',
    extra: {
      label: '利润快照来源说明',
    },
  },
]
```

预期：门禁失败。

### 6.4 祖先交互字段与后代 label 间隔超过 1000 字符

```ts
const actions = [
  {
    onClick: openHelp,
    filler: 'x'.repeat(1200),
    meta: {
      label: '利润计算说明',
    },
  },
]
```

预期：门禁失败。

### 6.5 children 嵌套菜单树

```ts
const menu = [
  {
    onSelect: selectMenu,
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

## 7. 必保留成功测试

以下合法只读场景必须继续通过：

1. 纯说明对象，无任何祖先交互字段：

```ts
const help = {
  meta: {
    label: '利润计算说明',
  },
  description: '只读帮助文案',
}
```

2. 详情只读导航：

```ts
const actions = [
  {
    label: '查看详情',
    onClick: goDetail,
  },
]
```

3. 查询只读动作：

```ts
const actions = [
  {
    label: '查询',
    onClick: loadRows,
  },
]
```

4. 返回动作：

```ts
const actions = [
  {
    label: '返回',
    onClick: goBack,
  },
]
```

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

### 8.3 祖先链反向测试覆盖扫描

```bash
rg -n "meta|props|extra|payload|children|onClick|handler|command|onSelect|onCommand|callback|execute|利润计算说明|利润率计算规则|利润快照来源说明|repeat\(1200\)" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

### 8.4 业务禁线扫描

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

## 9. 交付证据要求

工程师必须新建：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J3_Action祖先对象链门禁整改证据.md`

证据文件必须包含：

1. 修改文件清单。
2. 祖先对象链检测实现说明。
3. 新增反向测试清单。
4. 成功 fixture 清单。
5. 所有验证命令和结果。
6. 禁改范围扫描结果。
7. 是否存在误杀及处理说明。
8. commit hash。

## 10. 提交要求

### 10.1 白名单 staged

只允许 staged：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- 必要时允许的 style_profit 只读页面小范围修正文件
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J3_Action祖先对象链门禁整改证据.md`
- 本任务相关架构、计划、审计文档

### 10.2 推荐提交信息

```bash
git commit -m "fix: check style profit action ancestor chain"
```

## 11. 验收标准

1. 父 action 对象有 `onClick`，子 `meta.label='利润计算说明'` 时门禁失败。
2. 父 action 对象有 `handler/command/onSelect`，子 `props/extra/payload/meta` 出现利润说明文案时门禁失败。
3. 祖先交互字段与后代利润说明文案间隔超过 1000 字符仍失败。
4. `children` 菜单树中的祖先交互字段能够被识别。
5. 纯说明对象无祖先交互字段时继续通过。
6. `查看详情/查询/返回` 等只读动作继续通过。
7. `npm run test:style-profit-contracts` 通过。
8. `npm run verify` 通过。
9. `npm audit --audit-level=high` 为 0 high vulnerabilities。
10. 后端 style-profit API 定向回归通过。
11. 未开放创建快照入口。
12. 未进入 TASK-006。
