# TASK-004A1 生产计划审计阻断整改工程任务单

- 任务编号：TASK-004A1
- 模块：生产计划集成
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-13 18:13 CST
- 作者：技术架构师
- 审计来源：审计意见书第 62 份，TASK-004A 不通过，高危 2 / 中危 3
- 前置依赖：TASK-004A 已交付但审计不通过；本任务只允许修复 TASK-004A 阻断项
- 架构依据：`/03_需求与设计/01_架构设计/05_模块设计_生产计划集成.md` V1.1；`ADR-059`
- 任务边界：只修生产计划接口契约、Work Order outbox 原子 claim、映射表字段/索引、测试缺口；不做前端、不做生产入库、不做外发单自动创建、不做 TASK-005/TASK-006

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-004A1
模块：生产计划审计阻断整改
优先级：P0（审计阻断修复）
════════════════════════════════════════════════════════════════════════════

【任务目标】
关闭审计意见书第 62 份的 5 个必改问题，使 TASK-004A 达到复审条件。

【模块概述】
TASK-004A 已完成生产计划主链路骨架，但审计发现接口契约、outbox 并发认领、映射表结构和测试覆盖还没有达到架构任务单要求。本任务只做审计阻断整改，不扩展新业务范围。整改完成后，生产计划后端应能准确表达物料检查仓库、Work Order 的成品仓/WIP 仓/开工日期，并确保多个 worker 并发时不会重复创建 ERPNext Work Order。所有改动必须继续遵守 outbox/worker、权限 fail closed、审计闭环和日志脱敏原则。

【涉及文件】
修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/production.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_outbox_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/production_work_order_worker.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_production_adapter.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_004a_create_production_tables.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_plan.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_work_order_outbox.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_job_card_sync.py

如需要新增：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_production_work_order_worker_postgresql.py

禁止修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_settlement_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_job_card_sync_worker.py
- 任意 TASK-005/TASK-006 文件

【整改清单】

| 编号 | 严重级别 | 整改项 | 必须结果 |
| --- | --- | --- | --- |
| FIX-001 | P1 | 补齐 `material-check` 与 `create-work-order` 请求体契约 | 仓库、成品仓、WIP 仓、开工日期、幂等键全部落到 schema、router、service、outbox payload、测试 |
| FIX-002 | P1 | 修复 Work Order outbox worker 原子 claim 与 lease 恢复 | 并发 worker 不重复认领；processing 超过 lease 后可恢复；不得长事务包 ERPNext 调用 |
| FIX-003 | P2 | 补齐 `ly_production_work_order_link` 唯一约束、同步字段和索引 | `plan_id` 数据库唯一；有 `last_synced_at/created_by`；有 `sync_status` 索引 |
| FIX-004 | P2 | 补齐 `ly_production_job_card_link` 资源字段和同步字段 | 有 `company/item_code/operation_sequence/synced_at`；同步服务正确写入；有 `company,item_code` 索引 |
| FIX-005 | P2 | 补齐 TASK-004A 必测缺口 | 覆盖 Closed SO、BOM mismatch、DB/AUDIT 失败、仓库必填、worker 并发、commit 失败不调用 ERPNext |

【接口契约整改】

1. 新增 `ProductionMaterialCheckRequest`。
2. `POST /api/production/plans/{plan_id}/material-check` 必须接收请求体：

```json
{
  "warehouse": "WIP Warehouse - LY"
}
```

3. `warehouse` 必填且去空白后不能为空；缺失或空白返回 `PRODUCTION_WAREHOUSE_REQUIRED`。
4. 物料检查写入 `ly_production_plan_material.warehouse`。
5. 后续如读取 ERPNext Bin/Stock Balance，只允许读取快照，不得锁库存、不得修改库存。
6. 新增 `ProductionCreateWorkOrderRequest`。
7. `POST /api/production/plans/{plan_id}/create-work-order` 必须接收请求体：

```json
{
  "fg_warehouse": "Finished Goods - LY",
  "wip_warehouse": "Work In Progress - LY",
  "start_date": "2026-04-13",
  "idempotency_key": "client-generated-key"
}
```

