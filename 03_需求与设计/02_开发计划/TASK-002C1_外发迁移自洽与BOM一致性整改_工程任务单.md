# TASK-002C1 外发迁移自洽与 BOM 一致性整改工程任务单

- 任务编号：TASK-002C1
- 模块：外发加工管理
- 优先级：P0
- 版本：V1.0
- 更新时间：2026-04-12 22:21 CST
- 作者：技术架构师
- 审计来源：审计意见书第 37 份，TASK-002C 不通过，高 2 / 中 2
- 前置依赖：TASK-002C 已交付但审计不通过；必须继续遵守外发模块 V1.4、ADR-030、ADR-031、ADR-032、ADR-033
- 任务边界：只修 TASK-002C 审计阻断项；不得进入 TASK-002D/E/F 的发料 outbox、回料 outbox、验货金额口径或 ERPNext Stock Entry worker 实现

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-002C1
模块：外发迁移自洽与 BOM 一致性整改
优先级：P0（阻断修复）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复 TASK-002C 审计不通过的 4 个问题：迁移链自洽、BOM item 与外发 item 一致性、company 解析统一错误信封、回填写失败 rollback。

【模块概述】
TASK-002C 已开始补齐外发本地 `company` 事实字段，但迁移脚本依赖历史基础表存在，新库从迁移链升级会失败。创建外发单也存在事实污染入口：`payload.item_code` 可以和 `bom_id` 指向的 BOM 款式不一致，后续发料 outbox 会被错误 BOM 物料计划带偏。TASK-002C1 必须先把迁移链和创建事实校验修到可审计状态，才能继续进入 TASK-002D。此任务仍然不允许恢复回料、验货、Stock Entry worker 等后续业务成功路径。

【涉及文件】
新建或修改：
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_002c_subcontract_company_and_schema.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/[如需要新增基础表迁移文件].py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/subcontract.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/subcontract_migration_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_item_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_company_migration.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_company_permission.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_permissions.py
- /Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_subcontract_exception_handling.py

【整改问题清单】
| 编号 | 严重程度 | 问题 | 必须结果 |
| --- | --- | --- | --- |
| P1-1 | 高 | TASK-002C 迁移只 `add_column`，但迁移链没有创建外发基础表，新库升级会失败 | 从空库执行迁移链能创建 `ly_subcontract_order/material/receipt/status_log`，再完成 company 字段、索引、约束 |
| P1-2 | 高 | 创建外发单未校验 `bom.item_code == payload.item_code`，可落库错配 BOM | 不一致返回 `SUBCONTRACT_BOM_ITEM_MISMATCH`，不得落库、不得写成功审计 |
| P2-1 | 中 | `_resolve_create_company()` 在统一 `try/except` 外执行，空白 company 等场景返回裸 500 | company 解析错误必须返回统一错误信封，并按规则写失败审计/安全审计 |
| P2-2 | 中 | 回填 execute 写失败未统一 rollback，可能留下脏 session | 所有 `DatabaseWriteFailed/flush` 写失败必须 rollback，调用方后续 commit 不得落半更新 |

【迁移自洽规则】
1. 不得依赖 `metadata.create_all()` 证明迁移可用。
2. 必须提供可执行的 Alembic 迁移链，或在当前迁移中检测基础表不存在时完整创建基础表。
3. 新库从空库升级到 head 时，必须能创建 `ly_subcontract_order`、`ly_subcontract_material`、`ly_subcontract_receipt`、`ly_subcontract_status_log`。
4. 如果当前阶段已定义 `ly_subcontract_inspection`、`ly_subcontract_stock_outbox`、`ly_subcontract_stock_sync_log` 模型，迁移必须至少创建与 TASK-002C 范围一致的表结构或明确拆到后续迁移，不得出现模型有表、迁移链无表的半状态。
5. 已有库升级时，迁移必须只补缺失字段、索引和约束，不得破坏已有数据。
6. `ly_schema` 不存在时，迁移必须先创建 schema。
7. 迁移必须包含 downgrade 或明确项目约束下的可回滚策略。
8. 迁移测试必须从空库执行迁移链，不允许只用 ORM `create_all()`。
9. TASK-002C 阶段 `ly_subcontract_stock_outbox` 只允许作为资源 scope 骨架；完整 outbox 业务字段、幂等唯一约束和 worker 所需索引由 TASK-002D 接管。
10. TASK-002D 不得启动，直到 TASK-002C1 审计通过。

