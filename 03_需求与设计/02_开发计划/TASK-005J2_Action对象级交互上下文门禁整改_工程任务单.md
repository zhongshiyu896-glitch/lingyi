# TASK-005J2 Action 对象级交互上下文门禁整改工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J2
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 18:28 CST
- 作者：技术架构师
- 前置审计：审计意见书第 120 份，`TASK-005J1` 有条件通过但存在高危绕过
- 当前有效 HEAD：`5e5fd80e2a83f8b7e6a0099bf0e215f31e0067ba`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V3.9；`ADR-115`

## 1. 任务目标

修复长多行 action 配置绕过门禁的问题。当前门禁依赖固定半径窗口，当 `label: '利润计算说明'` 与 `onClick` 间隔超过 300 字符时，会漏判交互入口。TASK-005J2 必须将 action 配置检测升级为对象级/block 级检测，不再依赖固定窗口距离。

本任务只修复前端契约门禁和反向测试，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 120 份指出：

1. TASK-005J1 已修复多行按钮和菜单绕过。
2. 但长多行 action 配置中，`label` 与 `onClick` 间隔超过窗口半径时仍能绕过。
3. 示例：`label: '利润计算说明'` 与 `onClick: openHelp` 中间插入超过 300 字符的配置项。
4. 该绕过属于高危，因为 action 配置通常用于菜单、按钮组、toolbar 操作区。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 只读页面小范围修正

仅当现有只读页面被新门禁误杀时，允许小范围修正只读文案：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J2_Action对象级交互上下文门禁整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J2_Action对象级交互上下文门禁整改证据.md`（交付时新建）
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
9. 禁止把 action 对象检测继续建立在固定 300 字符窗口上。
10. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 Action 对象级检测

必须新增对象级/block 级 action 检测，识别以下结构：

1. `const actions = [{ label: '利润计算说明', onClick: openHelp }]`。
2. 多行对象：

```ts
const actions = [
  {
    label: '利润计算说明',
    disabled: false,
    type: 'default',
    // 中间可以有很多配置
    onClick: openHelp,
  },
]
```

3. 对象属性顺序反过来：

```ts
{
  onClick: openHelp,
  label: '利润计算说明',
}
```

4. `handler`、`action`、`command`、`onSelect` 等等价交互字段与 label 同对象出现。
5. `children` 菜单树内的 action 节点。

### 5.2 不再依赖固定窗口

固定窗口可以保留作为辅助，但不得作为 action 配置判断的唯一依据。对象级检测必须覆盖 label 与 onClick 间隔超过 300 字符、500 字符、1000 字符的情况。

### 5.3 必须失败的新增反向测试

`test-style-profit-contracts.mjs` 必须新增以下用例，且均失败：

1. `label` 与 `onClick` 间隔超过 300 字符：

```ts
const actions = [
  {
    label: '利润计算说明',
    description: 'x'.repeat(400),
    onClick: openHelp,
  },
]
```

2. `onClick` 在前、`label` 在后，间隔超过 300 字符。
3. `label: '利润率计算规则'` 与 `handler` 同对象出现。
4. `label: '利润快照来源说明'` 与 `command` 同对象出现。
5. 嵌套 `children` 菜单中 `label: '利润计算说明'` 与 `onSelect` 同节点出现。

### 5.4 合法 action 仍需通过

以下场景必须通过：

1. 纯展示对象：`{ label: '利润计算说明', description: '只读帮助文案' }`，没有任何交互字段。
2. 非利润动作对象：`{ label: '返回', onClick: goBack }`。
3. 查询动作对象：`{ label: '查询', onClick: loadRows }`，前提不是创建/生成/重算/计算利润快照。
4. 查看详情动作对象：`{ label: '查看详情', onClick: goDetail }`。

### 5.5 保持已通过门禁不回退

不得删除或降级：

1. TASK-005H 全局扫描范围。
2. TASK-005I 中文泛化写入口测试。
3. TASK-005I1 三条审计复现测试。
4. TASK-005J 只读说明成功 fixture。
5. TASK-005J1 多行按钮/菜单测试。
6. `style_profit:snapshot_create`、`snapshot_create`、`idempotency_key` 禁线。

## 6. 必跑验证命令

前端：

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

后端只读回归，不允许改后端代码：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

审计复现用例扫描：

```bash
rg -n "repeat\(400\)|repeat\(500\)|repeat\(1000\)|onClick|handler|command|onSelect|children|利润计算说明|利润率计算规则|利润快照来源说明" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

要求：长 action 配置反向测试必须存在。

业务禁线扫描：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算|款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

要求：`src` 业务文件不得命中写入口语义。

## 7. Git 提交要求

1. 禁止 `git add .`。
2. 禁止 `git add -A`。
3. 只允许显式白名单暂存。
4. 提交前必须执行：

```bash
git diff --cached --name-only
```

5. staged 文件不得包含：
   - `07_后端/**`
   - `.github/**`
   - `02_源码/**`
   - `.pytest-postgresql-*.xml`
   - `TASK-006*`
   - 历史未跟踪大目录

建议提交信息：

```bash
git commit -m "fix: detect long style profit action configs"
```

## 8. 验收标准

- [ ] label 与 onClick 间隔超过 300 字符时反向测试失败。
- [ ] onClick 在前、label 在后且间隔超过 300 字符时反向测试失败。
- [ ] label 与 handler 同对象时反向测试失败。
- [ ] label 与 command 同对象时反向测试失败。
- [ ] children 菜单节点中 label 与 onSelect 同节点时反向测试失败。
- [ ] 纯展示对象 `{ label: '利润计算说明', description: '只读帮助文案' }` 通过。
- [ ] `{ label: '返回', onClick: goBack }` 通过。
- [ ] `{ label: '查询', onClick: loadRows }` 通过。
- [ ] `{ label: '查看详情', onClick: goDetail }` 通过。
- [ ] TASK-005H/I/I1/J/J1 已通过测试未删除、未降级。
- [ ] 未恢复 substring 白名单豁免。
- [ ] 未继续只依赖固定窗口判断 action 对象。
- [ ] `npm run check:style-profit-contracts` 通过。
- [ ] `npm run test:style-profit-contracts` 通过。
- [ ] `npm run verify` 通过。
- [ ] `npm audit --audit-level=high` 为 0 vulnerabilities。
- [ ] 后端 style-profit API 定向回归和 py_compile 通过。
- [ ] commit 范围不包含后端、workflow、`02_源码`、JUnit 生成物或 TASK-006。

## 9. 交付证据要求

交付时新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J2_Action对象级交互上下文门禁整改证据.md`

必须记录：

1. 提交前 HEAD。
2. 提交后 HEAD。
3. commit message。
4. `git diff --cached --name-only` 提交前清单。
5. `git show --stat --oneline --name-only HEAD`。
6. action 对象级检测方案。
7. 新增长 action 配置反向测试清单。
8. 合法 action 成功 fixture 清单。
9. 未恢复 substring 白名单说明。
10. 未依赖固定窗口作为唯一判断说明。
11. `npm run check:style-profit-contracts` 结果。
12. `npm run test:style-profit-contracts` 结果。
13. `npm run verify` 结果。
14. `npm audit --audit-level=high` 结果。
15. 后端定向回归和 py_compile 结果。
16. 明确写出：未进入 TASK-006。
17. 明确写出：未开放创建/生成/重算利润快照入口。

## 10. 后续边界

1. `TASK-005J2` 审计通过后，才允许评估 `TASK-005K`。
2. 创建利润快照入口仍需单独任务单、单独审计。
3. `TASK-006` 仍需单独架构放行，不得由 TASK-005J2 自动启动。
