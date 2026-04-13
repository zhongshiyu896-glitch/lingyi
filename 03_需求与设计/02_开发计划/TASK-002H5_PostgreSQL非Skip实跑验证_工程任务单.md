# TASK-002H5 PostgreSQL 非 Skip 实跑验证工程任务单

- 任务编号：TASK-002H5
- 模块：外发加工管理
- 优先级：P1
- 版本：V1.0
- 更新时间：2026-04-13 16:15 CST
- 作者：技术架构师
- 审计来源：TASK-002H4 审计意见书第 55 份通过，剩余风险为当前环境未提供真实 `POSTGRES_TEST_DSN`，4 条 PostgreSQL 并发/唯一约束集成测试仍为 skip
- 架构裁决：进入 TASK-006 前，必须使用一次性 PostgreSQL 测试库并设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`，以非 skip 方式跑通结算 lock/release 并发集成测试
- 前置依赖：TASK-002H4 已通过；继续遵守外发模块 V1.23、ADR-049、ADR-050、ADR-051
- 任务边界：只做 PostgreSQL 测试环境准备、非 skip 实跑、证据整理和必要的测试依赖补齐；不得修改结算业务逻辑、不得创建 TASK-006 对账单主表、不得调用 ERPNext 写接口

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002H5
模块：PostgreSQL 非 Skip 实跑验证
优先级：P1（TASK-006 前置测试门禁）
════════════════════════════════════════════════════════════════════════════

【任务目标】
在一次性 PostgreSQL 测试库上非 skip 跑通结算并发集成测试，补齐 TASK-006 前缺失的真实 PostgreSQL 行锁与唯一约束验证证据。

【模块概述】
TASK-002H2 已修复结算 lock/release 同 key 并发 replay 逻辑，TASK-002H3 已补 PostgreSQL 集成测试，TASK-002H4 已补 destructive 测试安全门禁。当前唯一未闭环的是：没有真实 `POSTGRES_TEST_DSN`，所以 4 条 PostgreSQL 并发/唯一约束测试仍为 skip。TASK-006 加工厂对账单将依赖结算锁定结果，因此必须先在真实 PostgreSQL 上证明行锁、唯一约束等待和 replay 行为可用。

【涉及文件】
必须使用：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_settlement_postgresql.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/pytest.ini

允许修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/requirements-dev.txt（仅限缺少 PostgreSQL 驱动时补测试依赖）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/README.md 或测试说明（仅限记录 PostgreSQL 集成测试运行方式）

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py（除非真实非 skip 测试暴露生产缺陷，必须先停下回报并另出整改任务）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py（除非迁移/约束事实与文档不一致，必须先停下回报并另出整改任务）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/factory_statement.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/factory_statement_service.py

【环境准备要求】
1. 必须创建一次性 PostgreSQL 测试库，不得使用生产、预发、开发共享库或 ERPNext 真实业务库。
2. 数据库名必须命中 destructive gate 白名单之一：
   - 以 `_test` 结尾，例如 `lingyi_test`
   - 以 `test_` 开头，例如 `test_lingyi`
   - 以 `lingyi_test_` 开头，例如 `lingyi_test_20260413`
   - 以 `tmp_lingyi_` 开头，例如 `tmp_lingyi_ci_001`
3. 必须设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。
4. 必须设置 `POSTGRES_TEST_DSN`，且 DSN 只允许指向上述一次性测试库。
5. 如缺少 PostgreSQL Python 驱动，只允许补测试依赖，不得绕过 PostgreSQL 测试。
6. 输出日志和回报中必须脱敏 DSN，不得出现数据库密码、账号凭据或完整连接串。
7. destructive 测试会清理 `ly_schema`，只能在一次性测试库执行。

【执行命令】
```bash
cd /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service

# 1. 先确认门禁单测和无 DSN skip 行为仍正常
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_postgresql.py

# 2. 使用一次性 PostgreSQL 测试库非 skip 实跑 marker 测试
POSTGRES_TEST_ALLOW_DESTRUCTIVE=true \
POSTGRES_TEST_DSN='postgresql+psycopg://<user>:<password>@<host>:<port>/<db_name_matching_test_whitelist>' \
.venv/bin/python -m pytest -q -m postgresql tests/test_subcontract_settlement_postgresql.py

# 3. 结算定向回归
.venv/bin/python -m pytest -q tests/test_subcontract_settlement_export.py

