# TASK-005F8 PostgreSQL 外发 Schema 基线修复证据

- 任务编号：TASK-005F8
- 执行时间：2026-04-14 16:19:45 CST
- 执行人：Codex 工程执行
- 执行目录：`/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service`
- PostgreSQL 来源：Docker 一次性测试库（`postgres:16-alpine`）
- 数据库名：`lingyi_test_pg_gate`
- 脱敏 DSN：`postgresql+psycopg://postgres:***@127.0.0.1:55432/lingyi_test_pg_gate`

## 1. 修复摘要

1. settlement PostgreSQL fixture 已纳入 `TASK-005F2` 迁移链：
   - `migrations/versions/task_005f2_subcontract_profit_scope_bridge.py`
2. settlement fixture 在 seed 前增加了 schema assertion：
   - 覆盖 `ly_subcontract_order.sales_order/work_order/profit_scope_status`
   - 覆盖 `ly_subcontract_inspection.sales_order/work_order/profit_scope_status`
   - 同时覆盖 `profit_scope_resolved_at`
3. `TASK-005F2` 迁移补齐 `ly_subcontract_inspection.profit_scope_resolved_at`（幂等 add-column）。
4. `tests/test_ci_postgresql_gate.py` 增加静态防回退测试：
   - 迁移引用不可移除
   - schema assertion 不可移除
   - 关键字段覆盖不可回退

## 2. 关键执行命令

```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

.venv/bin/python -m pytest -q tests/test_ci_postgresql_gate.py
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_postgresql.py tests/test_style_profit_subcontract_postgresql.py

POSTGRES_TEST_ALLOW_DESTRUCTIVE=true \
POSTGRES_TEST_DSN='postgresql+psycopg://postgres:***@127.0.0.1:55432/lingyi_test_pg_gate' \
  bash scripts/run_postgresql_ci_gate.sh

.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

## 3. 双门禁 JUnit 指标（真实 PostgreSQL 非 Skip）

1. `.pytest-postgresql-subcontract-settlement.xml`
   - tests=4
   - skipped=0
   - failures=0
   - errors=0

2. `.pytest-postgresql-style-profit-subcontract.xml`
   - tests=4
   - skipped=0
   - failures=0
   - errors=0

## 4. 回归结果

1. `tests/test_ci_postgresql_gate.py`：12 passed
2. `tests/test_subcontract_settlement_postgresql.py tests/test_style_profit_subcontract_postgresql.py`：5 passed, 8 skipped（无 DSN 路径）
3. `scripts/run_postgresql_ci_gate.sh`（真实 DSN）
   - settlement gate：4 passed，JUnit 断言通过
   - style-profit gate：4 passed，JUnit 断言通过
4. `pytest -q`：641 passed, 13 skipped
5. `unittest discover`：Ran 624 tests, OK (skipped=1)
6. `py_compile`：通过

## 5. 敏感信息与安全门禁

1. 已设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
2. 测试库名符合 `lingyi_test_*` 规则。
3. 本文与命令均使用脱敏 DSN，不含 token/cookie/Authorization/私钥明文。
4. 失败不伪装通过；JUnit 使用双文件分组断言。

## 6. 禁改扫描说明

执行命令：

```bash
git status --short -- \
  06_前端 \
  02_源码 \
  .github \
  07_后端/lingyi_service/app \
  03_需求与设计/02_开发计划/TASK-006*
```

结果说明：

1. 工作区存在历史遗留脏变更（本任务前已存在）。
2. 本次 TASK-005F8 实际改动仅涉及：
   - `07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py`
   - `07_后端/lingyi_service/tests/test_ci_postgresql_gate.py`
   - `07_后端/lingyi_service/migrations/versions/task_005f2_subcontract_profit_scope_bridge.py`
   - `07_后端/lingyi_service/tests/test_subcontract_profit_scope_bridge.py`
   - `03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线修复证据.md`
3. 未新增前端改动、未新增 `TASK-006*` 改动。

## 7. 结论

- 结论：通过
- 真实 PostgreSQL 双门禁已恢复并非 skip 通过：
  - settlement：tests=4, skipped=0, failures=0, errors=0
  - style-profit：tests=4, skipped=0, failures=0, errors=0
- 审计官复审前，仍不进入 TASK-005G、前端创建入口或 TASK-006。
