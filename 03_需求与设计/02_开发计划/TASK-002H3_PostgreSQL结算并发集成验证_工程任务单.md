# TASK-002H3 PostgreSQL 结算并发集成验证工程任务单

- 任务编号：TASK-002H3
- 模块：外发加工管理
- 优先级：P2
- 版本：V1.0
- 更新时间：2026-04-13 15:57 CST
- 作者：技术架构师
- 审计来源：TASK-002H2 审计意见书第 53 份通过，剩余风险为当前未提供 `POSTGRES_TEST_DSN`，结算同 key 并发 lock/release 尚未在真实 PostgreSQL 行锁与唯一约束等待语义下非 skip 跑通
- 架构裁决：进入 TASK-006 前补一次 PostgreSQL 并发集成验证；本任务原则上只跑测试和补测试门禁，不改业务逻辑
- 前置依赖：TASK-002H2 已通过；继续遵守外发模块 V1.21 与 ADR-049
- 任务边界：只做 PostgreSQL 并发集成测试、迁移升级验证和测试结果记录；不得新增加工厂对账单主表、应付、付款、GL 或 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H3
模块：PostgreSQL 结算并发集成验证
优先级：P2（进入 TASK-006 前门禁）
════════════════════════════════════════════════════════════════════════════

【任务目标】
在真实 PostgreSQL 测试库上验证结算 lock/release 的同 key 并发幂等、行锁和唯一约束等待语义，确认 TASK-002H2 的 mock/SQLite 覆盖可以落到生产数据库行为。

【模块概述】
TASK-002H2 已在常规测试中修复同 key 并发唯一冲突 replay 问题，但 SQLite 不能证明 PostgreSQL 的 `FOR UPDATE` 行锁、唯一约束等待、事务提交后 replay 行为。加工厂对账单进入 TASK-006 前，必须用真实 PostgreSQL 测试库跑一次非 skip 集成验证，避免在财务前置结算锁定上留下数据库语义盲区。

【涉及文件】
必须新增或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_export.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/pytest.ini
- /Users/hh/Desktop/领意服装管理系统/03_需求与设计/05_审计记录.md（仅由审计官记录结果，工程师不手写审计报告）

允许修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（仅限 PostgreSQL DSN fixture）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/utils.py（如已有，仅限测试工具）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py（仅当 PostgreSQL 非 skip 测试暴露真实缺陷时，才允许最小修复）

【环境要求】
1. 必须提供 `POSTGRES_TEST_DSN`。
2. `POSTGRES_TEST_DSN` 必须指向专用测试库，禁止连接生产库、准生产库或共享业务库。
3. 测试运行前必须确认测试库可被清理或使用独立 schema。
4. 测试不得连接 ERPNext 真实业务服务。
5. 测试不得调用 ERPNext 写接口。
6. 如果当前无法提供 `POSTGRES_TEST_DSN`，不得声称 TASK-002H3 完成，只能说明阻塞原因。

【必须验证的 PostgreSQL 场景】
1. 同一批 inspection、同一个 lock `idempotency_key`，两个线程/事务并发调用 lock：
   - 两个请求最终都返回成功。
   - 只有一个请求 `idempotent_replay=false`。
   - 另一个请求 `idempotent_replay=true`。
   - `ly_subcontract_settlement_operation` 只有一条 lock operation。
   - inspection 最终为 `statement_locked`，statement_id/statement_no 正确。

2. 同一批 inspection、同一个 release `idempotency_key`，两个线程/事务并发调用 release：
   - 两个请求最终都返回成功。
   - 只有一个请求 `idempotent_replay=false`。
   - 另一个请求 `idempotent_replay=true`。
   - `ly_subcontract_settlement_operation` 只有一条 release operation。
   - inspection 最终为 `unsettled`，statement_id/statement_no 清空。

3. 同一个 `operation_type + idempotency_key`、不同 inspection_ids 或不同 statement：
   - 返回 `SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT`。
   - 不新增第二条 operation。
   - 不错误修改 inspection。

4. PostgreSQL 迁移验证：
   - Alembic upgrade head 能创建 `ly_subcontract_settlement_operation`。
   - 唯一约束 `operation_type + idempotency_key` 存在。
   - inspection 的结算字段存在，`idempotency_key` 相关字段长度符合 128 字符契约。

【测试要求】
必须新增或补齐以下测试：
1. `test_postgresql_settlement_same_key_concurrent_lock_replays`
2. `test_postgresql_settlement_same_key_concurrent_release_replays`
3. `test_postgresql_settlement_same_key_different_payload_conflicts`
4. `test_postgresql_settlement_operation_unique_constraint_exists`

要求：
1. 以上测试必须标记 `@pytest.mark.postgresql`。
2. 无 `POSTGRES_TEST_DSN` 时允许明确 skip，但 TASK-002H3 不能算完成。
3. 有 `POSTGRES_TEST_DSN` 时必须非 skip 执行。
4. 测试必须使用两个独立数据库连接或两个独立 Session。
5. 测试必须真实触发 PostgreSQL 事务并发，不得只 monkeypatch 唯一冲突。
6. 测试完成后必须清理测试数据。

【建议命令】
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service
POSTGRES_TEST_DSN='postgresql+psycopg://...' .venv/bin/python -m pytest -q -m postgresql tests/test_subcontract_settlement_export.py
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_export.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【验收标准】
□ `pytest.ini` 注册 `postgresql` marker。  
□ 无 `POSTGRES_TEST_DSN` 时测试明确 skip，原因清晰。  
□ 有 `POSTGRES_TEST_DSN` 时 PostgreSQL 并发测试非 skip 执行。  
□ 同 key 并发 lock 两个请求都成功，且只有一条 lock operation。  
□ 同 key 并发 release 两个请求都成功，且只有一条 release operation。  
□ replay 响应返回 `idempotent_replay=true`。  
□ 首次执行响应返回 `idempotent_replay=false`。  
□ 同 key 不同 payload 返回幂等冲突。  
□ PostgreSQL 确认真唯一约束存在。  
□ PostgreSQL 迁移 upgrade head 通过。  
□ 定向 `-m postgresql` 测试结果已提交给审计官复核。  
□ 常规结算测试仍通过。  
□ 全量 pytest/unittest/py_compile 仍通过。  

【禁止事项】
- 禁止连接生产或准生产数据库。
- 禁止跳过 PostgreSQL 测试后声称 TASK-002H3 完成。
- 禁止用 mock 替代本任务的 PostgreSQL 并发验证。
- 禁止调用 ERPNext 写接口。
- 禁止创建加工厂对账单主表。
- 禁止创建 ERPNext Purchase Invoice、Payment Entry、GL Entry。
- 禁止修改发料、回料、验货、retry 业务逻辑。

【前置依赖】
TASK-002H2 已通过审计意见书第 53 份；TASK-002H3 通过审计后，允许进入 TASK-006 加工厂对账单任务单。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
