# TASK-005J1 多行交互上下文门禁整改工程任务单

- 模块：款式利润报表 / 前端只读门禁稳定化整改
- 任务编号：TASK-005J1
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 18:14 CST
- 作者：技术架构师
- 前置审计：审计意见书第 119 份，`TASK-005J` 有条件通过但存在高危绕过
- 当前有效 HEAD：`ba3ef7351f3d252400e0f39cc70c1b6afd396d29`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V3.8；`ADR-114`

## 1. 任务目标

修复只读说明文案交互上下文识别只看“文案所在行”的高危绕过。当前多行按钮、菜单或 action 配置会绕过门禁，例如：

```vue
<el-button>
  利润计算说明
</el-button>
```

该片段仍是交互入口，必须被判定失败。

本任务只修复前端契约门禁和反向测试，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 119 份指出：

1. 只读说明文案的交互上下文识别目前只看“文案所在行”。
2. 多行按钮可绕过门禁。
3. 多行菜单可绕过门禁。
4. 多行 action 配置可绕过门禁。
5. 该问题属于高危，因为可以把写入口伪装成跨行说明文案放进交互组件。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 只读页面小范围修正

仅当现有只读页面被新门禁误杀时，允许小范围修正只读文案：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J1_多行交互上下文门禁整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J1_多行交互上下文门禁整改证据.md`（交付时新建）
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
9. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 交互上下文检测必须跨行

不得继续只用“文案所在行”判断交互上下文。必须采用以下任一方案：

1. 前后窗口检测：以文案命中位置为中心，向前/向后至少扫描 300 个字符，识别未闭合交互标签或 action 配置。
2. 标签块检测：解析或正则识别 `<el-button ...>...</el-button>`、`<button ...>...</button>`、`<el-menu-item ...>...</el-menu-item>`、`<menu-item ...>...</menu-item>` 块，块内出现只读说明文案但具备交互入口语义时失败。
3. 简易状态机：按字符遍历未闭合交互标签，在标签关闭前命中的说明文案都判为交互上下文。

推荐方案：前后窗口 + 未闭合标签块检测，避免引入重型解析器。

### 5.2 必须识别的交互上下文

1. `<el-button>...</el-button>`。
2. `<button>...</button>`。
3. `<el-menu-item>...</el-menu-item>`。
4. `<menu-item>...</menu-item>`。
5. 带 `@click` 的任意标签块。
6. 带 `onClick` 的配置对象。
7. 路由 `path/name`。
8. 函数名、方法名、变量名。

### 5.3 必须新增反向测试

`test-style-profit-contracts.mjs` 必须新增以下用例，且均失败：

1. 多行按钮：

```vue
<el-button>
  利润计算说明
</el-button>
```

2. 多行原生按钮：

```vue
<button>
  利润率计算规则
</button>
```

3. 多行菜单：

```vue
<el-menu-item @click="openHelp">
  利润快照来源说明
</el-menu-item>
```

4. 多行 action 配置：

```ts
const actions = [
  {
    label: '利润计算说明',
    onClick: openHelp,
  },
]
```

5. 多行路由配置：

```ts
{
  path: '/reports/style-profit/calculate',
  name: 'ProfitCalculationHelp',
}
```

### 5.4 合法说明文案仍需通过

以下纯说明文案在非交互上下文中必须继续通过：

1. `<p>利润计算说明</p>`。
2. `<p>利润率计算规则</p>`。
3. `<section>利润快照来源说明</section>`。
4. `<el-alert title="实际成本计算口径说明" />`，前提是不带点击或提交动作。

### 5.5 保持已通过门禁不回退

不得删除或降级：

1. TASK-005H 全局扫描范围。
2. TASK-005I 中文泛化写入口测试。
3. TASK-005I1 三条审计复现测试。
4. TASK-005J 只读说明成功 fixture。
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

审计复现用例扫描：

```bash
rg -n "<el-button>|<button>|<el-menu-item|onClick|利润计算说明|利润率计算规则|利润快照来源说明" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

要求：多行交互上下文反向测试必须存在。

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
git commit -m "fix: detect multiline style profit interactive wording"
```

## 8. 验收标准

- [ ] 多行 `<el-button>` 中的 `利润计算说明` 反向测试失败。
- [ ] 多行 `<button>` 中的 `利润率计算规则` 反向测试失败。
- [ ] 多行 `<el-menu-item @click>` 中的 `利润快照来源说明` 反向测试失败。
- [ ] 多行 action 配置中的 `利润计算说明 + onClick` 反向测试失败。
- [ ] 多行 `/reports/style-profit/calculate` 路由反向测试失败。
- [ ] 非交互说明文案 `<p>利润计算说明</p>` 仍通过。
- [ ] 非交互说明文案 `<section>利润快照来源说明</section>` 仍通过。
- [ ] TASK-005H/I/I1/J 已通过测试未删除、未降级。
- [ ] 未恢复 substring 白名单豁免。
- [ ] `npm run check:style-profit-contracts` 通过。
- [ ] `npm run test:style-profit-contracts` 通过。
- [ ] `npm run verify` 通过。
- [ ] `npm audit --audit-level=high` 为 0 vulnerabilities。
- [ ] 后端 style-profit API 定向回归和 py_compile 通过。
- [ ] commit 范围不包含后端、workflow、`02_源码`、JUnit 生成物或 TASK-006。

## 9. 交付证据要求

交付时新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005J1_多行交互上下文门禁整改证据.md`

必须记录：

1. 提交前 HEAD。
2. 提交后 HEAD。
3. commit message。
4. `git diff --cached --name-only` 提交前清单。
5. `git show --stat --oneline --name-only HEAD`。
6. 多行交互上下文识别方案。
7. 新增多行反向测试清单。
8. 非交互说明文案继续通过证据。
9. 未恢复 substring 白名单说明。
10. `npm run check:style-profit-contracts` 结果。
11. `npm run test:style-profit-contracts` 结果。
12. `npm run verify` 结果。
13. `npm audit --audit-level=high` 结果。
14. 后端定向回归和 py_compile 结果。
15. 明确写出：未进入 TASK-006。
16. 明确写出：未开放创建/生成/重算利润快照入口。

## 10. 后续边界

1. `TASK-005J1` 审计通过后，才允许评估 `TASK-005K`。
2. 创建利润快照入口仍需单独任务单、单独审计。
3. `TASK-006` 仍需单独架构放行，不得由 TASK-005J1 自动启动。
