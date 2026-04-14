# TASK-005F8 PostgreSQL 外发 Schema 基线与双门禁复跑工程任务单

- 任务编号：TASK-005F8
- 模块：款式利润报表 / 外发加工管理 / PostgreSQL CI 门禁
- 版本：V1.0
- 更新时间：2026-04-14 16:20 CST
- 作者：技术架构师
- 优先级：P0
- 前置依赖：TASK-005F7 审计不通过，审计意见书第 110 份
- 执行角色：后端工程师
- 审计要求：完成后必须提交审计官复审；复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006

## 1. 任务目标

修复真实 PostgreSQL 财务门禁暴露的外发 schema 漂移问题：settlement PostgreSQL 集成测试在真实 PostgreSQL 下缺少 TASK-005F2 外发利润桥接字段，导致 `ly_subcontract_order.sales_order` 缺列并使 PostgreSQL hard gate 失败。

本任务必须做到：

1. settlement PostgreSQL 测试库 schema 包含 TASK-005F2 外发利润桥接字段。
2. settlement PostgreSQL 测试在真实 PostgreSQL 下不再因 `sales_order/work_order/profit_scope_status` 等列缺失失败。
3. 双门禁脚本重跑后生成两份 JUnit，且 settlement 与 style-profit 均为非 skip 通过。
4. TASK-005F2 外发利润桥接字段明确升级为外发模块基础 schema，所有外发 PostgreSQL 集成测试必须纳入。

## 2. 本任务边界

### 2.1 允许修改

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_005f2_subcontract_profit_scope_bridge.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据.md`

### 2.2 允许新建

- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线修复证据.md`

### 2.3 谨慎允许修改

仅当双门禁脚本无法在 settlement 失败后保留已生成 JUnit、或无法继续生成 style-profit JUnit 失败证据时，允许小范围修改：

- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh`

要求：不得弱化门禁；最终任一组失败时脚本仍必须整体失败。

### 2.4 禁止修改

- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/02_源码/**`
- 禁止修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/**`，除非审计确认模型字段本身与迁移不一致
- 禁止新增业务功能
- 禁止修改 `.github/**`
- 禁止新增或修改任何 `TASK-006*` 文件
- 禁止把失败、skip 或未执行伪装成通过
- 禁止使用生产库、准生产库或含真实业务数据的数据库

## 3. 架构决策

TASK-005F2 外发利润桥接字段已经升级为外发模块基础 schema。所有外发 PostgreSQL 集成测试，包括外发结算 settlement 测试，都必须使用包含这些字段的 schema 基线。

至少包含以下字段口径：

### 3.1 `ly_subcontract_order` 必需字段

- `sales_order`
- `sales_order_item`
- `production_plan_id`
- `work_order`
- `job_card`
- `profit_scope_status`
- `profit_scope_error_code`
- `profit_scope_resolved_at`

### 3.2 `ly_subcontract_inspection` 必需字段

- `sales_order`
- `sales_order_item`
- `production_plan_id`
- `work_order`
- `job_card`
- `profit_scope_status`
- `profit_scope_error_code`
- `profit_scope_resolved_at`

如果当前模型或迁移实际字段名与上述清单存在差异，必须以 TASK-005F2 迁移和当前模型为准，并在交付说明中列出差异原因。

## 4. 修复要求

### 4.1 优先方案：PostgreSQL 测试执行完整 Alembic Head

优先把 settlement PostgreSQL fixture 改为执行完整 Alembic head，确保测试 schema 与当前迁移链一致。

要求：

1. 不能依赖 `metadata.create_all()` 给已存在表补字段。
2. Alembic 执行失败必须让测试失败，不得吞错后继续 seed。
3. seed 数据前必须断言外发桥接字段存在。
4. schema assertion 失败必须输出缺失字段列表。

### 4.2 备选方案：显式纳入 TASK-005F2 迁移

如果当前测试环境暂不能执行完整 Alembic head，允许在 settlement PostgreSQL fixture 中显式纳入：

`task_005f2_subcontract_profit_scope_bridge.py`

要求：

1. 迁移必须在 seed 数据前执行。
2. 不得只在测试中临时 `ALTER TABLE ADD COLUMN sales_order`，必须纳入完整桥接字段集合。
3. 必须覆盖 `ly_subcontract_order` 与 `ly_subcontract_inspection` 两张表。
4. 必须补 schema assertion 防回退。

### 4.3 禁止方案

禁止以下做法：

1. 只把 seed 数据里的 `sales_order` 字段删掉来绕过缺列。
2. 只给 `ly_subcontract_order` 补 `sales_order` 一个字段。
3. 使用 `metadata.create_all()` 作为迁移替代。
4. 跳过 settlement PostgreSQL 测试。
5. 降低 JUnit expected tests 或 expected skipped 断言。
6. 改脚本让失败也返回成功。

## 5. 静态防回退测试要求

修改：

`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`

必须新增或扩展静态测试：

1. settlement PostgreSQL fixture 必须引用完整 Alembic head，或引用 `task_005f2_subcontract_profit_scope_bridge`。
2. settlement PostgreSQL fixture 必须包含 schema assertion。
3. schema assertion 必须覆盖 `ly_subcontract_order.sales_order`。
4. schema assertion 必须覆盖 `ly_subcontract_order.work_order`。
5. schema assertion 必须覆盖 `ly_subcontract_order.profit_scope_status`。
6. schema assertion 必须覆盖 `ly_subcontract_inspection.sales_order`。
7. schema assertion 必须覆盖 `ly_subcontract_inspection.work_order`。
8. schema assertion 必须覆盖 `ly_subcontract_inspection.profit_scope_status`。
9. 反向测试：移除 TASK-005F2 迁移引用或 schema assertion 时，静态测试必须失败。

## 6. 真实 PostgreSQL 复跑要求

修复后必须重新执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

POSTGRES_TEST_ALLOW_DESTRUCTIVE=true \
POSTGRES_TEST_DSN='postgresql+psycopg://USER:***@HOST:PORT/lingyi_test_pg_gate' \
bash scripts/run_postgresql_ci_gate.sh
```

必须产出：

| JUnit 文件 | 必须指标 |
| --- | --- |
| `.pytest-postgresql-subcontract-settlement.xml` | `tests=4, skipped=0, failures=0, errors=0` |
| `.pytest-postgresql-style-profit-subcontract.xml` | `tests=4, skipped=0, failures=0, errors=0` |

如果任一 JUnit 未生成、skip、failure 或 error，本任务不通过。

## 7. 证据文档要求

新建或更新：

`/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线修复证据.md`

必须包含：

1. 修复摘要。
2. 采用方案：完整 Alembic head / 显式纳入 TASK-005F2 迁移。
3. schema assertion 覆盖字段清单。
4. 真实 PostgreSQL 测试库名称。
5. 脱敏 DSN。
6. 执行命令。
7. settlement JUnit 指标。
8. style-profit JUnit 指标。
9. 敏感信息扫描结果。
10. 禁改扫描结果。
11. 结论。

## 8. 回归验证命令

必须执行：

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_postgresql.py tests/test_style_profit_subcontract_postgresql.py
POSTGRES_TEST_ALLOW_DESTRUCTIVE=true POSTGRES_TEST_DSN='postgresql+psycopg://USER:***@HOST:PORT/lingyi_test_pg_gate' bash scripts/run_postgresql_ci_gate.sh
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 9. 敏感信息扫描

证据文件写完后必须扫描：

```bash
rg -n "postgresql\+psycopg://[^*\n]*:[^*\n]*@|password|passwd|secret|token|Authorization|Cookie|BEGIN PRIVATE KEY|github_pat|ghp_" \
  /Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线修复证据.md
```

要求：不得出现真实密码、token、Cookie、Authorization、私钥或未脱敏 DSN。

## 10. 禁改扫描

交付前必须执行：

```bash
git status --short -- \
  06_前端 \
  02_源码 \
  .github \
  07_后端/lingyi_service/app \
  03_需求与设计/02_开发计划/TASK-006*
```

如果因模型字段不一致确需修改 `app/**`，必须先单独说明原因，并在交付中列出具体文件和理由。

## 11. 验收标准

□ settlement PostgreSQL fixture 已纳入完整 Alembic head，或显式纳入 TASK-005F2 外发利润桥接迁移。  
□ seed 数据前存在 schema assertion。  
□ schema assertion 覆盖 `ly_subcontract_order.sales_order/work_order/profit_scope_status`。  
□ schema assertion 覆盖 `ly_subcontract_inspection.sales_order/work_order/profit_scope_status`。  
□ 禁止使用 `metadata.create_all()` 作为迁移替代给已存在表补字段。  
□ 真实 PostgreSQL 下 settlement JUnit 为 `tests=4, skipped=0, failures=0, errors=0`。  
□ 真实 PostgreSQL 下 style-profit JUnit 为 `tests=4, skipped=0, failures=0, errors=0`。  
□ 证据文档记录修复摘要、脱敏 DSN、命令、两份 JUnit 指标和敏感信息扫描。  
□ 定向 pytest、全量 pytest、unittest、py_compile 通过。  
□ 禁改扫描通过。  
□ 未进入前端、`.github`、`02_源码`、TASK-006。  
□ 审计官复审通过前不得进入 TASK-005G、前端创建入口或 TASK-006。  

## 12. 交付说明要求

工程师交付时必须说明：

1. 根因确认：缺失哪些字段。
2. 修复方案：完整 Alembic head / 显式迁移链。
3. schema assertion 覆盖字段。
4. 两份 JUnit 指标。
5. 真实 PostgreSQL 测试库名称。
6. 脱敏 DSN。
7. 回归测试结果。
8. 敏感信息扫描结果。
9. 禁改扫描结果。
10. 是否修改了脚本；如修改，说明为什么没有弱化门禁。
11. 明确未进入 TASK-005G、前端创建入口或 TASK-006。