【BOM 与 Item 一致性规则】
1. `_validate_bom_exists()` 或等价函数必须返回 BOM 的 `item_code`。
2. 创建外发单时必须校验 `payload.item_code == bom.item_code`。
3. 不一致时返回 `SUBCONTRACT_BOM_ITEM_MISMATCH`。
4. 不一致时不得新增 `ly_subcontract_order`。
5. 不一致时不得写成功状态日志、成功操作审计或任何子表事实。
6. 显式传入 `company` 时，也必须校验 ERPNext Item 存在且未禁用，或至少以 BOM item 作为本地权威校验，禁止 payload item 与 BOM 脱钩。
7. BOM item 校验必须早于生成外发单号和写入本地事实。
8. BOM item 校验失败必须走统一错误信封，响应不得泄露 SQL、ERPNext 响应原文或敏感凭证。

【company 解析与权限规则】
1. `get_subcontract_user_permissions()`、`_resolve_create_company()`、资源权限校验、service 调用必须放入统一异常处理范围。
2. `company=null/''/'   '` 必须返回 `SUBCONTRACT_COMPANY_REQUIRED`，不得返回裸 500。
3. 公司候选多义必须返回 `SUBCONTRACT_COMPANY_AMBIGUOUS`。
4. 公司候选为空必须返回 `SUBCONTRACT_COMPANY_UNRESOLVED`。
5. ERPNext Item/Supplier/BOM 查询不可用必须返回 `ERPNEXT_SERVICE_UNAVAILABLE` 或 `DATABASE_READ_FAILED`。
6. 权限源不可用必须返回 `PERMISSION_SOURCE_UNAVAILABLE`。
7. 上述错误必须使用统一响应 `{code,message,data}` 或项目既有错误信封，不得返回裸 `Internal Server Error`。
8. 失败操作审计如按当前策略强制成功，审计写失败必须返回 `AUDIT_WRITE_FAILED` 并 rollback。
9. Company-only 权限策略：允许拥有动作权限且 ERPNext 权限源明确返回 Company 范围、且 Item/Supplier/Warehouse 为“无显式限制”的用户访问该 Company 内外发单；但必须区分“无显式限制”和“权限源不可用/查询失败”，后者必须 fail closed。
10. 如果 ERPNext 明确配置了 Item/Supplier/Warehouse 限制，则必须继续叠加校验，不得仅凭 company 放行。

【回填 rollback 规则】
1. `backfill_subcontract_company_scope()` 必须捕获 `DatabaseWriteFailed`。
2. `_propagate_company_to_children()` 抛 `DatabaseWriteFailed` 时，execute 模式必须 rollback。
3. 末尾 `flush()` 抛 `DatabaseWriteFailed` 或 `SQLAlchemyError` 时，必须 rollback 后再抛标准错误。
4. rollback 后 `session.new/session.dirty/session.deleted` 不得残留可 commit 的半更新对象。
5. 调用方捕获异常后继续 `session.commit()`，不得落库主单 company、子表 company、状态变更、回填日志或审计副作用。
6. dry-run 继续保持真正只读，不得因本次整改引入 ORM 挂载副作用。

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 本任务要求 |
| --- | --- | --- | --- |
| 创建外发单 | POST | `/api/subcontract/` | 校验 BOM item 与 payload item 一致；company 解析错误走统一错误信封 |
| 外发列表 | GET | `/api/subcontract/` | Company-only 策略按本任务规则处理；权限源不可用 fail closed |
| 外发详情 | GET | `/api/subcontract/{id}` | 继续以本地 `order.company` 做资源权限校验 |
| 回料门禁 | POST | `/api/subcontract/{id}/receive` | 继续 fail closed，不恢复业务成功路径 |
| 验货门禁 | POST | `/api/subcontract/{id}/inspect` | 继续 fail closed，不恢复业务成功路径 |
| 迁移预检 | 内部服务函数 | `build_subcontract_company_backfill_plan(dry_run=True)` | 继续只读 |
| 迁移执行 | 内部服务函数 | `backfill_subcontract_company_scope(dry_run=False)` | 写失败必须 rollback |

