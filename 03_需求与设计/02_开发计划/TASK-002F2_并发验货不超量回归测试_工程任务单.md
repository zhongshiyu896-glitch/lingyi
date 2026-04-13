# TASK-002F2 并发验货不超量回归测试工程任务单

- 任务编号：TASK-002F2
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.1
- 更新时间：2026-04-13 13:41 CST
- 作者：技术架构师
- 审计来源：TASK-002F1 审计意见书第 44 份，结论有条件通过
- 前置依赖：TASK-002A/B1/C1/D1/E1 已通过；TASK-002F1 高危幂等问题已闭环但仍缺并发验货不超量测试
- 任务边界：只补并发验货不超量回归测试；若测试失败，只允许修复验货行锁/事务/剩余可验数量计算；不得进入加工厂对账、结算、应付、付款、ERPNext GL/AP

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002F2
模块：并发验货不超量回归测试
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
补齐两个请求同时验同一 `receipt_batch_no` 时不会超过该批次已同步回料数量的回归测试，锁住验货并发安全边界。

【模块概述】
外发验货按回料批次扣款计价。如果两个操作员或两个请求同时验同一个回料批次，系统必须保证最终 `sum(inspection.inspected_qty)` 不超过该批次已同步回料数量。当前代码依赖生产库 `FOR UPDATE` 与剩余可验数量校验，但测试缺少真实并发覆盖；本任务只补测试和必要的并发保护修正，确保后续重构不会让超验回潮。

【涉及文件】
新建或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py（仅当并发测试失败时允许修改）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py（仅当需要调整事务边界时允许修改）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_inspection.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_inspection_concurrency.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/conftest.py（仅当需要 PostgreSQL 集成测试标记/夹具时允许修改）
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/requirements-dev.txt（仅当新增并发测试依赖时允许修改）

【并发测试要求】
1. 必须新增 `test_inspect_concurrent_requests_do_not_overinspect` 或同等命名测试。
2. 测试必须使用两个独立 session 或两个独立客户端请求。
3. 测试必须让两个请求同时验同一个 `receipt_batch_no`。
4. 测试前置数据：同一外发单、同一已同步成功回料批次、批次已回料数量固定，例如 `received_qty=100`。
5. 两个并发请求的验货数量之和必须大于批次已回料数量，例如 `70 + 70 > 100`。
6. 最终数据库中该批次 `sum(inspection.inspected_qty) <= received_qty`。
7. 允许结果一：一个请求成功，另一个返回 `SUBCONTRACT_INSPECTION_QTY_EXCEEDED`。
8. 允许结果二：一个请求成功，另一个因锁等待后重新计算剩余数量并返回业务错误。
9. 不允许两个请求都成功且累计验货数量超过批次已回料数量。
10. 不允许通过同一个 SQLAlchemy session 模拟并发。
11. 如果 SQLite 无法可靠覆盖行锁语义，必须新增 PostgreSQL 集成测试，并用明确标记隔离，例如 `@pytest.mark.postgres`。
12. PostgreSQL 集成测试缺少数据库连接时可以 skip，但必须同时保留一个不依赖 PostgreSQL 的服务层防回归测试，验证 `_must_get_receipt_batch_rows()` 或等价逻辑仍启用锁/重新计算剩余数量。
13. CI 输出必须能看出并发测试是否运行、是否 skip、skip 原因是什么。

【必要修复规则】
如果新增并发测试失败，只允许按以下方向修复：
1. 验货读取目标 receipt batch 时必须在生产数据库使用 `FOR UPDATE` 或等效行锁。
2. 剩余可验数量必须在锁内重新计算。
3. 插入 inspection 和更新主单汇总必须与剩余可验数量校验在同一事务内完成。
4. 并发冲突不得返回 200 成功壳。
5. 并发冲突不得写入第二条超量 inspection。
6. 并发冲突错误优先使用 `SUBCONTRACT_INSPECTION_QTY_EXCEEDED`。
7. 数据库锁超时或死锁必须映射为安全错误码，不得泄露 SQL 原文。
8. 不得用进程内全局锁替代数据库事务锁。
9. 不得用 sleep 作为唯一并发保证。

【详情接口安全顺序】
同时收口第 44 份风险项：
1. `GET /api/subcontract/{id}` 必须先完成订单级资源权限校验。
2. 权限通过后才读取 `latest_issue_outbox/latest_receipt_outbox/inspections[]/receipts[]/status_logs[]` 等子表明细。
3. 无权限用户不得触发子表明细查询。
4. 权限源不可用必须返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得读取子表明细。
5. 若本轮只补测试，也必须增加防回归测试覆盖“资源鉴权失败时不读 inspections 明细”。

【迁移口径确认】
1. TASK-002F/002F1 的验货字段必须通过独立 Alembic migration 补齐。
2. 如果当前代码仍只改 `task_002c_subcontract_company_and_schema.py`，必须新增补丁迁移。
3. 已执行 TASK-002C revision 的数据库执行 TASK-002F migration 后必须拥有验货字段和索引。
4. 空库升级到 head 必须拥有验货字段和索引。