8. `fg_warehouse/wip_warehouse/start_date/idempotency_key` 必填；仓库字段去空白后不能为空。
9. 缺少任一仓库返回 `PRODUCTION_WAREHOUSE_REQUIRED`。
10. `idempotency_key` 缺失或空白必须返回统一错误信封，不得裸 500。
11. `fg_warehouse/wip_warehouse/start_date/idempotency_key` 必须进入 outbox `payload_json`。
12. `payload_hash` 必须包含 `fg_warehouse/wip_warehouse/start_date`。
13. 同一 `plan_id + idempotency_key` 相同 payload 重试返回首次 outbox。
14. 同一 `plan_id + idempotency_key` 不同 payload 返回 `PRODUCTION_IDEMPOTENCY_CONFLICT`。
15. 如果计划已有成功 `work_order_link`，重复 create-work-order 必须返回已有 `work_order`，不得新建 outbox。
16. 如果计划已有 pending/processing outbox，重复请求必须返回已有 outbox，除非 idempotency_key 相同但 payload 不同，此时返回冲突。

【Worker 原子 Claim 整改】

1. Work Order outbox 必须支持 lease 字段，优先新增 `lease_until`；如复用 `locked_at`，必须有明确过期计算和测试。
2. `claim_due()` 必须原子认领 due outbox。
3. PostgreSQL 实现必须使用 `SELECT ... FOR UPDATE SKIP LOCKED` 或等价原子 `UPDATE ... WHERE ... RETURNING`。
4. due 条件必须包括：
   - `status in ('pending', 'failed') and next_retry_at <= now`
   - `status='processing' and lease_until < now`
5. claim 成功后必须写入：`status='processing'`、`locked_by/worker_id`、`locked_at`、`lease_until`、`attempts`。
6. Worker 必须先 claim 并提交，再调用 ERPNext API。
7. ERPNext 调用不得发生在持有 outbox 行锁的数据库事务内。
8. Worker 崩溃后，超过 lease 的 processing outbox 必须可被后续 worker 重新认领。
9. 两个 worker 并发处理同一 outbox 时，ERPNext create/submit 调用最多发生一次。
10. claim/回写阶段数据库异常必须返回或抛出系统错误，不得吞错返回 200。

【数据库表整改】

`ly_schema.ly_production_work_order_link` 必须补齐：
- `plan_id` 唯一约束：`uk_ly_production_work_order_plan(plan_id)`
- `sync_status` 索引：`idx_ly_production_work_order_sync_status(sync_status)`
- `last_synced_at`
- `created_by`

`ly_schema.ly_production_job_card_link` 必须补齐：
- `company`
- `item_code`
- `operation_sequence`
- `synced_at`
- `idx_ly_production_job_card_company_item(company, item_code)`

`ly_schema.ly_production_work_order_outbox` 建议补齐：
- `lease_until`
- `payload_hash`，如当前没有单独字段
- `idx_ly_production_work_order_outbox_lease(status, next_retry_at, lease_until)` 或等效索引

迁移要求：
1. 空库迁移必须能自举全部生产计划表。
2. 已存在表迁移必须幂等升级。
3. 添加 `plan_id` 唯一约束前必须检测重复数据；如存在重复，迁移必须 fail closed 并给出明确错误，不得静默选择一条。
4. 所有新增索引/约束命名必须稳定，禁止自动匿名约束名。

【Job Card 同步整改】

1. 同步 Job Card 时必须从生产计划或 Work Order link 派生并写入 `company/item_code`。
2. ERPNext 返回工序顺序时写入 `operation_sequence`；无法获取时允许为空，但不得写错顺序。
3. 每次同步成功写入或更新 `synced_at`。
4. 查询详情时可直接返回本地 Job Card 映射，不得绕过资源权限读取子表。
5. 不得直接更新 ERPNext Job Card 完成数量；完成数量仍由 TASK-003 工票链路负责。

【测试要求】

