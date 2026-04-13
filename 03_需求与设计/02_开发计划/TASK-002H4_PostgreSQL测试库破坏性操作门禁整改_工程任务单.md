# TASK-002H4 PostgreSQL 测试库破坏性操作门禁整改工程任务单

- 任务编号：TASK-002H4
- 模块：外发加工管理
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-13 16:06 CST
- 作者：技术架构师
- 审计来源：TASK-002H3 审计意见书第 54 份不通过，P1 为 PostgreSQL 集成测试拿到 `POSTGRES_TEST_DSN` 后会直接执行 `DROP SCHEMA IF EXISTS ly_schema CASCADE`，缺少一次性测试库和允许破坏性操作的双重安全门禁
- 架构裁决：PostgreSQL destructive 测试必须同时满足 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 和数据库名测试库白名单；否则不得执行 drop schema
- 前置依赖：TASK-002H3 本轮不通过；继续遵守外发模块 V1.22 与 ADR-050
- 任务边界：只修 PostgreSQL 测试库破坏性操作安全门禁、skip/fail 文案和测试；不得修改结算业务逻辑、不得创建对账单主表、不得调用 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H4
模块：PostgreSQL 测试库破坏性操作门禁整改
优先级：P1（测试安全阻断整改）
════════════════════════════════════════════════════════════════════════════

【任务目标】
为 PostgreSQL 结算并发集成测试增加破坏性操作双重安全门禁，防止误把 `POSTGRES_TEST_DSN` 指向开发、预发或共享库时执行 `DROP SCHEMA ly_schema CASCADE`。

【模块概述】
TASK-002H3 增加了真实 PostgreSQL 并发测试，但 fixture 在检测到 `POSTGRES_TEST_DSN` 后会直接删除 `ly_schema`。这在专用一次性测试库中是可接受的，但如果环境变量误配到共享库，会造成不可逆数据破坏。本任务只修测试安全门禁，确保没有明确授权和测试库命名白名单时，测试不会执行任何 destructive SQL。

【涉及文件】
必须修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_export.py（如需补静态扫描或共享工具）

允许修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（仅限抽取 PostgreSQL destructive gate fixture）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md 或测试说明（如已有，仅限记录运行方式）

【安全门禁规则】
执行任何以下 SQL 前必须先通过双重门禁：
- `DROP SCHEMA IF EXISTS ly_schema CASCADE`
- `DROP DATABASE`
- `TRUNCATE ... CASCADE`
- 任意可删除整个 schema 或批量清空业务数据的 SQL

双重门禁：
1. 环境变量 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
2. 连接后的 `current_database()` 或 DSN 数据库名必须匹配以下白名单之一：
   - 以 `_test` 结尾，例如 `lingyi_test`
   - 以 `test_` 开头，例如 `test_lingyi`
   - 以 `lingyi_test_` 开头，例如 `lingyi_test_20260413`
   - 以 `tmp_lingyi_` 开头，例如 `tmp_lingyi_ci_001`
3. 以上两项必须同时满足。
4. 仅 DSN 存在不得执行 destructive SQL。
5. 仅 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 但数据库名不匹配白名单，不得执行 destructive SQL。
6. 白名单检查必须基于数据库真实返回值优先，例如 `select current_database()`；DSN 解析只能作为辅助。
7. 不满足门禁时，测试必须 `pytest.skip()` 或明确 fail，且不得执行 drop。
8. skip/fail 文案必须说明缺少哪个条件，但不得打印账号、密码、host、完整 DSN。
9. 允许打印脱敏数据库名和 schema 名，不得打印密码。

【推荐实现】
新增辅助函数：
1. `_destructive_postgres_tests_enabled() -> bool`
2. `_assert_safe_destructive_postgres_target(engine) -> str`
3. `_database_name_is_allowed_for_destructive_tests(db_name: str) -> bool`
4. `_redact_dsn_for_message(dsn: str) -> str`（可选）

