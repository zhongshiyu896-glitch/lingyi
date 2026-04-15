# TASK-005K 款式利润模块封版盘点工程任务单

- 任务编号：TASK-005K
- 模块：款式利润报表
- 优先级：P0
- 任务类型：封版盘点 / 证据汇总 / 交付门禁判定
- 更新时间：2026-04-15 14:42 CST
- 作者：技术架构师
- 前置审计：审计意见书第 156 份，TASK-005J37 已通过
- 前置基线：`f0fc6c92e46354eeb44add119267359ea919a74e`

## 一、任务目标

汇总 TASK-005 款式利润报表从口径冻结、模型迁移、来源采集、API 权限审计、前端只读联调到只读契约门禁的完整证据，判断 TASK-005 是否具备“本地封版候选”条件。

本任务只做封版盘点和证据文件，不实现新功能，不修改前端/后端业务代码，不解锁 TASK-006。

## 二、封版范围

### 2.1 本次必须盘点的 TASK-005 链路

1. TASK-005A：开发前基线盘点。
2. TASK-005B：利润口径冻结。
3. TASK-005C：模型、迁移与来源映射设计。
4. TASK-005D：利润快照计算服务。
5. TASK-005E：API 权限与审计基线。
6. TASK-005F：真实服务端来源 Adapter 与 PostgreSQL 财务门禁。
7. TASK-005G：前端只读联调。
8. TASK-005H/I/J：前端只读边界与契约门禁收口。
9. TASK-005J37：J36/J37 当前本地基线提交。

### 2.2 本次不包含的范围

1. 不开放 `POST /api/reports/style-profit/snapshots` 前端创建入口。
2. 不新增款式利润计算口径。
3. 不新增后端 API。
4. 不修改数据库迁移。
5. 不修改 `06_前端/**`、`07_后端/**`、`.github/**`、`02_源码/**`。
6. 不进入 TASK-006 加工厂对账单。

## 三、允许修改文件

只允许新建或修改以下文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md`

如发现必须修改其他文档，先停止并回报，不要自行扩大范围。

## 四、禁止事项

1. 禁止修改 `06_前端/**`。
2. 禁止修改 `07_后端/**`。
3. 禁止修改 `.github/**`。
4. 禁止修改 `02_源码/**`。
5. 禁止修改任何 `TASK-006*` 文件。
6. 禁止提交或暂存 `.pytest-postgresql-*.xml` 运行产物。
7. 禁止使用 `git add .` 或 `git add -A`。
8. 禁止把“本地封版候选”写成“生产封版完成”。
9. 禁止把 TASK-005K 通过解释为 TASK-006 放行。

## 五、必须核对的证据

| 证据项 | 检查要求 |
| --- | --- |
| 审计意见书第 156 份 | 确认 TASK-005J37 结论为通过，且 commit 为 `f0fc6c92e46354eeb44add119267359ea919a74e` |
| TASK-005 模块设计 | 确认当前版本、结论、关键门禁与 TASK-006 阻塞口径一致 |
| ADR-079 至 ADR-150 | 确认利润口径、来源映射、API 权限、前端只读门禁和本地基线决策均有记录 |
| TASK-005F PostgreSQL 证据 | 确认 settlement 与 style-profit 两份真实 PostgreSQL JUnit 指标均为 `tests=4, skipped=0, failures=0, errors=0`，或明确缺口 |
| TASK-005J37 提交范围 | 确认 commit 只包含 3 个白名单文件，未包含 `App.vue`、后端、workflow、TASK-006 或运行产物 |
| 当前工作区 | 确认未跟踪运行产物不会被误提交 |

## 六、必须执行的验证命令

### 6.1 前端只读契约验证

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

### 6.2 后端只读 API 回归

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

### 6.3 本地基线核对

```bash
cd /Users/hh/Desktop/领意服装管理系统
git show --stat --oneline --name-only f0fc6c92e46354eeb44add119267359ea919a74e
git diff -- 06_前端/lingyi-pc/src/App.vue
git status --short
```

### 6.4 PostgreSQL 证据核对

如果当前环境已有 PostgreSQL 一次性测试库和门禁变量，再执行真实非 skip 门禁；如果没有，不要伪造通过结论，只在证据文件中标记“本轮未重跑，沿用 TASK-005F8/F9 已审计证据”。

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
./scripts/run_postgresql_ci_gate.sh
```

## 七、输出文件要求

创建：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md`

证据文件必须包含以下章节：

1. 封版盘点结论。
2. 前置审计与 commit 基线。
3. TASK-005A 至 TASK-005J37 证据清单。
4. 前端验证结果。
5. 后端验证结果。
6. PostgreSQL 证据状态。
7. 当前工作区与运行产物风险。
8. 剩余风险清单。
9. 是否建议申请 TASK-005 本地封版。
10. 明确声明：TASK-006 继续阻塞，需单独任务单与审计放行。

## 八、封版判定标准

只有同时满足以下条件，才能写“建议 TASK-005 进入本地封版复审”：

1. 审计意见书第 156 份结论为通过。
2. `f0fc6c92e46354eeb44add119267359ea919a74e` 提交范围符合白名单。
3. 前端 `check/test/verify/audit` 全部通过。
4. 后端 style-profit API 定向回归与 `py_compile` 通过。
5. PostgreSQL 双 JUnit 证据已存在，或本轮无法重跑时明确引用已审计通过的 F8/F9 证据，不得伪造新证据。
6. `App.vue` 无残留 diff。
7. `.pytest-postgresql-*.xml` 未被暂存或提交。
8. TASK-006 未被修改、未被放行。

## 九、剩余风险必须写明

至少写明以下风险：

1. 当前项目按本地仓库基线工作，不依赖 GitHub 平台闭环。
2. 款式利润前端仍保持只读，不开放创建快照入口。
3. 真实生产 ERPNext 数据质量、权限源和 User Permission 仍需在部署环境复验。
4. PostgreSQL 门禁如本轮未重跑，必须说明沿用哪一份已审计证据。
5. TASK-006 加工厂对账单仍需单独架构任务单和审计放行。

## 十、交付回报格式

工程师完成后按以下格式回报：

```text
TASK-005K 封版盘点完成。

已输出：
- /03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md

结论：建议 / 不建议 TASK-005 进入本地封版复审

验证摘要：
- 前端：...
- 后端：...
- PostgreSQL：...
- Git 基线：...

剩余风险：
1. ...
2. ...

TASK-006 状态：继续阻塞，未放行。
```
