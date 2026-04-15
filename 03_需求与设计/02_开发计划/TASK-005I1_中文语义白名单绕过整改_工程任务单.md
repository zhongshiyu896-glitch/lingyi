# TASK-005I1 中文语义白名单绕过整改工程任务单

- 模块：款式利润报表 / 前端只读边界三次收口整改
- 任务编号：TASK-005I1
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-14 17:52 CST
- 作者：技术架构师
- 前置审计：审计意见书第 117 份，`TASK-005I` 有条件通过但存在高危绕过
- 当前有效 HEAD：`f0cc7e045a3293cb69b01c30900710e8396bae82`
- 架构依据：`/03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md` V3.6；`ADR-112`

## 1. 任务目标

修复 `check-style-profit-contracts.mjs` 中 `shouldIgnoreSemanticMatch()` 的白名单绕过问题。当前逻辑按 substring 豁免整段语义匹配，导致 `<button>款式利润报表计算</button>`、`利润快照列表生成`、`利润金额重新计算` 这类“白名单只读词 + 写动作词”组合能绕过门禁。

本任务只修复前端契约门禁和反向测试，不开放利润快照创建入口，不进入 TASK-006。

## 2. 审计问题来源

审计意见书第 117 份指出：

1. `shouldIgnoreSemanticMatch()` 只要匹配片段附近包含只读白名单词，就直接忽略整个语义命中。
2. 这会把“款式利润报表计算”错误识别为只读。
3. 这会把“利润快照列表生成”错误识别为只读。
4. 这会把“利润金额重新计算”错误识别为只读。
5. 该绕过属于高危，因为会让写入口以普通中文按钮文案形式进入前端。

## 3. 允许修改文件

### 3.1 前端门禁文件

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

### 3.2 只读页面小范围修正

仅当现有页面被新门禁误杀时，允许小范围修正只读文案：

- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotList.vue`
- `/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/src/views/style_profit/StyleProfitSnapshotDetail.vue`

### 3.3 文档证据

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005I1_中文语义白名单绕过整改_工程任务单.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005I1_中文语义白名单绕过整改证据.md`（交付时新建）
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
8. 禁止使用 `git add .` 或 `git add -A`。

## 5. 必做整改

### 5.1 修复白名单逻辑

不得继续使用“片段包含只读白名单词就忽略”的逻辑。

必须改为以下任一安全方案：

1. 精确白名单：只对白名单短语本身豁免，不豁免白名单短语与写动作词拼接后的更长片段。
2. 负向优先：只要匹配窗口内存在写动作词，必须先判定为违规；只读白名单只能用于“没有写动作词”的纯展示文案。
3. AST/Token 级判断：把领域词和写动作词拆开识别，写动作词存在时不允许被只读词覆盖。

推荐采用方案 2：负向优先。

### 5.2 必须失败的新增反向测试

`test-style-profit-contracts.mjs` 必须新增以下三条审计复现用例，且均失败：

1. `<button>款式利润报表计算</button>`
2. `<button>利润快照列表生成</button>`
3. `<button>利润金额重新计算</button>`

### 5.3 继续保留 TASK-005I 测试

不得删除或降级 TASK-005I 已要求的反向测试：

1. `<el-button>款式利润计算</el-button>` 必须失败。
2. `<el-button>利润报表重算</el-button>` 必须失败。
3. `<el-button>毛利核算</el-button>` 必须失败。
4. `<el-button>利润一键生成</el-button>` 必须失败。
5. `function openProfitCalculateDialog()` 必须失败。
6. `/reports/style-profit/calculate` 必须失败。
7. `generateProfitSnapshot` 必须失败。
8. 合法只读文案 fixture 必须通过。

### 5.4 合法只读文案仍需通过

合法 fixture 必须继续覆盖并通过：

1. `款式利润报表`
2. `利润快照列表`
3. `利润快照详情`
4. `查看详情`
5. `查询`
6. `利润明细`
7. `来源追溯`
8. `利润金额`
9. `利润率`

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

审计复现扫描：

```bash
rg -n "款式利润报表计算|利润快照列表生成|利润金额重新计算" \
  /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs
```

要求：三条用例必须存在于反向测试中。

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
git commit -m "fix: tighten style profit semantic gate whitelist"
```

## 8. 验收标准

- [ ] `shouldIgnoreSemanticMatch()` 不再按 substring 豁免整段语义匹配。
- [ ] `款式利润报表计算` 反向测试失败。
- [ ] `利润快照列表生成` 反向测试失败。
- [ ] `利润金额重新计算` 反向测试失败。
- [ ] TASK-005I 原有中文泛化反向测试仍保留且通过。
- [ ] 合法只读文案 fixture 仍通过。
- [ ] `npm run check:style-profit-contracts` 通过。
- [ ] `npm run test:style-profit-contracts` 通过。
- [ ] `npm run verify` 通过。
- [ ] `npm audit --audit-level=high` 为 0 vulnerabilities。
- [ ] 后端 style-profit API 定向回归和 py_compile 通过。
- [ ] commit 范围不包含后端、workflow、`02_源码`、JUnit 生成物或 TASK-006。

## 9. 交付证据要求

交付时新建：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005I1_中文语义白名单绕过整改证据.md`

必须记录：

1. 提交前 HEAD。
2. 提交后 HEAD。
3. commit message。
4. `git diff --cached --name-only` 提交前清单。
5. `git show --stat --oneline --name-only HEAD`。
6. 白名单逻辑修复说明。
7. 三条审计复现用例结果。
8. TASK-005I 原反向测试保留说明。
9. 合法只读文案通过证据。
10. `npm run check:style-profit-contracts` 结果。
11. `npm run test:style-profit-contracts` 结果。
12. `npm run verify` 结果。
13. `npm audit --audit-level=high` 结果。
14. 后端定向回归和 py_compile 结果。
15. 明确写出：未进入 TASK-006。
16. 明确写出：未开放创建/生成/重算利润快照入口。

## 10. 后续边界

1. `TASK-005I1` 审计通过后，才允许评估 `TASK-005J`。
2. 创建利润快照入口仍需单独任务单、单独审计，不得由 TASK-005I1 自动开放。
3. `TASK-006` 仍需单独架构放行，不得由 TASK-005I1 自动启动。
