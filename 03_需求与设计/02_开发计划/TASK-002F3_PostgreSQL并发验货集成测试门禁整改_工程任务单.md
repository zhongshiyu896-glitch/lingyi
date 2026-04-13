# TASK-002F3 PostgreSQL 并发验货集成测试门禁整改工程任务单

- 任务编号：TASK-002F3
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 13:41 CST
- 作者：技术架构师
- 审计来源：TASK-002F2 审计意见书第 45 份，结论有条件通过
- 前置依赖：TASK-002A/B1/C1/D1/E1 已通过；TASK-002F2 详情鉴权顺序已闭环，但 PostgreSQL 并发测试仍是无条件 skip 占位
- 任务边界：只补真实可执行 PostgreSQL 并发验货集成测试、pytest marker 配置、inspect 审计快照鉴权顺序；如测试失败，只允许修验货行锁/事务/剩余可验数量计算

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002F3
模块：PostgreSQL 并发验货集成测试门禁整改
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
把 `test_inspect_concurrent_requests_do_not_overinspect` 从无条件 skip 占位改成真实可执行的 PostgreSQL 并发集成测试，并注册 `postgresql` pytest marker，证明生产库行锁语义能防止同一回料批次并发超验。

【模块概述】
SQLite 默认测试只能验证顺序超量，不能证明 PostgreSQL `FOR UPDATE` 在双事务并发下有效。验货金额会进入加工厂对账，如果并发超验漏测，后续对账金额会被放大。本任务把 PostgreSQL 并发测试纳入交付门禁：本地默认没有 `POSTGRES_TEST_DSN` 可以明确 skip，但工程师交付与审计复审必须提供带 `POSTGRES_TEST_DSN` 的真实运行结果。

【涉及文件】
新建或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/pytest.ini
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_inspection.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_inspection_concurrency.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py（仅当真实并发测试失败时允许修改）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/requirements-dev.txt（仅当缺少 PostgreSQL driver 时允许修改）

【pytest marker 配置】
必须新增或修改 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/pytest.ini`：

```ini
[pytest]
markers =
    postgresql: tests requiring PostgreSQL row-lock semantics and POSTGRES_TEST_DSN