# 4. 全量回归
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【非 Skip 验证要求】
1. `-m postgresql` 命令必须实际执行 PostgreSQL marker 用例，不得全部 skip。
2. 预期至少覆盖以下 4 条真实 PostgreSQL 用例：
   - 同 key 并发 lock replay
   - 同 key 并发 release replay
   - 同 key 不同 payload 幂等冲突
   - `ly_subcontract_settlement_operation` 唯一约束存在并生效
3. 同 key 并发 lock 必须两个请求成功，只有一条 lock operation，其中一个响应 `idempotent_replay=true`。
4. 同 key 并发 release 必须两个请求成功，只有一条 release operation，其中一个响应 `idempotent_replay=true`。
5. 同 key 不同 payload 必须返回 `SUBCONTRACT_SETTLEMENT_IDEMPOTENCY_CONFLICT`。
6. PostgreSQL 唯一约束必须验证 `operation_type + idempotency_key` 生效。
7. 如果 marker 结果仍是全部 skip，本任务不得回报完成。
8. 如果真实 PostgreSQL 测试失败，不得用 mock 替代；必须保留失败输出并回报架构师/审计官。

【验收标准】
□ 已提供一次性 PostgreSQL 测试库，库名命中测试库白名单。  
□ 已设置 `POSTGRES_TEST_ALLOW_DESTRUCTIVE=true`。  
□ `POSTGRES_TEST_DSN` 已脱敏回报，不泄露账号密码。  
□ `.venv/bin/python -m pytest -q -m postgresql tests/test_subcontract_settlement_postgresql.py` 非 skip 通过。  
□ PostgreSQL marker 用例没有全部 skip。  
□ 同 key 并发 lock PostgreSQL 测试通过。  
□ 同 key 并发 release PostgreSQL 测试通过。  
□ 同 key 不同 payload PostgreSQL 测试通过。  
□ operation 唯一约束 PostgreSQL 测试通过。  
□ `tests/test_subcontract_settlement_postgresql.py` 常规门禁测试通过。  
□ `tests/test_subcontract_settlement_export.py` 结算定向测试通过。  
□ 全量 pytest/unittest/py_compile 通过。  
□ 回报中列出每条命令的结果和 skipped 数量。  
□ 未修改结算业务逻辑、未创建 TASK-006 对账单主表、未调用 ERPNext 写接口。  

【回报格式】
工程师完成后按以下格式回报：

```text
TASK-002H5 PostgreSQL 非 Skip 实跑验证完成。

测试库：<脱敏后的数据库名，例如 lingyi_test_20260413>
Destructive gate：POSTGRES_TEST_ALLOW_DESTRUCTIVE=true，数据库名白名单通过

验证结果：
- tests/test_subcontract_settlement_postgresql.py：X passed, Y skipped
- -m postgresql：X passed, 0 skipped（必须非 skip）
- tests/test_subcontract_settlement_export.py：X passed
- 全量 pytest：X passed, Y skipped
- unittest discover：Ran X tests OK
- py_compile：通过

PostgreSQL 非 skip 覆盖：
- 同 key 并发 lock replay：通过
- 同 key 并发 release replay：通过
- 同 key 不同 payload 冲突：通过
- operation 唯一约束：通过

改动文件：
- [如无代码改动，写“无”]
- [如只补依赖/README，列出路径]

风险/说明：
- [如无，写“无”]
```

【禁止事项】
- 禁止连接生产、预发、开发共享库或 ERPNext 真实业务库。
- 禁止在非测试库执行 `DROP SCHEMA ly_schema CASCADE`。
- 禁止仅凭 `POSTGRES_TEST_DSN` 跑 destructive 测试，必须同时设置 allow env。
- 禁止把全部 skip 的结果回报为完成。
- 禁止用 SQLite、mock 或 monkeypatch 结果替代 PostgreSQL 非 skip 验证。
- 禁止泄露完整 DSN、账号、密码。
- 禁止修改结算业务逻辑来“适配测试”，真实 PostgreSQL 暴露缺陷时先停下回报。
- 禁止进入 TASK-006 代码实现。
- 禁止创建加工厂对账单主表、Purchase Invoice、Payment Entry 或 GL。
- 禁止调用 ERPNext 写接口。

【前置依赖】
TASK-002H4 审计意见书第 55 份通过。

【后置门禁】
TASK-002H5 通过审计后，才允许进入 TASK-006 加工厂对账单模块开发。

【预计工时】
0.5 天

════════════════════════════════════════════════════════════════════════════