示例逻辑：
```python
allow = os.getenv("POSTGRES_TEST_ALLOW_DESTRUCTIVE", "").lower() == "true"
if not allow:
    pytest.skip("POSTGRES_TEST_ALLOW_DESTRUCTIVE=true is required before destructive PostgreSQL tests")

with engine.connect() as conn:
    db_name = conn.execute(text("select current_database()")).scalar_one()

if not is_allowed_test_database_name(db_name):
    pytest.skip("PostgreSQL destructive tests require a database name ending with _test or starting with test_/lingyi_test_/tmp_lingyi_")
```

【必须补测试】
1. `test_postgresql_destructive_gate_requires_allow_env`
   - 设置 DSN 但不设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
   - 断言不会调用 drop schema。
   - 断言测试 skip/fail 文案清楚。

2. `test_postgresql_destructive_gate_rejects_non_test_database_name`
   - 模拟 `current_database()` 返回 `lingyi_prod`、`lingyi_dev`、`erpnext`。
   - 即使 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`，也不得 drop schema。

3. `test_postgresql_destructive_gate_accepts_test_database_name`
   - 模拟 `current_database()` 返回 `lingyi_test`、`test_lingyi`、`lingyi_test_20260413` 或 `tmp_lingyi_ci`。
   - 且 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 时允许进入 destructive 分支。

4. `test_postgresql_destructive_gate_message_redacts_dsn`
   - 错误或 skip 文案不得包含密码、完整 DSN、账号凭据。

5. `test_postgresql_drop_schema_only_after_gate_passes`
   - monkeypatch 或 spy 确认 gate 未通过时不执行 `DROP SCHEMA`。
   - gate 通过时才允许执行。

【验收标准】
□ `DROP SCHEMA IF EXISTS ly_schema CASCADE` 前必须调用安全门禁。  
□ 未设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true` 时，即使有 `POSTGRES_TEST_DSN` 也不得执行 drop schema。  
□ 数据库名不匹配测试库白名单时，即使 allow=true 也不得执行 drop schema。  
□ 数据库名匹配测试库白名单且 allow=true 时，才允许执行 destructive SQL。  
□ skip/fail 文案不泄露完整 DSN、账号、密码。  
□ PostgreSQL marker 测试无 DSN 时仍明确 skip。  
□ 有 DSN 但无 destructive allow 时明确 skip/fail，且不执行 drop。  
□ 已补门禁单元测试或静态测试。  
□ 结算定向测试通过。  
□ 全量 pytest/unittest/py_compile 通过。  
□ 不修改结算业务逻辑。  

【建议命令】
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_postgresql.py
POSTGRES_TEST_DSN='postgresql+psycopg://...' .venv/bin/python -m pytest -q -m postgresql tests/test_subcontract_settlement_postgresql.py
POSTGRES_TEST_ALLOW_DESTRUCTIVE=true POSTGRES_TEST_DSN='postgresql+psycopg://.../lingyi_test' .venv/bin/python -m pytest -q -m postgresql tests/test_subcontract_settlement_postgresql.py
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_export.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【禁止事项】
- 禁止仅凭 `POSTGRES_TEST_DSN` 执行 `DROP SCHEMA`。
- 禁止连接生产、预发、共享业务库执行 destructive 测试。
- 禁止在 skip/fail 文案中输出完整 DSN、账号、密码。
- 禁止用 mock 替代后续真实 PostgreSQL 并发验证。
- 禁止修改结算 lock/release 业务逻辑，除非真实非 skip 测试暴露缺陷。
- 禁止创建加工厂对账单主表。
- 禁止调用 ERPNext 写接口。

【前置依赖】
TASK-002H3 审计意见书第 54 份不通过；必须完成本任务并通过审计后，才允许重新提供 `POSTGRES_TEST_DSN` 实跑 TASK-002H3。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
