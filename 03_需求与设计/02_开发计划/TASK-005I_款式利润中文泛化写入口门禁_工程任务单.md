# TASK-005I 款式利润中文泛化写入口门禁工程任务单

- 模块：款式利润报表 / 前端只读边界三次收口
- 任务编号：TASK-005I
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-14 17:39 CST
- 作者：技术架构师
- 前置审计：审计意见书第 116 份，`TASK-005H` 通过
- 当前有效 HEAD：`3d778cb55b63755bf69e263afe6e2d7b62d85b3d`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V3.5；`ADR-111`

## 1. 任务目标

在 TASK-005H 已把 style-profit 只读边界扩展到全局前端入口的基础上，继续补齐中文泛化写入口门禁。重点防止工程师不用固定词“生成利润快照”，而改用“款式利润计算”“利润报表重算”“利润一键生成”“毛利核算”等中文泛化文案、路由或函数名绕过只读边界。

本任务仍然只做前端契约门禁增强，不开放利润快照创建入口，不进入 TASK-006。

## 2. 前置条件

1. `TASK-005H` 审计通过，审计意见书第 116 份。
2. 当前 HEAD 为 `3d778cb55b63755bf69e263afe6e2d7b62d85b3d`。
3. 当前款式利润前端只允许列表与详情只读。
4. `TASK-006` 未放行，不得进入加工厂对账单开发。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package.json`（仅当 verify 脚本需要调整时允许）
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/package-lock.json`（仅当 package.json 触发锁文件变化时允许）

### 3.2 只读页面小范围修正

