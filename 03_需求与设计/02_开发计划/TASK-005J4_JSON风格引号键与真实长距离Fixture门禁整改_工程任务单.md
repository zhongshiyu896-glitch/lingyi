# TASK-005J4 JSON 风格引号键与真实长距离 Fixture 门禁整改工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J4
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 19:07 CST
- 作者：技术架构师
- 前置审计：审计意见书第 122 份，`TASK-005J3` 有条件通过但存在高危 JSON 风格引号键绕过
- 当前有效前置：`TASK-005J3` 已修复未加引号对象键的祖先链绕过，但 JSON 风格引号键仍可绕过
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V4.1；`ADR-117`

## 1. 任务目标

修复 JSON 风格引号键绕过问题。当前 `check-style-profit-contracts.mjs` 能识别未加引号对象键，但当父对象使用 `"onClick": openHelp`、子对象使用 `"label": "利润计算说明"` 时，祖先链检测仍会漏判。TASK-005J4 必须让门禁同时识别裸键、单引号键、双引号键，并补真实 1200 字符距离 fixture，不能再用源码文本 `'x'.repeat(1200)` 冒充长距离。

本任务只修复前端契约门禁和反向测试，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 122 份指出：

1. TASK-005J3 已修复未加引号对象键的祖先链绕过。
2. JSON 风格引号键仍可绕过：父对象使用 `"onClick": openHelp`，子对象使用 `"label": "利润计算说明"`。
3. 中间插入真实 1200 字符 filler 后，`check-style-profit-contracts.mjs --project-root <tmp>` 仍返回通过。
4. 现有 `repeat(1200)` fixture 写入的是源码文本 `'x'.repeat(1200)`，不是实际 1200 字符距离，长距离覆盖证据偏弱。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 只读页面小范围修正