【错误码】
必须使用或补齐：
- `SUBCONTRACT_BOM_ITEM_MISMATCH`
- `SUBCONTRACT_COMPANY_REQUIRED`
- `SUBCONTRACT_COMPANY_UNRESOLVED`
- `SUBCONTRACT_COMPANY_AMBIGUOUS`
- `SUBCONTRACT_SCOPE_BLOCKED`
- `ERPNEXT_SERVICE_UNAVAILABLE`
- `DATABASE_READ_FAILED`
- `DATABASE_WRITE_FAILED`
- `PERMISSION_SOURCE_UNAVAILABLE`
- `AUDIT_WRITE_FAILED`
- `AUTH_UNAUTHORIZED`
- `AUTH_FORBIDDEN`

【验收标准】
□ 从空数据库执行迁移链能成功创建 `ly_schema`。  
□ 从空数据库执行迁移链能成功创建 `ly_subcontract_order/material/receipt/status_log`。  
□ 从空数据库执行迁移链能成功完成 TASK-002C 的 company 字段、索引和约束。  
□ 迁移测试不得使用 ORM `metadata.create_all()` 代替 Alembic 迁移。  
□ 已有表场景下重复执行迁移不会重复加列或重复创建索引失败。  
□ `item_code=ITEM-A`、`bom_id` 指向 `ITEM-B` BOM 时，`POST /api/subcontract/` 返回 `SUBCONTRACT_BOM_ITEM_MISMATCH`。  
□ BOM item mismatch 场景不新增 `ly_subcontract_order`。  
□ BOM item mismatch 场景不写成功操作审计或成功状态日志。  
□ 显式传入 company 时仍会校验 Item/BOM 事实一致性。  
□ `company=null` 创建外发单返回 `SUBCONTRACT_COMPANY_REQUIRED`，不是裸 500。  
□ `company=''` 创建外发单返回 `SUBCONTRACT_COMPANY_REQUIRED`，不是裸 500。  
□ `company='   '` 创建外发单返回 `SUBCONTRACT_COMPANY_REQUIRED`，不是裸 500。  
□ 公司候选多义返回 `SUBCONTRACT_COMPANY_AMBIGUOUS`，统一错误信封。  
□ 公司候选为空返回 `SUBCONTRACT_COMPANY_UNRESOLVED`，统一错误信封。  
□ ERPNext Item/Supplier/BOM 查询不可用返回 `ERPNEXT_SERVICE_UNAVAILABLE` 或 `DATABASE_READ_FAILED`，统一错误信封。  
□ 权限源不可用返回 `PERMISSION_SOURCE_UNAVAILABLE`，不得降级为无资源限制。  
□ Company-only 用户在权限源明确“Item/Supplier/Warehouse 无显式限制”时，可以访问该 Company 内外发列表。  
□ Company-only 用户不能访问其他 Company 外发单。  
□ 明确配置 Item 限制时，Company-only 不得绕过 Item 限制。  
□ `_propagate_company_to_children()` 写失败时 rollback，调用方后续 commit 不落半更新。  
□ `flush()` 写失败时 rollback，调用方后续 commit 不落半更新。  
□ dry-run 后 `session.new/session.dirty/session.deleted` 仍为 0。  
□ `receive/inspect` 仍保持 TASK-002B1 fail closed，不新增回料/验货事实。  
□ 业务代码扫描不出现 `STE-ISS/STE-REC` 伪库存号回潮。  
□ 业务代码扫描不出现旧公式 `net_amount = inspected_qty - deduction_amount` 回潮。  
□ 全量 pytest、unittest、py_compile 通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_alembic_migration_chain_creates_subcontract_base_tables_from_empty_database`
2. `test_alembic_migration_chain_adds_task_002c_company_columns_from_empty_database`
3. `test_task_002c_migration_does_not_depend_on_metadata_create_all`
4. `test_task_002c_migration_is_idempotent_when_tables_already_exist`
5. `test_create_subcontract_rejects_bom_item_mismatch`
6. `test_create_subcontract_bom_item_mismatch_does_not_insert_order`
7. `test_create_subcontract_bom_item_mismatch_does_not_write_success_audit`
8. `test_create_subcontract_with_explicit_company_still_validates_item_and_bom_match`
9. `test_create_subcontract_blank_company_returns_company_required_envelope`
10. `test_create_subcontract_null_company_returns_company_required_envelope`
11. `test_create_subcontract_ambiguous_company_returns_company_ambiguous_envelope`
12. `test_create_subcontract_unresolved_company_returns_company_unresolved_envelope`
13. `test_create_subcontract_erpnext_unavailable_returns_service_unavailable_envelope`
14. `test_company_only_permission_lists_same_company_when_item_supplier_unrestricted`
15. `test_company_only_permission_cannot_list_other_company`
16. `test_item_restriction_is_still_enforced_when_company_allowed`
17. `test_backfill_child_update_write_failed_rolls_back_dirty_session`
18. `test_backfill_flush_write_failed_rolls_back_dirty_session`
19. `test_backfill_write_failed_caller_commit_does_not_persist_partial_changes`
20. `test_task_002c1_does_not_restore_receive_or_inspect_success_path`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q tests/test_subcontract_company_migration.py tests/test_subcontract_company_permission.py tests/test_subcontract_permissions.py tests/test_subcontract_exception_handling.py
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
rg "STE-ISS|STE-REC|net_amount = .*inspected_qty|detail=str\(exc\)|metadata.create_all" app migrations tests
```

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| `Item` | REST API 或共享 PostgreSQL 只读 | 校验 `payload.item_code` 存在、未禁用，并与 BOM item 一致 |
| `Supplier` | REST API 或共享 PostgreSQL 只读 | 参与 company 候选解析；不可用 fail closed |
| `User Permission` | ERPNext 权限聚合 | 区分 Company-only、Item/Supplier/Warehouse 限制、权限源不可用 |
| `Stock Entry` | 不调用 | TASK-002C1 禁止创建 ERPNext Stock Entry |

