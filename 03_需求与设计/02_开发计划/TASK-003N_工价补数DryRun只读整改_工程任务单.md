# 工程任务单：TASK-003N 工价补数 Dry-Run 只读整改

- 任务编号：TASK-003N
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / Dry-Run 只读语义 / 迁移工具安全
- 创建时间：2026-04-12 17:59 CST
- 作者：技术架构师
- 审计来源：TASK-003M 审计意见，`backfill_wage_rate_company_scope(dry_run=True)` 仍会把补数日志对象挂入当前 session，调用方后续 commit 会产生持久化日志

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003N
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将 `backfill_wage_rate_company_scope(dry_run=True)` 改为真正只读预演：不得向 SQLAlchemy session 挂载任何 ORM 新增、修改、删除对象，调用方后续 `commit()` 也不得持久化补数日志或工价变更。

【问题背景】
TASK-003L/TASK-003M 已补齐历史工价 company 缺失口径和迁移策略。但审计发现：`backfill_wage_rate_company_scope(dry_run=True)` 虽然名义上是 dry-run，仍会构造补数日志 ORM 对象并挂入当前 session。如果调用方在 dry-run 后执行 `session.commit()`，这些日志会被持久化，导致 dry-run 产生数据库副作用。补数工具、管理入口或审计预演都可能误用该函数，因此必须保证 dry-run 路径“零写入、零挂载、可安全 commit”。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_003l_wage_rate_company_backfill.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_ticket.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_permissions.py`

【接口 / 函数清单】
| 名称 | 类型 | 入参 | 出参 | 本任务要求 |
| --- | --- | --- | --- | --- |
| `backfill_wage_rate_company_scope` | service/function | `session`, `dry_run`, `limit` 等 | `BackfillReport` | `dry_run=True` 时纯只读，不挂 ORM 对象 |
| 工价 company 补数迁移 | migration/command | dry-run / execute 模式 | 补数报告 | dry-run 不写补数日志表 |
| 工价补数管理入口 | admin/internal endpoint，如存在 | `dry_run` | 补数报告 | dry-run 不得通过补数日志表落库 |

【核心设计决策】
1. `dry_run=True` 的语义是“只读预演”，不是“写日志但不改主表”。
2. `dry_run=True` 路径不得调用 `session.add()`、`session.add_all()`、`session.merge()`、`session.delete()`、`session.flush()`、`session.commit()`。
3. `dry_run=True` 路径不得修改已加载 ORM 实例字段，包括不得临时设置 `company/status/last_error_code` 后依赖 rollback。
4. `dry_run=True` 路径不得创建并挂载 `ly_operation_wage_rate_company_backfill_log` ORM 对象。
5. `dry_run=True` 返回值必须使用普通 dict、dataclass、Pydantic schema 或不可持久化 DTO，禁止返回已挂 session 的 ORM 对象作为报告行。
6. `dry_run=True` 执行结束后，`session.new`、`session.dirty`、`session.deleted` 必须为空。
7. `dry_run=True` 后调用方即使执行 `session.commit()`，也不得新增补数日志、不得修改工价、不得新增审计。
8. `dry_run=False` 正式执行路径仍必须写补数日志、更新工价 company/status，并保持 TASK-003L/TASK-003M 的补数和阻断规则。
9. 如果未来管理入口需要记录“有人执行过 dry-run”，必须使用独立操作审计设计，且不得复用补数日志表持久化预演行；本任务范围内服务函数必须保持纯只读。
10. 若确实需要在 dry-run 中复用正式执行计算逻辑，必须拆分为“计划生成 plan”和“计划应用 apply”两阶段：dry-run 只调用 plan，execute 才调用 apply。

【推荐实现结构】
1. 新增或重构为 `build_wage_rate_company_backfill_plan(session, limit)`：只读查询，返回 plain plan rows。
2. 新增或保留 `apply_wage_rate_company_backfill_plan(session, plan)`：只在 `dry_run=False` 调用，负责更新工价和写补数日志。
3. `backfill_wage_rate_company_scope(dry_run=True)` 只调用 plan，不调用 apply。
4. `backfill_wage_rate_company_scope(dry_run=False)` 调用 plan + apply。
5. plan row 字段建议包括：`wage_rate_id`, `item_code`, `old_company`, `normalized_company`, `planned_company`, `planned_action`, `reason_code`。
6. report 汇总字段保持 TASK-003L：`total_scanned`, `backfilled_count`, `blocked_count`, `ambiguous_count`, `unresolved_count`, `unchanged_count`。

【数据库副作用边界】
| 模式 | 可读 DB | 可写工价表 | 可写补数日志表 | 可写审计表 | session 可有 new/dirty/deleted |
| --- | --- | --- | --- | --- | --- |
| `dry_run=True` | 是 | 否 | 否 | 否 | 否 |
| `dry_run=False` | 是 | 是 | 是 | 按既有规则 | 是，提交前允许 |

【业务规则】
1. dry-run 报告必须与正式执行使用同一套 company 缺失判断：`company IS NULL OR btrim(company) = ''`。
2. dry-run 报告必须能展示哪些记录将被 `backfilled/blocked/unchanged/ambiguous/unresolved`。
3. dry-run 不得为了生成报告写入 `ly_operation_wage_rate_company_backfill_log`。
4. dry-run 不得为了生成报告写入 `ly_security_audit_log` 或 `ly_audit_log`。
5. dry-run 不得依赖调用方 rollback 才能保持只读；即使调用方 commit 也必须无副作用。
6. dry-run 遇到权限源不可用或 ERPNext 查询失败时，按既有错误分类返回，不得留下部分日志对象。
7. dry-run 过程中发生异常后，session 不得残留 new/dirty/deleted ORM 对象。
8. 正式执行失败时仍按既有事务规则 rollback，避免部分补数落库。
9. 正式执行成功后，补数日志必须准确记录实际执行结果，而不是 dry-run 计划缓存。
10. dry-run 和 execute 的统计口径必须一致，避免预演报告与正式执行结果口径分裂。

【错误码要求】
| 场景 | HTTP 状态 | code | 要求 |
| --- | --- | --- | --- |
| dry-run 权限源不可用 | 503 | `PERMISSION_SOURCE_UNAVAILABLE` | 不挂 ORM 对象 |
| dry-run ERPNext 读取失败 | 503 | `ERPNEXT_SERVICE_UNAVAILABLE` | 不挂 ORM 对象 |
| dry-run 内部异常 | 500 | `WORKSHOP_INTERNAL_ERROR` | 不挂 ORM 对象 |
| execute 数据库写失败 | 500 | `DATABASE_WRITE_FAILED` | rollback |
| execute 补数日志写失败 | 500 | `DATABASE_WRITE_FAILED` 或专用错误 | rollback |

【验收标准】
□ 调用 `backfill_wage_rate_company_scope(dry_run=True)` 后，`session.new` 为空。
□ 调用 `backfill_wage_rate_company_scope(dry_run=True)` 后，`session.dirty` 为空。
□ 调用 `backfill_wage_rate_company_scope(dry_run=True)` 后，`session.deleted` 为空。
□ 调用 dry-run 后再执行 `session.commit()`，`ly_operation_wage_rate_company_backfill_log` 新增 0 条。
□ 调用 dry-run 后再执行 `session.commit()`，`ly_operation_wage_rate` 的 `company/status` 无变化。
□ 调用 dry-run 后再执行 `session.commit()`，`ly_security_audit_log` 和 `ly_audit_log` 不新增 dry-run 产生的记录。
□ dry-run 返回报告仍包含 `total_scanned/backfilled_count/blocked_count/ambiguous_count/unresolved_count/unchanged_count`。
□ dry-run 报告行不是 SQLAlchemy ORM 持久化对象。
□ dry-run 异常路径结束后 session 不残留 new/dirty/deleted 对象。
□ `dry_run=False` 正式执行仍会写补数日志并更新工价 company/status。
□ `dry_run=False` 正式执行统计与 dry-run 计划口径一致。
□ TASK-003L/TASK-003M 的 company 缺失、补数、列表过滤、计薪阻断测试继续通过。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_wage_rate_company_backfill_dry_run_leaves_session_new_empty`
2. `test_wage_rate_company_backfill_dry_run_leaves_session_dirty_empty`
3. `test_wage_rate_company_backfill_dry_run_commit_persists_no_backfill_logs`
4. `test_wage_rate_company_backfill_dry_run_commit_changes_no_wage_rates`
5. `test_wage_rate_company_backfill_dry_run_writes_no_audit_logs`
6. `test_wage_rate_company_backfill_dry_run_report_uses_plain_rows_not_orm`
7. `test_wage_rate_company_backfill_dry_run_exception_leaves_session_clean`
8. `test_wage_rate_company_backfill_execute_still_writes_logs_and_updates_rates`
9. `test_wage_rate_company_backfill_plan_and_execute_counts_match`
10. `test_wage_rate_company_backfill_dry_run_handles_blank_company_without_session_side_effects`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【前置依赖】
- TASK-003L：历史工价 Company 补数与计薪一致性整改已接入
- TASK-003M：`NULL/空字符串/空白字符串` company 缺失口径已统一

【交付物】
1. dry-run 只读实现。
2. plan/apply 两阶段拆分或等价实现。
3. dry-run 后 commit 无副作用测试。
4. execute 正式补数仍可写入测试。
5. 全量测试结果。

【禁止事项】
1. 禁止 dry-run 路径向 session 添加补数日志 ORM 对象。
2. 禁止 dry-run 路径修改工价 ORM 实例字段。
3. 禁止 dry-run 依赖调用方 rollback 保证只读。
4. 禁止 dry-run 后 commit 产生任何补数日志或工价变更。
5. 禁止 dry-run 返回已挂 session 的 ORM 对象作为报告行。
6. 禁止为了修复 dry-run 而削弱正式执行补数日志。

════════════════════════════════════════════════════════════════════════════
