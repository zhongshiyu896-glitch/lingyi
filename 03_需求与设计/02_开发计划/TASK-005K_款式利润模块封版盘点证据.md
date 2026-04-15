# TASK-005K 款式利润模块封版盘点证据

## 1. 封版盘点结论
- 盘点结论：满足 TASK-005 本地封版复审前置条件。
- 建议：建议 `TASK-005` 进入“本地封版复审”。
- 结论边界：本结论仅针对 `TASK-005`（款式利润模块）本地基线与证据链，不等同于生产封版完成。

## 2. 前置审计与 commit 基线
- 前置审计口径：`审计意见书第 156 份，TASK-005J37 已通过`。
- 基线 commit：`f0fc6c92e46354eeb44add119267359ea919a74e`。
- 本地 HEAD：`f0fc6c92e46354eeb44add119267359ea919a74e`（与基线一致）。

### 2.1 基线 commit 提交范围核对
执行：
- `git show --stat --oneline --name-only f0fc6c92e46354eeb44add119267359ea919a74e`

结果仅包含 3 个白名单文件：
1. `03_需求与设计/02_开发计划/TASK-005J36_同步数组迭代方法Bind与CallCall门禁整改证据.md`
2. `06_前端/lingyi-pc/scripts/check-style-profit-contracts.mjs`
3. `06_前端/lingyi-pc/scripts/test-style-profit-contracts.mjs`

判定：符合 J37 白名单提交要求。

## 3. TASK-005A 至 TASK-005J37 证据清单

### 3.1 任务单链路存在性（A~J37）
在 `03_需求与设计/02_开发计划/` 目录可检索到以下主链任务单：
- A 组：`TASK-005A*`
- B 组：`TASK-005B*`
- C 组：`TASK-005C*`
- D 组：`TASK-005D*`
- E 组：`TASK-005E*`
- F 组：`TASK-005F*`
- G：`TASK-005G_款式利润前端只读联调_工程任务单.md`
- H：`TASK-005H_款式利润全局只读边界门禁收口_工程任务单.md`
- I：`TASK-005I_款式利润中文泛化写入口门禁_工程任务单.md`、`TASK-005I1_中文语义白名单绕过整改_工程任务单.md`
- J37：`TASK-005J37_J36最小范围本地基线提交_工程任务单.md`

### 3.2 设计与决策链核对
- 模块设计文件：`03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`
  - 已记录：第 156 份审计通过、基线 commit、进入 TASK-005K、TASK-006 继续阻塞口径。
- 技术决策文件：`03_需求与设计/01_架构设计/03_技术决策记录.md`
  - ADR 覆盖检查结果：`ADR-079` 至 `ADR-150` 无缺失（脚本检查 `missing_79_150 = []`）。
  - 含 `ADR-150`（J36 白名单本地基线提交）与 `ADR-151`（K 只做封版盘点，不解锁 TASK-006）记录。

## 4. 前端验证结果
执行目录：`/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc`

执行命令与结果：
1. `npm run check:style-profit-contracts`：通过（`Scanned files: 24`）
2. `npm run test:style-profit-contracts`：通过（`All style-profit contract fixture tests passed. scenarios=475`）
3. `npm run verify`：通过（production contracts + style-profit contracts + typecheck + build 全通过）
4. `npm audit --audit-level=high`：`found 0 vulnerabilities`

附加核对：
- `git diff -- 06_前端/lingyi-pc/src/App.vue` 输出为空（无 `App.vue` 探针改动残留）。
- `rg -n "probe|PROBE|临时探针|scratch|debug" 06_前端/lingyi-pc/src/App.vue` 无命中。

## 5. 后端验证结果
执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

执行命令与结果：
1. `.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py`
   - 结果：`34 passed, 1 warning in 0.87s`
2. `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)`
   - 结果：通过（无错误输出）

## 6. PostgreSQL 证据状态

### 6.1 历史已审计证据
已存在并可核对：
- `03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线修复证据.md`
- `03_需求与设计/02_开发计划/TASK-005F9_本地基线提交证据.md`

两份证据均记录双 JUnit 指标：
- `.pytest-postgresql-subcontract-settlement.xml`：`tests=4, skipped=0, failures=0, errors=0`
- `.pytest-postgresql-style-profit-subcontract.xml`：`tests=4, skipped=0, failures=0, errors=0`

### 6.2 本轮环境复跑状态
执行：`./scripts/run_postgresql_ci_gate.sh`
- 结果：`POSTGRES_TEST_DSN is required for PostgreSQL CI gate`
- 判定：本轮环境缺少 PostgreSQL CI gate 必需 DSN，未进行新一轮真实 gate 复跑。
- 处理：沿用 F8/F9 已审计通过证据，不伪造“本轮复跑通过”结论。

### 6.3 本地 XML 文件状态
当前后端目录可见：
- `.pytest-postgresql-style-profit-subcontract.xml`
- `.pytest-postgresql-subcontract-settlement.xml`

文件内指标均为：`tests=4, skipped=0, failures=0, errors=0`（时间戳 2026-04-14 16:18 +08:00）。

## 7. 当前工作区与运行产物风险
- `git status --short` 显示存在大量历史未跟踪文件与若干文档变更（非本任务范围）。
- 本轮未执行 `git add .` / `git add -A`。
- 本轮 `git diff --cached --name-only` 为空（无新增暂存）。
- 运行产物风险项：
  - `07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml`
  - `07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml`
  均未被暂存/提交。

## 8. 剩余风险清单
1. 项目当前依赖本地仓库基线与本地证据链，未走 GitHub 平台 required checks 闭环。
2. 款式利润前端仍为只读策略，未开放创建快照入口（策略正确但意味着写入口业务能力仍冻结）。
3. 真实生产环境 ERPNext 数据质量、权限源（含 User Permission）仍需部署后复验。
4. 本轮 PostgreSQL gate 未复跑（缺少 `POSTGRES_TEST_DSN`），当前结论沿用 F8/F9 已审计证据与现存 XML。
5. 工作区存在大量历史未跟踪文件，后续若进行提交操作需继续严格白名单暂存。

## 9. 是否建议申请 TASK-005 本地封版
- 建议：**建议申请 TASK-005 进入本地封版复审**。

判断依据（与任务单封版判定标准对齐）：
1. 第 156 份审计通过口径已在模块设计/ADR 中明确。
2. 基线 commit `f0fc6c92e46354eeb44add119267359ea919a74e` 范围符合白名单。
3. 前端 `check/test/verify/audit` 全通过，`scenarios=475`，audit 0 高危。
4. 后端 style-profit 定向回归通过（34 passed），`py_compile` 通过。
5. PostgreSQL 双 JUnit 证据存在且为 `4/0/0/0`，本轮无法复跑时已明确沿用已审计证据。
6. `App.vue` 无 diff、无探针关键词命中。
7. 未发现 TASK-006 文件被修改或放行动作。

## 10. 明确声明（阻塞边界）
- `TASK-006` 状态：**继续阻塞，未放行**。
- 本文件不构成 TASK-006 放行依据；TASK-006 仍需单独任务单与审计放行。
