# TASK-005L TASK-005 本地封版复审工程任务单

- 任务编号：TASK-005L
- 模块：款式利润报表
- 优先级：P0
- 任务类型：本地封版复审 / 最终证据核验 / release candidate review
- 更新时间：2026-04-15 15:09 CST
- 作者：技术架构师
- 前置审计：审计意见书第 158 份，TASK-005K1 通过
- 前置基线：`1da795333d20ed8ecfb2308da623358668272458`
- 前置结论：TASK-005K 证据已被 git 跟踪，可作为 TASK-005 本地封版复审稳定证据点

## 一、任务目标

对 TASK-005 款式利润报表做本地封版复审，确认当前本地仓库是否满足“TASK-005 本地封版完成”的条件。

本任务只做最终证据核验和封版复审证据输出，不新增功能，不修改前端/后端业务代码，不修改数据库迁移，不进入 TASK-006。

## 二、复审范围

必须覆盖以下链路：

1. 利润口径冻结：TASK-005B / ADR-079。
2. 利润模型与来源映射：TASK-005C-C4。
3. 利润快照计算服务：TASK-005D-D6。
4. API 权限与审计基线：TASK-005E-E4。
5. 真实来源 Adapter 与 PostgreSQL 财务门禁：TASK-005F-F11。
6. 前端只读联调：TASK-005G。
7. 前端只读边界与契约门禁：TASK-005H-I-J37。
8. 封版盘点与证据入库：TASK-005K-K1。

## 三、允许修改文件

只允许新建或修改以下文件：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005L_TASK-005本地封版复审证据.md`

如复审发现必须修改其他文件，先停止并回报，不得自行扩大范围。

## 四、禁止事项

1. 禁止修改 `06_前端/**`。
2. 禁止修改 `07_后端/**`。
3. 禁止修改 `.github/**`。
4. 禁止修改 `02_源码/**`。
5. 禁止修改数据库迁移文件。
6. 禁止修改任何 `TASK-006*` 文件。
7. 禁止提交或暂存 `.pytest-postgresql-*.xml`。
8. 禁止修改审计记录或审计官会话日志。
9. 禁止开放款式利润快照创建入口。
10. 禁止把“本地封版完成”写成“生产发布完成”。
11. 禁止把 TASK-005L 通过解释为 TASK-006 自动放行。

## 五、必须核对的基线

| 项目 | 要求 |
| --- | --- |
| K1 前置审计 | 审计意见书第 158 份结论为通过 |
| 当前 HEAD | 必须记录当前 HEAD；若不是 `1da795333d20ed8ecfb2308da623358668272458`，必须说明原因 |
| K 证据 commit | commit `1da795333d20ed8ecfb2308da623358668272458` 只包含 K 证据文件 |
| TASK-006 | 未修改、未放行、未进入实现 |
| 创建入口 | 前端不得出现款式利润创建快照入口 |
| 运行产物 | `.pytest-postgresql-*.xml` 不得被暂存或提交 |

## 六、必须执行的验证命令

### 6.1 Git 基线核验

```bash
cd /Users/hh/Desktop/领意服装管理系统
git rev-parse HEAD
git show --stat --oneline --name-only HEAD
git status --short
git diff -- 06_前端/lingyi-pc/src/App.vue
```

### 6.2 前端只读门禁

```bash
cd /Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
npm run check:style-profit-contracts
npm run test:style-profit-contracts
npm run verify
npm audit --audit-level=high
```

### 6.3 后端回归

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

### 6.4 PostgreSQL 证据

如果当前环境具备一次性 PostgreSQL 测试库和安全门禁变量，则重跑：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
./scripts/run_postgresql_ci_gate.sh
```

如果当前环境不具备 PostgreSQL 条件，不得伪造新结果；在证据中明确写：本轮未重跑 PostgreSQL，沿用已审计通过的 TASK-005F8/F9 双 JUnit 证据，指标为 `tests=4, skipped=0, failures=0, errors=0`。

## 七、输出证据文件要求

创建：

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005L_TASK-005本地封版复审证据.md`

证据文件必须包含：

1. 本地封版复审结论。
2. 当前 HEAD 与 K1 commit 核验。
3. TASK-005A 至 TASK-005K1 完成状态表。
4. 前端只读门禁验证结果。
5. 后端 style-profit 回归验证结果。
6. PostgreSQL 门禁证据状态。
7. 禁改范围核验。
8. 剩余风险。
9. 是否建议 TASK-005 标记为“本地封版完成”。
10. 明确声明：本地封版不等同生产发布，不等同平台 required-check 闭环，TASK-006 继续阻塞。

## 八、封版通过标准

只有同时满足以下条件，才能写“建议 TASK-005 标记为本地封版完成”：

1. 审计意见书第 158 份为通过。
2. K 证据已纳入本地基线 commit。
3. 前端只读门禁全部通过。
4. 后端 style-profit 回归全部通过。
5. PostgreSQL 双 JUnit 证据存在且未被伪造；若本轮未重跑，必须清楚引用历史已审计证据。
6. 未发现创建快照入口回潮。
7. 未发现 TASK-006 文件变更或实现入口。
8. 未提交运行产物。
9. 剩余风险均已列明。

## 九、交付回报格式

```text
TASK-005L 本地封版复审完成。

已输出：
- /03_需求与设计/02_开发计划/TASK-005L_TASK-005本地封版复审证据.md

结论：建议 / 不建议 TASK-005 标记为本地封版完成

验证摘要：
- HEAD：...
- 前端：...
- 后端：...
- PostgreSQL：...
- 禁改范围：...

剩余风险：
1. ...
2. ...

TASK-006 状态：继续阻塞，未放行。
```
