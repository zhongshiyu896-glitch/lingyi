# TASK-005F4 PostgreSQL 非 Skip 证据

- 任务编号：TASK-005F4
- 生成时间：2026-04-14 15:24 CST
- 执行环境：本地仓库 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`

## 1. 外发来源查询下推实现位置

- 文件：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_style_profit_adapter.py`
- 方法：`ERPNextStyleProfitAdapter.load_subcontract_rows`

已落实：
1. 正常成本候选查询在数据库层按 `company + item_code + inspected_at` 做期间过滤。
2. `selector.sales_order` 非空时，查询优先在数据库层限制 `sales_order`（允许 `NULL` 进入后续 unresolved 解释）。
3. `selector.work_order` 非空时，查询优先在数据库层限制 `work_order`（允许 `NULL` 进入后续 unresolved 解释）。
4. 正常候选查询显式排除 `inspected_at IS NULL`。
5. 缺 `inspected_at` 改为单独诊断查询，不计入利润。
6. 仍保留 Python 层最终安全校验与 `source_map` 原因解释，不承担主要期间过滤。

## 2. inspected_at 正常查询 vs 缺失诊断查询

正常查询：
- `inspected_at IS NOT NULL`
- `inspected_at >= from_date 起始边界`
- `inspected_at <= to_date 结束边界`

缺失诊断查询：
- `inspected_at IS NULL`
- 只用于产生 unresolved 诊断来源（`SUBCONTRACT_INSPECTED_AT_REQUIRED`）
- 不进入 `actual_subcontract_cost`

## 3. 诊断限制与超限处理

- 环境变量：`STYLE_PROFIT_SUBCONTRACT_DIAGNOSTIC_LIMIT`
- 默认值：`200`
- 超限处理：
1. 仅拉取前 N 条缺 `inspected_at` 记录。
2. 追加 1 条聚合诊断项（`bridge_source=diagnostic_aggregate`）。
3. 聚合项输出：
   - `diagnostic_total_missing_inspected_at`
   - `diagnostic_truncated_count`

## 4. PostgreSQL marker 测试数量与结果

新增文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_style_profit_subcontract_postgresql.py`

新增 `@pytest.mark.postgresql` 用例：4 条
1. `test_postgresql_subcontract_profit_filters_by_inspected_at`
2. `test_postgresql_subcontract_profit_filters_work_order_in_database`
3. `test_postgresql_subcontract_profit_uses_indexed_period_query`
4. `test_postgresql_subcontract_profit_missing_inspected_at_is_limited_diagnostic`

本地执行结果：
- `pytest -q tests/test_style_profit_subcontract_postgresql.py` -> `4 skipped`
- `pytest -q -m postgresql tests/test_style_profit_subcontract_postgresql.py` -> `4 skipped`

结论：本地环境未提供 `POSTGRES_TEST_DSN` / destructive gate，故为**安全 skip**，非 skip 证据状态为 **pending**。

## 5. JUnit 非 Skip 硬门禁结果（TASK-005F5 口径修正）

- 脚本：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/scripts/run_postgresql_ci_gate.sh`
- 当前脚本同时覆盖两组门禁目标：
1. `tests/test_subcontract_settlement_postgresql.py`
2. `tests/test_style_profit_subcontract_postgresql.py`
- 分别输出两份 JUnit：
1. `.pytest-postgresql-subcontract-settlement.xml`
2. `.pytest-postgresql-style-profit-subcontract.xml`
- 分组断言均为：`--expected-tests 4 --expected-skipped 0`

当前状态（本地无 DSN，不伪装通过）：
- settlement JUnit：pending（等待可用 PostgreSQL 测试库）
- style-profit JUnit：pending（等待可用 PostgreSQL 测试库）

待回填（有真实 DSN 后）：
- settlement JUnit：tests=4, skipped=0, failures=0, errors=0
- style-profit JUnit：tests=4, skipped=0, failures=0, errors=0

## 6. 验证命令结果

1. `pytest -q tests/test_ci_postgresql_gate.py` -> 通过（8 passed）
2. `pytest -q tests/test_style_profit_subcontract_postgresql.py tests/test_subcontract_settlement_postgresql.py` -> 通过（5 passed, 8 skipped）
3. `pytest -q -m postgresql tests/test_style_profit_subcontract_postgresql.py tests/test_subcontract_settlement_postgresql.py` -> 安全 skip（8 skipped, 5 deselected）
4. `bash scripts/run_postgresql_ci_gate.sh`（无 DSN） -> 失败并 fast-fail：`POSTGRES_TEST_DSN is required for PostgreSQL CI gate`
5. `pytest -q` -> 通过（637 passed, 13 skipped）
6. `python -m unittest discover` -> 通过（624 tests, skipped=1）
7. `python -m py_compile ...` -> 通过

## 7. 范围确认

- 未进入前端修改。
- 未进入 `.github`。
- 未进入 `02_源码`。
- 未修改 migrations。
- 未进入 TASK-006。

## 8. TASK-005F6 Workflow 双 JUnit 上传回填

- workflow 文件：`/Users/hh/Desktop/领意服装管理系统/.github/workflows/backend-postgresql.yml`
- 已修复为双 artifact 上传：
1. `postgresql-settlement-junit` -> `.pytest-postgresql-subcontract-settlement.xml`
2. `postgresql-style-profit-junit` -> `.pytest-postgresql-style-profit-subcontract.xml`
- 旧单文件 `.pytest-postgresql.xml` 已废弃，不再作为门禁证据路径。
- 当前无真实 PostgreSQL DSN，双 JUnit 非 skip 指标仍为 pending，未伪装通过。