仅当现有页面误触新门禁时，允许小范围修正只读文案，不允许增加新功能：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005I_款式利润中文泛化写入口门禁_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005I_款式利润中文泛化写入口门禁证据.md`（交付时新建）
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
7. 禁止新增、展示或映射 `style_profit:snapshot_create`。
8. 禁止新增 `snapshot_create`、`idempotency_key`、`createStyleProfitSnapshot`。
9. 禁止新增任何创建、生成、重算、计算利润快照的 UI 入口。
10. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 中文语义门禁矩阵

在 `check-style-profit-contracts.mjs` 中新增中文语义门禁。不得简单禁止所有“款式利润/利润快照/利润报表”字样，因为只读页面正常需要展示这些名称；必须拦截“领域词 + 写动作词”的组合。

领域词建议至少包含：

1. `款式利润`
2. `利润快照`
3. `利润报表`
4. `毛利`
5. `净利`
6. `利润核算`

写动作词建议至少包含：

1. `新建`
2. `创建`
3. `生成`
4. `重算`
5. `重新计算`
6. `计算`
7. `核算`
8. `提交`
9. `保存`
10. `一键生成`

必须拦截以下语义组合：

1. 写动作词在领域词前后 0-16 个字符内出现。
2. 写动作词出现在 `el-button`、`button`、菜单项、路由 name/path、函数名、方法名、变量名附近。
3. 英文绕过词：`createProfit`、`generateProfit`、`recalculateProfit`、`createSnapshot`、`generateSnapshot`、`recalculateSnapshot`、`profitCreate`、`profitGenerate`、`profitRecalculate`。
4. 路由绕过：`/reports/style-profit/create`、`/reports/style-profit/new`、`/reports/style-profit/generate`、`/reports/style-profit/recalculate`、`/reports/style-profit/calculate`。

### 5.2 允许的只读词

以下词在只读页面可保留，不得被误杀：

1. `款式利润报表`
2. `利润快照列表`
3. `利润快照详情`
4. `查看详情`
5. `查询`
6. `筛选`
7. `搜索`
8. `返回`
9. `审计信息`
10. `利润明细`
11. `来源追溯`
12. `利润率`
13. `利润金额`

如实现中需要白名单，必须是精准白名单，禁止用“整文件跳过”规避。

### 5.3 扫描范围

继续覆盖 TASK-005H 范围：

1. `src/api/**`
2. `src/views/**`
3. `src/router/**`
4. `src/stores/**`
5. `src/App.vue`
6. `src/main.ts`
7. 如存在 `src/components/**`，自动纳入扫描

### 5.4 反向测试

`test-style-profit-contracts.mjs` 必须新增或补齐以下反向测试：

1. `<el-button>款式利润计算</el-button>` 必须失败。
2. `<el-button>利润报表重算</el-button>` 必须失败。
3. `<el-button>毛利核算</el-button>` 必须失败。
4. `<el-button>利润一键生成</el-button>` 必须失败。
5. `function openProfitCalculateDialog()` 必须失败。
6. 路由 `/reports/style-profit/calculate` 必须失败。
7. 英文 `generateProfitSnapshot` 必须失败。
8. 合法只读文案 `款式利润报表 / 利润快照列表 / 查看详情 / 查询 / 利润明细 / 来源追溯` 必须通过。
9. `src/api/request.ts` 统一 fetch 白名单继续通过。
10. 原 TASK-005H 反向测试不得删除或降级。

### 5.5 防误杀要求

1. 不得因页面标题 `款式利润报表` 导致合法 fixture 失败。
2. 不得因列表列名 `利润金额 / 利润率` 导致合法 fixture 失败。
3. 不得因详情区块 `利润明细 / 来源追溯` 导致合法 fixture 失败。
4. 如果新增白名单，必须在证据中列出白名单规则和原因。

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

静态禁线扫描：

```bash
rg -n "款式利润.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}款式利润)|利润报表.{0,16}(新建|创建|生成|重算|重新计算|计算|核算|提交|保存)|((新建|创建|生成|重算|重新计算|计算|核算|提交|保存).{0,16}利润报表)|毛利核算|净利核算|利润一键生成|createProfit|generateProfit|recalculateProfit|createSnapshot|generateSnapshot|recalculateSnapshot|profitCreate|profitGenerate|profitRecalculate" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src
```

要求：`src` 业务文件不得命中写入口语义。合法只读文案不应命中。

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
git commit -m "test: add style profit semantic write-entry gate"
```

## 8. 验收标准

- [ ] 中文语义门禁已覆盖领域词 + 写动作词组合。
- [ ] “款式利润计算”反向测试失败。
- [ ] “利润报表重算”反向测试失败。
- [ ] “毛利核算”反向测试失败。
- [ ] “利润一键生成”反向测试失败。
- [ ] `openProfitCalculateDialog` 反向测试失败。
- [ ] `/reports/style-profit/calculate` 反向测试失败。
- [ ] `generateProfitSnapshot` 反向测试失败。
- [ ] 合法只读文案 fixture 通过。
- [ ] TASK-005H 原反向测试仍保留且通过。
- [ ] `npm run check:style-profit-contracts` 通过。
- [ ] `npm run test:style-profit-contracts` 通过。
- [ ] `npm run verify` 通过。
- [ ] `npm audit --audit-level=high` 为 0 vulnerabilities。
- [ ] 后端 style-profit API 定向回归与 py_compile 通过。
- [ ] commit 范围不包含后端、workflow、`02_源码`、JUnit 生成物或 TASK-006。

## 9. 交付证据要求

交付时新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005I_款式利润中文泛化写入口门禁证据.md`

必须记录：

1. 提交前 HEAD。
2. 提交后 HEAD。
3. commit message。
4. `git diff --cached --name-only` 提交前清单。
5. `git show --stat --oneline --name-only HEAD`。
6. 新增中文语义规则清单。
7. 新增反向测试清单。
8. 合法只读文案通过证据。
9. `npm run check:style-profit-contracts` 结果。
10. `npm run test:style-profit-contracts` 结果。
11. `npm run verify` 结果。
12. `npm audit --audit-level=high` 结果。
13. 后端定向回归与 py_compile 结果。
14. 明确写出：未进入 TASK-006。
15. 明确写出：未开放创建/生成/重算利润快照入口。

## 10. 后续边界

1. `TASK-005I` 审计通过后，才允许评估 `TASK-005J` 是否进行只读页面体验优化、导航接入或文档封版。
2. 创建利润快照入口仍需单独任务单、单独审计，不得由 TASK-005I 自动开放。
3. `TASK-006` 仍需单独架构放行，不得由 TASK-005I 自动启动。
