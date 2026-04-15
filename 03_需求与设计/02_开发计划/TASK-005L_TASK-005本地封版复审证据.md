# TASK-005L TASK-005 本地封版复审证据

- 任务编号：TASK-005L
- 模块：款式利润报表
- 复审类型：本地封版复审 / release candidate review
- 执行时间：2026-04-15 15:35 CST
- 前置基线：`1da795333d20ed8ecfb2308da623358668272458`
- 当前 HEAD：`1da795333d20ed8ecfb2308da623358668272458`
- 复审结论：建议 `TASK-005` 标记为“本地封版完成”
- TASK-006 状态：继续阻塞，未放行

## 一、结论

TASK-005 款式利润报表已满足本地封版条件。

本结论仅表示本地仓库、本地证据链、本地验证命令满足 TASK-005 本地封版复审要求，不表示生产发布完成，不表示 GitHub hosted runner / required-check 平台闭环完成，也不构成 TASK-006 自动放行依据。

## 二、Git 基线核验

### 2.1 当前 HEAD

执行命令：

```bash
git rev-parse HEAD
```

结果：

```text
1da795333d20ed8ecfb2308da623358668272458
```

结论：当前 HEAD 与 TASK-005K1 前置基线一致。

### 2.2 HEAD 提交范围

执行命令：

```bash
git show --stat --oneline --name-only HEAD
```

关键结果：

```text
1da7953 docs: add task 005K closeout evidence
03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md
```

结论：K 证据 commit 仅包含 1 个白名单文件。

### 2.3 工作区状态

执行命令：

```bash
git status --short
git diff -- 06_前端/lingyi-pc/src/App.vue
git diff --cached --name-only
```

结果摘要：

- `App.vue` diff：无输出。
- staged files：无输出。
- 当前存在历史未跟踪/未暂存文件与本轮证据文件。
- 未跟踪运行产物仍包括：
  - `07_后端/lingyi_service/.pytest-postgresql-subcontract-settlement.xml`
  - `07_后端/lingyi_service/.pytest-postgresql-style-profit-subcontract.xml`

结论：本轮未暂存或提交运行产物；后续如需提交证据仍需白名单暂存。

## 三、TASK-005A 至 TASK-005K1 状态表

| 阶段 | 范围 | 状态 | 备注 |
| --- | --- | --- | --- |
| TASK-005A-A2 | 款式利润开发前基线盘点与时间口径修正 | 完成 | 文档证据已入库 |
| TASK-005B-B1 | 利润口径冻结与 Sprint 旧口径修正 | 完成 | 双收入口径、SLE 实际材料成本、快照不可变已冻结 |
| TASK-005C-C4 | 利润模型、迁移、来源映射骨架与本地基线 | 完成 | 4 表模型、索引、source_map 契约已落地 |
| TASK-005D-D6 | 利润快照计算服务与幂等、事务、归属 fail-closed | 完成 | 服务层基线已提交 |
| TASK-005E-E4 | API 权限、审计、统一错误信封 | 完成 | 只读与创建 API 后端已具备权限审计基线 |
| TASK-005F-F11 | 真实来源 Adapter、外发桥接、PostgreSQL 财务门禁 | 完成 | F8/F9 双 JUnit 非 skip 证据已形成 |
| TASK-005G | 前端只读列表/详情联调 | 完成 | 未开放创建快照入口 |
| TASK-005H-I-J37 | 前端只读边界与契约门禁持续收口 | 完成 | style-profit contract scenarios=475 |
| TASK-005K | 封版盘点 | 完成 | 审计意见书第 157 份通过 |
| TASK-005K1 | K 证据本地基线提交 | 完成 | 审计意见书第 158 份通过，HEAD=`1da795333d20ed8ecfb2308da623358668272458` |

## 四、前端只读门禁验证

执行目录：

```bash
/Users/hh/Desktop/领意服装管理系统/06_前端/lingyi-pc
```

执行命令与结果：

| 命令 | 结果 |
| --- | --- |
| `npm run check:style-profit-contracts` | 通过，`Style-profit contract check passed.`，`Scanned files: 24` |
| `npm run test:style-profit-contracts` | 通过，`All style-profit contract fixture tests passed. scenarios=475` |
| `npm run verify` | 通过，含 production/style-profit 契约、typecheck、build |
| `npm audit --audit-level=high` | 通过，`found 0 vulnerabilities` |

补充说明：Vite build 存在既有 chunk size warning，不影响本次 TASK-005L 封版复审结论。

## 五、后端 style-profit 回归验证

执行目录：

```bash
/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
```

执行命令：

```bash
.venv/bin/python -m pytest -q tests/test_style_profit_api.py tests/test_style_profit_api_permissions.py tests/test_style_profit_api_audit.py tests/test_style_profit_api_errors.py
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

结果：

```text
34 passed, 1 warning in 1.37s
py_compile 通过
```

警告为既有 `pytest_asyncio` / Python 版本相关 DeprecationWarning，不影响 TASK-005L 本地封版复审结论。

## 六、PostgreSQL 门禁证据状态

本轮环境检查结果：

```text
POSTGRES_TEST_DSN=missing
```

因此本轮未复跑 `scripts/run_postgresql_ci_gate.sh`，未伪造新 PostgreSQL 结果。

沿用已审计通过的 TASK-005F8/F9 双 JUnit 证据，当前本地现存 JUnit 指标为：

```text
.pytest-postgresql-subcontract-settlement.xml: tests=4 skipped=0 failures=0 errors=0 timestamp=2026-04-14T16:18:26.411471+08:00
.pytest-postgresql-style-profit-subcontract.xml: tests=4 skipped=0 failures=0 errors=0 timestamp=2026-04-14T16:18:30.330354+08:00
```

结论：PostgreSQL 非 skip 证据链已存在并已被 F8/F9 审计引用；本轮未新增 PostgreSQL 实跑证据。

## 七、禁改范围核验

执行命令：

```bash
git diff --name-only -- '06_前端' '07_后端' '.github' '02_源码' '03_需求与设计/**/TASK-006*'
git diff -- 06_前端/lingyi-pc/src/App.vue
git diff --cached --name-only
```

结果摘要：

- tracked forbidden diffs：无输出。
- `App.vue` diff：无输出。
- staged files：无输出。
- `TASK-006*` 未发现本轮修改或实现入口。
- `.pytest-postgresql-*.xml` 未被暂存或提交。

结论：本轮复审未修改禁改范围。

## 八、剩余风险

1. 当前封版结论为本地封版，不等同于生产发布完成。
2. 当前仓库仍未配置 remote，未 push，不等同于 GitHub hosted runner / required-check 平台闭环。
3. 本轮缺少 `POSTGRES_TEST_DSN`，未重跑 PostgreSQL gate；沿用 F8/F9 已审计证据与现存双 JUnit 文件。
4. 款式利润前端继续保持只读，不开放创建/生成/重算快照入口；后续若开放写入口，需要重新任务单与审计。
5. 工作区仍存在历史未跟踪/未暂存文件与运行产物，后续提交必须继续白名单暂存。
6. 生产环境 ERPNext 数据质量、权限源可用性、真实权限矩阵仍需部署后复验。

## 九、最终建议

建议将 TASK-005 标记为“本地封版完成”。

该建议仅限 TASK-005 本地封版，不代表生产发布，不代表平台 required-check 闭环，不放行 TASK-006。

TASK-006 状态：继续阻塞，未放行。