必须新增或补齐以下测试：
1. `material-check` 缺少 `warehouse` 返回 `PRODUCTION_WAREHOUSE_REQUIRED`。
2. `material-check` 传入 warehouse 后，物料快照写入该 warehouse。
3. `create-work-order` 缺少 `fg_warehouse` 返回 `PRODUCTION_WAREHOUSE_REQUIRED`。
4. `create-work-order` 缺少 `wip_warehouse` 返回 `PRODUCTION_WAREHOUSE_REQUIRED`。
5. `create-work-order` 缺少 `start_date` 返回统一错误信封。
6. `create-work-order` 缺少 `idempotency_key` 返回统一错误信封。
7. `create-work-order` outbox payload 包含 `fg_warehouse/wip_warehouse/start_date`。
8. 同一 `plan_id + idempotency_key` 相同 payload 重试返回同一 outbox。
9. 同一 `plan_id + idempotency_key` 不同 payload 返回 `PRODUCTION_IDEMPOTENCY_CONFLICT`。
10. 已有成功 `work_order_link` 时重复 create-work-order 返回已有 `work_order`，不新建 outbox。
11. create-work-order 本地 commit 失败时 ERPNext 调用次数为 0。
12. SO Closed 返回 `PRODUCTION_SO_CLOSED_OR_CANCELLED`。
13. SO Cancelled 返回 `PRODUCTION_SO_CLOSED_OR_CANCELLED`。
14. BOM item 与 SO 行 item 不一致返回 `PRODUCTION_BOM_ITEM_MISMATCH`。
15. 数据库写失败返回 `DATABASE_WRITE_FAILED`。
16. 操作审计写失败返回 `AUDIT_WRITE_FAILED`。
17. Worker claim 成功后再调用 ERPNext，不持有本地事务跨网络调用。
18. PostgreSQL 或等效并发测试：两个 worker 同时运行，ERPNext create/submit 调用最多一次。
19. lease 过期测试：processing outbox 超过 lease 后可被重新 claim。
20. 未过 lease 的 processing outbox 不会被第二个 worker 抢占。
21. `ly_production_work_order_link.plan_id` 数据库唯一约束生效。
22. Job Card 同步写入 `company/item_code/operation_sequence/synced_at`。
23. 仅授权 ITEM-B 的用户访问 ITEM-A 生产计划详情和子表返回 403，且写安全审计。

【验收标准】

□ 审计意见书第 62 份的 5 个问题均有对应代码和测试闭环。  
□ `POST /api/production/plans/{plan_id}/material-check` 请求体契约已落地。  
□ `POST /api/production/plans/{plan_id}/create-work-order` 请求体契约已落地。  
□ Work Order outbox payload 包含 `fg_warehouse/wip_warehouse/start_date`。  
□ Work Order outbox 幂等冲突能稳定区分相同 payload 和不同 payload。  
□ Worker claim 在 PostgreSQL 下原子，不会并发重复调用 ERPNext。  
□ processing outbox lease 过期后可恢复处理。  
□ `ly_production_work_order_link.plan_id` 唯一约束生效。  
□ `ly_production_job_card_link` 已补齐 `company/item_code/operation_sequence/synced_at`。  
□ 全量 `.venv/bin/python -m pytest -q` 通过。  
□ 全量 `.venv/bin/python -m unittest discover` 通过。  
□ `.venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)` 通过。  
□ 未修改外发结算、工票计薪、BOM 主业务逻辑。  
□ 未进入 TASK-005/TASK-006。  

【禁止事项】

- 禁止弱化或删除 TASK-004A 既有权限校验。
- 禁止把 warehouse/fg_warehouse/wip_warehouse 写成固定默认值绕过契约。
- 禁止在请求事务内调用 ERPNext 创建 Work Order。
- 禁止 worker 持有数据库行锁期间调用 ERPNext。
- 禁止没有 lease 的 processing outbox 永久卡死。
- 禁止 outbox event_key 包含 `outbox_id/request_id/created_at/operator`。
- 禁止只按 item/qty 模糊查重 ERPNext Work Order。
- 禁止自动创建外发单。
- 禁止修改 TASK-005/TASK-006。
- 禁止日志或审计记录 Authorization/Cookie/Token/Secret/完整 DSN/SQLAlchemy 原始 SQL 参数。

【交付回报格式】

工程师完成后按以下格式回复：

```text
TASK-004A1 已完成。

修复项：
1. FIX-001：...
2. FIX-002：...
3. FIX-003：...
4. FIX-004：...
5. FIX-005：...

涉及文件：
- ...

验证结果：
- .venv/bin/python -m pytest -q：...
- .venv/bin/python -m unittest discover：...
- .venv/bin/python -m py_compile $(find app tests scripts -name '*.py' -print)：...

未进入范围：
- 未修改外发结算
- 未进入 TASK-005/TASK-006
- 未自动创建外发单
```

【前置依赖】
TASK-004A 已交付但审计不通过；本任务为阻断整改。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