```

要求：
1. 全量 pytest 不得再出现 `PytestUnknownMarkWarning: Unknown pytest.mark.postgresql`。
2. 默认无 `POSTGRES_TEST_DSN` 时，PostgreSQL 集成测试可以 skip，但必须显示 skip 原因。
3. 设置 `POSTGRES_TEST_DSN` 时，测试必须真实执行，不得再 `skipTest()`。

【PostgreSQL 集成测试要求】
1. `test_inspect_concurrent_requests_do_not_overinspect` 必须删除无条件 `self.skipTest()`。
2. 使用环境变量 `POSTGRES_TEST_DSN` 控制测试数据库连接。
3. 未设置 `POSTGRES_TEST_DSN` 时允许 skip，skip reason 必须是 `POSTGRES_TEST_DSN not set` 或等价明确原因。
4. 设置 `POSTGRES_TEST_DSN` 时必须真实创建两个独立连接或两个独立 SQLAlchemy Session。
5. 两个并发请求必须针对同一外发单、同一已同步成功 `receipt_batch_no`。
6. 批次已回料数量固定，例如 `received_qty=100`。
7. 两个并发验货请求数量之和必须大于已回料数量，例如 `70 + 70 > 100`。
8. 使用 `threading.Barrier`、`ThreadPoolExecutor` 或等价机制让两个事务真实并发进入验货逻辑。
9. 禁止用同一个 session 顺序调用模拟并发。
10. 禁止用 sleep 作为唯一并发同步手段。
11. 最终数据库断言：`sum(inspection.inspected_qty where receipt_batch_no=目标批次) <= received_qty`。
12. 结果断言：不允许两个请求都成功且累计超验。
13. 允许一个成功、另一个返回 `SUBCONTRACT_INSPECTION_QTY_EXCEEDED`。
14. 如果发生数据库锁超时或死锁，必须返回统一错误信封或明确测试失败，不得吞掉异常当作通过。
15. 测试完成后必须清理测试数据，避免污染复用 PostgreSQL 测试库。
16. 测试不得依赖 ERPNext 外部服务，ERPNext 权限与主数据依赖必须使用已有 mock/stub。

【合并/交付门禁】
1. TASK-002F3 复审前，工程师必须提供默认测试结果：`.venv/bin/python -m pytest -q`。
2. TASK-002F3 复审前，工程师必须提供 PostgreSQL 并发测试结果：`POSTGRES_TEST_DSN=... .venv/bin/python -m pytest -q -m postgresql tests/test_subcontract_inspection_concurrency.py` 或等价命令。
3. 如果项目当前没有 CI，工程师必须在本地 PostgreSQL 测试库运行上述命令并回报输出。
4. 后续合并门禁必须包含至少一个 PostgreSQL job；若短期没有 CI，审计复审以工程师提供的本地 PostgreSQL 命令输出为最低门禁。
5. PostgreSQL 并发测试不得长期只作为 skip 占位保留。

【inspect 审计快照安全顺序】
同步收口第 45 份风险项：
1. `POST /api/subcontract/{id}/inspect` 中 `before_data = service.get_order_snapshot(...)` 必须移到资源权限校验之后。
2. 未登录、无动作权限、无资源权限、权限源不可用时，不得读取 latest issue/receipt outbox 或 inspections 等子表快照。
3. 如果审计前置必须记录基础信息，只能读取主单最小字段，不得读取子表明细。
4. 增加防回归测试：无资源权限或权限源不可用时，inspect 路由不调用 `get_order_snapshot()` 或不读取子表明细。

【必要修复规则】
如果真实 PostgreSQL 并发测试失败，只允许按以下方向修复：
1. `_must_get_receipt_batch_rows()` 或等价回料批次读取必须在 PostgreSQL 上使用 `FOR UPDATE`。
2. 剩余可验数量必须在锁内重新计算。
3. 插入 inspection、更新主单汇总、写状态日志必须与剩余可验校验在同一事务内完成。
4. 并发失败不得写超量 inspection。
5. 主单汇总不得超量更新。
6. 不得用进程内全局锁替代数据库事务锁。
7. 不得放宽验货数量校验。

【验收标准】
□ `pytest.ini` 注册 `postgresql` marker。  
□ 全量 pytest 不再出现 unknown marker warning。  
□ `test_inspect_concurrent_requests_do_not_overinspect` 不再无条件 `skipTest()`。  
□ 无 `POSTGRES_TEST_DSN` 时 PostgreSQL 测试明确 skip，并说明原因。  
□ 有 `POSTGRES_TEST_DSN` 时 PostgreSQL 测试真实执行。  
□ PostgreSQL 测试使用两个独立连接或两个独立 Session。  
□ 两个并发请求验同一 `receipt_batch_no`。  
□ 两个请求数量之和大于批次已回料数量。  
□ 最终 `sum(inspection.inspected_qty) <= receipt.received_qty`。  
□ 不出现两个请求都成功且累计超验。  
□ 并发失败不写超量 inspection。  
□ 主单汇总不被超量更新。  
□ PostgreSQL 测试完成后清理测试数据。  
□ 工程师交付必须提供带 `POSTGRES_TEST_DSN` 的测试命令输出。  
□ `inspect` 路由资源鉴权前不得读取子表快照。  
□ 无权限 inspect 请求不调用 `get_order_snapshot()` 或不读取子表明细。  
□ 权限源不可用 inspect 请求不调用 `get_order_snapshot()` 或不读取子表明细。  
□ 全量 pytest 通过。  
□ unittest discover 通过。  
□ py_compile 通过。  
□ 业务代码扫描不出现 `STE-ISS-*`、`STE-REC-*` 伪库存号生成。  
□ 业务代码扫描不出现旧公式 `net_amount = inspected_qty - deduction_amount`。  
□ 业务代码扫描不出现有效口径 `gross_amount = accepted_qty * subcontract_rate`。

【测试要求】
必须新增或修改以下测试：
1. `test_inspect_concurrent_requests_do_not_overinspect`
2. `test_inspect_postgresql_concurrent_requests_one_succeeds_one_rejected_when_total_exceeds_batch_qty`
3. `test_inspect_postgresql_concurrent_requests_do_not_overupdate_order_rollups`
4. `test_inspect_postgresql_concurrent_conflict_does_not_insert_extra_inspection`
5. `test_postgresql_marker_registered_without_warning`
6. `test_inspect_does_not_snapshot_child_rows_before_resource_permission`
7. `test_inspect_permission_source_unavailable_does_not_snapshot_child_rows`

【禁止事项】
- 禁止保留无条件 `skipTest()` 占位。
- 禁止未注册 `postgresql` marker。
- 禁止把 PostgreSQL 并发测试长期排除在交付复审之外。
- 禁止用同一个 session 顺序调用冒充并发。
- 禁止用进程内全局锁替代数据库事务锁。
- 禁止用 sleep 作为唯一并发保护。
- 禁止两个超量请求都返回成功。
- 禁止并发冲突写入超量 inspection。
- 禁止 inspect 路由在资源鉴权前读取子表快照。
- 禁止实现加工厂对账单、结算、应付、付款、GL。
- 禁止验货接口调用 ERPNext 写接口。
- 禁止生成 `STE-ISS-*`、`STE-REC-*` 或任何伪 `stock_entry_name`。
- 禁止使用 `detail=str(exc)` 或普通日志输出 SQL/密钥/ERPNext 敏感响应。

【前置依赖】
TASK-002F2 有条件通过；必须先完成本任务并通过复审，才允许进入 TASK-002G/TASK-002H。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════
