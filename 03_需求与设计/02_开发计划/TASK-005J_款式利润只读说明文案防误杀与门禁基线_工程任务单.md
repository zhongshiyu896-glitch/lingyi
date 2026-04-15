# TASK-005J 款式利润只读说明文案防误杀与门禁基线工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化
- 任务编号：TASK-005J
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 18:02 CST
- 作者：技术架构师
- 前置审计：审计意见书第 118 份，`TASK-005I1` 通过
- 当前有效 HEAD：`9146f0cea171aff488aa907f373bbc0864648bbc`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V3.7；`ADR-113`

## 1. 任务目标

在 TASK-005I1 已修复中文语义白名单绕过后，补齐“合法只读说明文案”的成功 fixture 与防误杀门禁，避免后续出现“利润计算说明”“利润率计算规则”等纯说明文字时被误杀，进而诱导工程师恢复 substring 白名单。

本任务只做前端门禁稳定化和本地基线提交，不开放利润快照创建入口，不进入 TASK-006。

## 2. 背景

审计意见书第 118 份确认 `TASK-005I1` 通过，同时提示剩余风险：语义门禁收紧后可能误杀部分纯说明文案，例如“利润计算说明”“利润率计算规则”。如果后续确实需要这类只读文案，应通过明确成功 fixture 保护，而不是恢复 substring 豁免。

因此 TASK-005J 的核心不是新增业务页面，而是把“可允许的只读说明文案”写成测试契约，防止未来门禁被误改。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 只读页面小范围文案

仅当需要在现有只读页面加入说明文案用于真实页面验证时，允许小范围增加只读说明，不允许新增按钮、菜单或交互动作：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J_款式利润只读说明文案防误杀与门禁基线_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J_款式利润只读说明文案防误杀与门禁基线证据.md`（交付时新建）
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
7. 禁止新增创建、生成、重算、计算利润快照的按钮、菜单、路由或函数。
8. 禁止恢复 substring 白名单豁免。
9. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 新增合法只读说明成功 fixture

`test-style-profit-contracts.mjs` 必须新增成功用例，覆盖以下纯说明文案可以通过：

1. `利润计算说明`
2. `利润率计算规则`
3. `实际成本计算口径说明`
4. `标准成本计算口径说明`
5. `款式利润报表查看说明`
6. `利润快照来源说明`
7. `利润金额展示规则`
8. `未解析来源处理说明`

这些文案必须只出现在说明文本、提示文本、帮助区、折叠说明区或只读段落中，不得出现在按钮、菜单、路由、函数名或可触发操作的变量名中。

### 5.2 新增位置敏感反向测试

同样的说明词一旦出现在交互入口中，必须失败：

1. `<el-button>利润计算说明</el-button>` 必须失败。
2. `<button>利润率计算规则</button>` 必须失败。
3. 菜单项 `利润快照来源说明` 带点击处理时必须失败。
4. `function openProfitCalculationHelpDialog()` 如果只是帮助说明，可允许；但 `function openProfitCalculateDialog()` 必须继续失败。
5. 路由 `/reports/style-profit/profit-calculation-help` 可作为帮助页候选允许；但 `/reports/style-profit/calculate` 必须继续失败。

如果实现复杂，至少必须覆盖前 3 条反向测试和第 4/5 条既有反向测试不回退。

### 5.3 白名单策略要求

允许说明文案通过时，不得恢复以下危险逻辑：

1. 不得用 `segment.includes(readonlyPhrase)` 直接豁免整个 segment。
2. 不得对整个文件白名单。
3. 不得对整个 `src/views/style_profit/**` 目录跳过语义扫描。
4. 不得把“计算/核算/生成/重算”等写动作词全局白名单。

推荐策略：

1. 对说明文案做“上下文白名单”，只允许在非交互文本上下文中通过。
2. 交互上下文包括 `button`、`el-button`、`@click` 附近、路由 path/name、函数名、方法名、变量名。
3. 在交互上下文中出现领域词 + 写动作词，一律失败。

### 5.4 保持已通过门禁

不得删除或降级以下已通过保护：

1. TASK-005H 全局扫描范围。
2. TASK-005I 中文泛化写入口测试。
3. TASK-005I1 三条审计复现测试。
4. `src/api/request.ts` 统一 fetch 白名单。
5. `style_profit:snapshot_create`、`snapshot_create`、`idempotency_key` 禁线。

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

成功 fixture 检查：

```bash
rg -n "利润计算说明|利润率计算规则|实际成本计算口径说明|标准成本计算口径说明|款式利润报表查看说明|利润快照来源说明|利润金额展示规则|未解析来源处理说明" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

要求：以上文案必须存在于成功 fixture 或明确的通过测试中。

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
git commit -m "test: protect style profit read-only wording fixtures"
```

## 8. 验收标准

- [ ] 合法只读说明文案成功 fixture 已覆盖 8 条文案。
- [ ] 说明文案出现在按钮/菜单交互入口时反向测试失败。
- [ ] `openProfitCalculateDialog` 仍失败。
- [ ] `/reports/style-profit/calculate` 仍失败。
- [ ] TASK-005H / TASK-005I / TASK-005I1 已通过反向测试未删除、未降级。
- [ ] 未恢复 substring 白名单豁免。
- [ ] 未全文件或全目录跳过语义扫描。
- [ ] `npm run check:style-profit-contracts` 通过。
- [ ] `npm run test:style-profit-contracts` 通过。
- [ ] `npm run verify` 通过。
- [ ] `npm audit --audit-level=high` 为 0 vulnerabilities。
- [ ] 后端 style-profit API 定向回归和 py_compile 通过。
- [ ] commit 范围不包含后端、workflow、`02_源码`、JUnit 生成物或 TASK-006。

## 9. 交付证据要求

交付时新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J_款式利润只读说明文案防误杀与门禁基线证据.md`

必须记录：

1. 提交前 HEAD。
2. 提交后 HEAD。
3. commit message。
4. `git diff --cached --name-only` 提交前清单。
5. `git show --stat --oneline --name-only HEAD`。
6. 成功 fixture 文案清单。
7. 交互入口反向测试清单。
8. 未恢复 substring 白名单说明。
9. `npm run check:style-profit-contracts` 结果。
10. `npm run test:style-profit-contracts` 结果。
11. `npm run verify` 结果。
12. `npm audit --audit-level=high` 结果。
13. 后端定向回归和 py_compile 结果。
14. 明确写出：未进入 TASK-006。
15. 明确写出：未开放创建/生成/重算利润快照入口。

## 10. 后续边界

1. `TASK-005J` 审计通过后，才允许评估 `TASK-005K` 款式利润只读前端封版或导航接入。
2. 创建利润快照入口仍需单独任务单、单独审计。
3. `TASK-006` 仍需单独架构放行，不得由 TASK-005J 自动启动。