仅当现有只读页面被新门禁误杀时，允许小范围修正只读文案或只读配置：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J4_JSON风格引号键与真实长距离Fixture门禁整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J4_JSON风格引号键与真实长距离Fixture门禁整改证据.md`（交付时新建）
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
9. 禁止只支持未加引号对象键。
10. 禁止继续使用源码文本 `'x'.repeat(1200)` 作为长距离 fixture 证据。
11. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 引号键识别

门禁必须同时识别以下键格式：

1. 裸键：`onClick: openHelp`、`label: '利润计算说明'`。
2. 单引号键：`'onClick': openHelp`、`'label': '利润计算说明'`。
3. 双引号键：`"onClick": openHelp`、`"label": "利润计算说明"`。
4. 混合风格：父对象双引号交互键、子对象裸 label；父对象裸交互键、子对象双引号 label。
5. 嵌套键：`"meta": { "label": "利润计算说明" }`、`"props": { "label": "利润率计算规则" }`。

### 5.2 祖先链规则保持不变

引号键修复不得削弱 TASK-005J3 的祖先链规则：

1. 子 `meta/props/extra/payload/children` 内出现利润说明类字段时，必须检查全部祖先对象。
2. 任一祖先对象存在 `onClick/handler/action/command/onSelect/onCommand/callback/execute` 等交互字段时，必须失败。
3. 字段顺序不影响判断。
4. 字段距离不影响判断。

### 5.3 真实长距离 Fixture

必须把长距离 fixture 改为真实长字符串，而不是源码文本表达式。

错误示例：

```ts
filler: 'x'.repeat(1200),
```

正确方式示例：测试脚本生成临时 fixture 内容时，实际写入 1200 个以上字符：

```js
const longFiller = 'x'.repeat(1200)
const content = `
const actions = [{
  "onClick": openHelp,
  "filler": "${longFiller}",
  "meta": {
    "label": "利润计算说明"
  }
}]
`
```

验收时必须能从临时文件或测试构造内容中证明 `onClick` 与 `label` 的真实字符距离超过 1200。

## 6. 必补反向测试

必须在 `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs` 中补充以下失败用例：

### 6.1 双引号 onClick + 双引号 meta.label + 真实 1200 字符 filler

```ts
const actions = [
  {
    "onClick": openHelp,
    "filler": "这里必须是实际 1200 个以上字符，不是 repeat 表达式",
    "meta": {
      "label": "利润计算说明"
    }
  }
]
```

预期：门禁失败。

### 6.2 单引号 handler + 单引号 props.label

```ts
const actions = [
  {
    'handler': showRule,
    'props': {
      'label': '利润率计算规则',
    },
  },
]
```

预期：门禁失败。

### 6.3 混合风格 command + extra.label

```ts
const menus = [
  {
    "command": 'open-profit-source-help',
    extra: {
      "label": '利润快照来源说明',
    },
  },
]
```

预期：门禁失败。

### 6.4 双引号 children 菜单树

```ts
const menu = [
  {
    "onSelect": selectMenu,
    "children": [
      {
        "meta": {
          "label": "利润计算说明"
        }
      }
    ]
  }
]
```

预期：门禁失败。

### 6.5 真实距离断言

测试脚本必须增加断言，证明 fixture 中交互字段和利润说明 label 的真实字符距离超过 1200：

```js
assert.ok(Math.abs(content.indexOf('"label"') - content.indexOf('"onClick"')) > 1200)
```

## 7. 必保留成功测试

以下合法只读场景必须继续通过：

1. 纯说明对象，无任何祖先交互字段：

```ts
const help = {
  "meta": {
    "label": "利润计算说明"
  },
  "description": "只读帮助文案"
}
```

2. 详情只读导航：

```ts
const actions = [
  {
    "label": "查看详情",
    "onClick": goDetail,
  },
]
```

3. 查询只读动作：

```ts
const actions = [
  {
    "label": "查询",
    "onClick": loadRows,
  },
]
```

4. 返回动作：

```ts
const actions = [
  {
    "label": "返回",
    "onClick": goBack,
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

### 8.3 引号键与真实长距离覆盖扫描

```bash
rg -n '"onClick"|"label"|\x27onClick\x27|\x27label\x27|longFiller|indexOf\(.*onClick|indexOf\(.*label|repeat\(1200\)|真实 1200|利润计算说明|利润率计算规则|利润快照来源说明' \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

### 8.4 禁止伪长距离扫描

```bash
rg -n "filler:\s*['\"]x['\"]\.repeat\(1200\)|['\"]x['\"]\.repeat\(1200\).*label|repeat\(1200\).*不是实际" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

### 8.5 业务禁线扫描

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

## 9. 交付证据要求

工程师必须新建：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J4_JSON风格引号键与真实长距离Fixture门禁整改证据.md`

证据文件必须包含：

1. 修改文件清单。
2. 引号键识别实现说明。
3. 真实长距离 fixture 生成方式。
4. `onClick` 与 `label` 真实距离断言结果。
5. 新增反向测试清单。
6. 成功 fixture 清单。
7. 所有验证命令和结果。
8. 禁改范围扫描结果。
9. commit hash。

## 10. 提交要求

### 10.1 白名单 staged

只允许 staged：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- 必要时允许的 style_profit 只读页面小范围修正文件
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J4_JSON风格引号键与真实长距离Fixture门禁整改证据.md`
- 本任务相关架构、计划、审计文档

### 10.2 推荐提交信息

```bash
git commit -m "fix: detect quoted style profit action keys"
```

## 11. 验收标准

1. `"onClick": openHelp` + `"meta": { "label": "利润计算说明" }` 必须失败。
2. `'handler': showRule` + `'props': { 'label': '利润率计算规则' }` 必须失败。
3. 混合引号键与裸键组合必须失败。
4. 双引号 `children` 菜单树祖先交互字段必须失败。
5. 真实长距离 fixture 中 `onClick` 与 `label` 的距离必须超过 1200 字符。
6. 不得再用源码文本 `'x'.repeat(1200)` 冒充长距离。
7. 纯说明对象无祖先交互字段时继续通过。
8. `查看详情/查询/返回` 等只读动作继续通过。
9. `npm run test:style-profit-contracts` 通过。
10. `npm run verify` 通过。
11. `npm audit --audit-level=high` 为 0 high vulnerabilities。
12. 后端 style-profit API 定向回归通过。
13. 未开放创建快照入口。
14. 未进入 TASK-006。
