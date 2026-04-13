# TASK-002H2 结算并发幂等 Replay 整改工程任务单

- 任务编号：TASK-002H2
- 模块：外发加工管理
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-13 15:43 CST
- 作者：技术架构师
- 审计来源：TASK-002H1 审计意见书第 52 份有条件通过，剩余中危为同 `idempotency_key` 并发重复请求可能在唯一约束处返回 `DATABASE_WRITE_FAILED`，而不是稳定 replay 首次响应
- 架构裁决：结算 operation 并发唯一冲突必须转为幂等 replay 或幂等冲突；lock/release 响应必须显式返回 `idempotent_replay`；`settlement_request_id` 保留为兼容/最近请求标识，但不是完整幂等历史
- 前置依赖：TASK-002H1 主漏洞已修复但有条件通过；继续遵守外发模块 V1.20 与 ADR-048
- 任务边界：只修结算幂等并发唯一冲突 replay、响应标识和兼容字段文档；不得新增加工厂对账单主表、应付、付款、GL 或 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H2
模块：结算并发幂等 Replay 整改
优先级：P1（进入 TASK-006 前必修）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复同一个结算 `idempotency_key` 并发重复请求在唯一约束处变成 `DATABASE_WRITE_FAILED` 的问题，让重复请求稳定返回首次响应或幂等冲突。

【模块概述】
TASK-002H1 已经把结算锁定/释放幂等历史改为 append-only 操作表，解决了 release 后旧 lock 重放的高危问题。当前剩余问题是并发窗口：两个相同幂等请求同时进入时，第二个请求可能在第一次提交前查不到 operation；等第一次提交后，第二个请求写 operation 才撞唯一约束，当前会被当成数据库写失败。幂等接口必须把这种唯一冲突识别为并发 replay，而不是 500。

【涉及文件】
必须修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_export.py

允许修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py（仅限注释/字段说明，不改业务结构）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py（仅限识别唯一冲突辅助）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（仅限测试 fixture）

【实现规则】
1. lock/release 在首次 `_load_operation()` 未命中后，拿到 inspection 行锁后必须再次读取 operation。
2. 第二次读取命中且 `request_hash` 相同：直接返回首次响应，不得修改 inspection。
3. 第二次读取命中但 `request_hash` 不同：返回 `SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT`。
4. 写入 operation 时如果撞上 `operation_type + idempotency_key` 唯一约束，不得返回 `DATABASE_WRITE_FAILED`。
5. 唯一冲突必须进入 replay 分支：rollback 当前 savepoint 或事务内待写状态，重新读取 operation。
6. 重新读取 operation 后，`request_hash` 相同则返回首次响应，`request_hash` 不同则返回 `SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT`。
7. 只有非幂等唯一约束、未知数据库写失败、operation 不存在且无法安全 replay 时，才允许返回 `DATABASE_WRITE_FAILED`。
8. 同 key replay 不得追加第二条 settlement operation。
9. 同 key replay 不得再次写 inspection 状态、statement_id、statement_no、locked_by、locked_at。
10. release replay 同样适用，不得再次修改 inspection。
11. operation replay 响应必须来自 `response_json` 脱敏快照或等价安全重建，禁止重新计算导致金额/字段漂移。
12. `settlement_request_id` 保留为兼容/最近请求标识，仅用于排查最近一次 lock/release 请求；正式幂等历史只看 `ly_subcontract_settlement_operation`。

【响应契约】
lock/release 响应 data 必须新增或确认以下字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `operation_id` | number/null | settlement operation ID |
| `idempotency_key` | string | 本次请求幂等键 |
| `idempotent_replay` | boolean | 首次执行为 `false`，幂等回放为 `true` |

规则：
1. 首次 lock/release 成功：`idempotent_replay=false`。
2. 同 key 同 hash replay：`idempotent_replay=true`。
3. 同 key 不同 hash：返回冲突，不返回成功 data。
4. `response_json` 中不得保存 Authorization、Cookie、token、password、secret、SQL 原文或堆栈。