【验收标准】
□ 新增并发验货测试，两个独立 session/client 同时验同一 `receipt_batch_no`。  
□ 两个并发请求验货数量之和大于批次已回料数量。  
□ 最终 `sum(inspection.inspected_qty) <= receipt.received_qty`。  
□ 不出现两个请求都成功且累计超验。  
□ 失败请求返回 `SUBCONTRACT_INSPECTION_QTY_EXCEEDED` 或明确并发/锁冲突错误信封。  
□ 并发失败不写超量 inspection。  
□ 主单 `inspected_qty/rejected_qty/accepted_qty/gross_amount/deduction_amount/net_amount` 不被超量更新。  
□ 测试必须使用两个独立 session/client，不得同 session 顺序模拟。  
□ 如 SQLite 无法验证行锁，必须提供 PostgreSQL 集成测试标记和 skip 原因。  
□ 同时保留不依赖 PostgreSQL 的服务层防回归测试。  
□ `GET /api/subcontract/{id}` 必须资源鉴权通过后再读取 inspections 等子表明细。  
□ 无权限详情请求不读取 inspections 明细。  
□ 权限源不可用详情请求不读取 inspections 明细。  
□ TASK-002F 独立 Alembic migration 存在，或明确已有独立迁移已覆盖验货字段。  
□ 已执行 TASK-002C revision 的库可通过 TASK-002F migration 补齐验货字段。  
□ 全量 pytest 通过。  
□ unittest discover 通过。  
□ py_compile 通过。  
□ 业务代码扫描不出现 `STE-ISS-*`、`STE-REC-*` 伪库存号生成。  
□ 业务代码扫描不出现旧公式 `net_amount = inspected_qty - deduction_amount`。  
□ 业务代码扫描不出现有效口径 `gross_amount = accepted_qty * subcontract_rate`。

【测试要求】
必须新增或补齐以下测试：
1. `test_inspect_concurrent_requests_do_not_overinspect`
2. `test_inspect_concurrent_requests_one_succeeds_one_rejected_when_total_exceeds_batch_qty`
3. `test_inspect_concurrent_requests_do_not_overupdate_order_rollups`
4. `test_inspect_concurrent_conflict_does_not_insert_extra_inspection`
5. `test_inspect_receipt_batch_query_uses_lock_on_postgresql`
6. `test_subcontract_detail_does_not_load_inspections_before_resource_permission`
7. `test_subcontract_detail_permission_source_unavailable_does_not_load_child_rows`
8. `test_task_002f_independent_migration_exists_or_patch_migration_covers_existing_task_002c_db`

【TASK-002F3 审计整改补充】
1. `test_inspect_concurrent_requests_do_not_overinspect` 不允许无条件 `skipTest()`。
2. 必须注册 `postgresql` pytest marker。
3. 无 `POSTGRES_TEST_DSN` 时可 skip；有 `POSTGRES_TEST_DSN` 时必须真实执行 PostgreSQL 双事务并发测试。
4. 工程师交付复审必须提供带 `POSTGRES_TEST_DSN` 的 PostgreSQL 并发测试运行结果。
5. `inspect` 路由的 `before_data/get_order_snapshot()` 必须放在资源鉴权之后，避免鉴权前读取子表快照。

【禁止事项】
- 禁止用同一个 session 顺序调用冒充并发测试。
- 禁止用进程内全局锁替代数据库事务锁。
- 禁止用 sleep 作为唯一并发保护。
- 禁止两个超量请求都返回成功。
- 禁止并发冲突写入超量 inspection。
- 禁止详情接口在资源鉴权前读取 inspections/receipts/status_logs 子表明细。
- 禁止继续只依赖已执行过的 TASK-002C 旧 migration 补 TASK-002F 字段。
- 禁止实现加工厂对账单、结算、应付、付款、GL。
- 禁止验货接口调用 ERPNext 写接口。
- 禁止生成 `STE-ISS-*`、`STE-REC-*` 或任何伪 `stock_entry_name`。
- 禁止使用 `detail=str(exc)` 或普通日志输出 SQL/密钥/ERPNext 敏感响应。

【前置依赖】
TASK-002F1 有条件通过；必须先完成本任务并通过复审，才允许进入 TASK-002G/TASK-002H。

【预计工时】
0.5-1 天

════════════════════════════════════════════════════════════════════════════

【版本记录】
| 版本 | 更新时间 | 作者 | 说明 |
| --- | --- | --- | --- |
| V1.0 | 2026-04-13 13:26 CST | 技术架构师 | 初版 TASK-002F2 并发验货不超量回归测试任务单 |
| V1.1 | 2026-04-13 13:41 CST | 技术架构师 | 同步 TASK-002F3 审计整改：PostgreSQL 并发测试必须真实执行，注册 marker，inspect 快照鉴权后读取 |