【前置依赖】
- TASK-002A：外发模块设计契约冻结已封版。
- TASK-002B1：权限、审计、回料/验货 fail closed 已通过。
- TASK-002C：已交付但审计不通过，必须整改。
- ADR-033：外发迁移必须自洽且创建单据必须校验 BOM 款式一致。

【交付物】
1. 修复后的外发迁移链或补齐的基础表迁移。
2. 空库迁移链测试结果。
3. BOM item mismatch 校验实现和测试。
4. company 解析统一错误信封和测试。
5. 回填写失败 rollback 实现和测试。
6. Company-only 权限策略实现和测试。
7. 全量测试结果。

【禁止事项】
1. 禁止进入 TASK-002D 发料 outbox 实现。
2. 禁止进入 TASK-002E 回料 outbox 实现。
3. 禁止进入 TASK-002F 验货金额口径实现。
4. 禁止创建 ERPNext `Stock Entry`。
5. 禁止恢复 `receive/inspect` 成功路径。
6. 禁止用 `metadata.create_all()` 替代迁移链验收。
7. 禁止 BOM item mismatch 时创建外发单。
8. 禁止 company 无法解析时默认写任意公司。
9. 禁止把权限源不可用当成“无资源限制”。
10. 禁止日志、审计、响应中泄露 SQL 原文或敏感凭证。

【预计工时】
1-2 天

════════════════════════════════════════════════════════════════════════════