【并发处理建议】
推荐实现二选一或组合：
1. 在 inspection 行锁后、写 operation 前再次 `_load_operation()`，关闭大部分竞态窗口。
2. 在 `_record_operation_success()` 内使用 savepoint 捕获 `IntegrityError`；若是 `uk_ly_subcontract_settlement_operation_idem` 或等价唯一冲突，则 reload operation 并 replay。
3. PostgreSQL 下同 key 并发请求会在唯一约束等待后进入冲突路径，必须稳定返回 replay。
4. SQLite 测试可用 monkeypatch/模拟唯一冲突覆盖；PostgreSQL 有 DSN 时必须补真实并发测试。

【验收标准】
□ lock 同 key 同 payload 并发重复请求不会返回 `DATABASE_WRITE_FAILED`。  
□ release 同 key 同 payload 并发重复请求不会返回 `DATABASE_WRITE_FAILED`。  
□ lock 同 key同 payload replay 返回首次成功响应，`idempotent_replay=true`。  
□ release 同 key同 payload replay 返回首次成功响应，`idempotent_replay=true`。  
□ lock/release 首次成功返回 `idempotent_replay=false`。  
□ 同 key 不同 payload 返回 `SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT`。  
□ 同 key replay 不新增第二条 settlement operation。  
□ 同 key replay 不再次修改 inspection 行。  
□ 唯一约束冲突只在 operation 幂等约束且 hash 相同时转 replay；其他数据库写失败仍按数据库错误处理。  
□ `settlement_request_id` 文档/注释标明“非完整幂等历史，只是兼容/最近请求标识”。  
□ 不创建 factory_statement 表。  
□ 不调用 ERPNext 写接口。  
□ 不修改发料、回料、验货、retry 既有业务逻辑。  
□ `.venv/bin/python -m pytest -q tests/test_subcontract_settlement_export.py` 通过。  
□ `.venv/bin/python -m pytest -q` 通过。  
□ `.venv/bin/python -m unittest discover` 通过。  
□ `.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)` 通过。  

【必须新增或补齐的测试】
1. `test_settlement_lock_duplicate_unique_conflict_replays_first_response`
2. `test_settlement_release_duplicate_unique_conflict_replays_first_response`
3. `test_settlement_lock_replay_sets_idempotent_replay_true`
4. `test_settlement_release_replay_sets_idempotent_replay_true`
5. `test_settlement_first_lock_sets_idempotent_replay_false`
6. `test_settlement_first_release_sets_idempotent_replay_false`
7. `test_settlement_duplicate_unique_conflict_different_hash_returns_conflict`
8. `test_settlement_duplicate_unique_conflict_does_not_create_second_operation`
9. `test_settlement_duplicate_unique_conflict_does_not_mutate_inspection_again`
10. `test_settlement_request_id_is_not_used_as_idempotency_history`

PostgreSQL 条件测试：
1. 如有 `POSTGRES_TEST_DSN`，新增 `@pytest.mark.postgresql` 测试：两个线程/事务用同一 lock `idempotency_key` 锁同一批 inspection，两个请求都应返回 200，其中一个 `idempotent_replay=true`，operation 表只有一条。
2. 无 `POSTGRES_TEST_DSN` 时允许明确 skip，但必须说明原因。

【禁止事项】
- 禁止把 operation 唯一冲突继续包装成 `DATABASE_WRITE_FAILED`。
- 禁止 replay 时再次修改 inspection。
- 禁止 replay 时追加第二条 operation。
- 禁止继续把 `settlement_request_id` 当作幂等历史来源。
- 禁止创建加工厂对账单主表。
- 禁止创建 ERPNext Purchase Invoice、Payment Entry、GL Entry。
- 禁止调用 ERPNext 写接口。
- 禁止重算历史 inspection 金额。
- 禁止在 response_json 中保存 Authorization、Cookie、token、password、secret、SQL 原文或堆栈。

【前置依赖】
TASK-002H1 审计意见书第 52 份有条件通过；必须完成本任务并通过审计后，才允许继续 TASK-002H 封版或进入 TASK-006。

【预计工时】
1 天

════════════════════════════════════════════════════════════════════════════
