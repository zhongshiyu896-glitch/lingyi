# 工程任务单：TASK-003O 工价补数读取失败 Fail Closed 整改

- 任务编号：TASK-003O
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / 数据修复链路 / 数据库异常分类
- 创建时间：2026-04-12 18:17 CST
- 作者：技术架构师
- 审计来源：TASK-003N 审计意见，`_resolve_backfill_companies()` 读取同款式 scoped 工价候选时吞掉 `SQLAlchemyError` 并继续生成补数计划

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003O
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复 `_resolve_backfill_companies()` 的数据库读取失败处理：任何 `SQLAlchemyError` 必须 fail closed，返回 `DATABASE_READ_FAILED`，不得静默降级为 `ambiguous/unresolved` 或继续生成不完整补数计划。

【问题背景】
TASK-003N 已把工价 company 补数 dry-run 改为真正只读，避免 dry-run 挂 ORM 对象和 commit 后副作用。审计继续发现：`_resolve_backfill_companies()` 在读取同款式 scoped 工价候选时吞掉 `SQLAlchemyError`，然后继续生成补数计划。补数属于数据修复链路，数据库读取失败意味着基础事实不完整，不能继续推断 company，也不能把系统故障误判为业务上的“无法解析”或“多义”。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_003l_wage_rate_company_backfill.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/logging.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_permissions.py`

【接口 / 函数清单】
| 名称 | 类型 | 入参 | 出参 | 本任务要求 |
| --- | --- | --- | --- | --- |
| `_resolve_backfill_companies` | internal function | `session`, `item_code` 等 | company resolution result | DB 读取失败必须抛出/返回 `DATABASE_READ_FAILED` |
| `build_wage_rate_company_backfill_plan` | service/function | `session`, `limit` | plan/report | 任一解析读取失败必须中断，不返回成功计划 |
| `backfill_wage_rate_company_scope` | service/function | `session`, `dry_run`, `limit` | `BackfillReport` 或错误 | dry-run/execute 均 fail closed |
| 工价 company 补数迁移 | migration/command | dry-run / execute 模式 | 补数报告或错误 | DB 读取失败不得生成部分计划 |

【核心设计决策】
1. 数据库读取失败是系统级失败，不是业务解析失败。
2. `_resolve_backfill_companies()` 禁止吞掉 `SQLAlchemyError` 后继续返回空候选、`ambiguous_company` 或 `company_unresolved`。
3. 读取同款式 scoped 工价候选失败时，必须抛出 `DatabaseReadFailed` 或等价异常。
4. `build_wage_rate_company_backfill_plan()` 遇到任何 `DatabaseReadFailed` 必须立即中断。
5. `backfill_wage_rate_company_scope(dry_run=True)` 遇到数据库读取失败必须返回/抛出 `DATABASE_READ_FAILED`，不得返回 `code=0` 的 dry-run 报告。
6. `backfill_wage_rate_company_scope(dry_run=False)` 遇到数据库读取失败必须 rollback，且不得更新工价、不得写补数日志。
7. 业务上的 `ambiguous_company/company_unresolved` 只允许在数据库读取成功、事实完整但业务无法唯一判断时产生。
8. 错误日志必须脱敏，不得记录 SQL 原文、参数、连接串、账号密码或 token。
9. dry-run 失败路径仍必须保持 TASK-003N 的只读要求：`session.new/session.dirty/session.deleted` 为空。
10. execute 失败路径必须保持事务一致性：无部分补数、无部分日志、无部分审计。

【错误分类】
| 场景 | HTTP/命令结果 | code | 是否继续生成计划 | 是否写补数日志 |
| --- | --- | --- | --- | --- |
| scoped 工价候选查询 `SQLAlchemyError` | 500 | `DATABASE_READ_FAILED` | 否 | 否 |
| Item / Work Order / Job Card 历史引用查询 `SQLAlchemyError` | 500 | `DATABASE_READ_FAILED` | 否 | 否 |
| 查询成功但同 item 多 company | 409 或 plan reason | `WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS` | 是，作为业务阻断项 | execute 时按规则写 |
| 查询成功但无法解析 company | 409 或 plan reason | `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED` | 是，作为业务阻断项 | execute 时按规则写 |
| dry-run 读取失败 | 500 | `DATABASE_READ_FAILED` | 否 | 否 |
| execute 读取失败 | 500 | `DATABASE_READ_FAILED` | 否 | 否，rollback |

【业务规则】
1. `_resolve_backfill_companies()` 所有数据库读取必须在统一异常边界内处理。
2. 捕获 `SQLAlchemyError` 后只能转换为 `DATABASE_READ_FAILED`，不得返回空列表或默认值。
3. `DATABASE_READ_FAILED` 响应中的 `message/detail` 不得包含 SQL 原文和参数。
4. 读取失败时不得把记录标记为 `blocked/ambiguous/unresolved`。
5. 读取失败时不得增加 `blocked_count/ambiguous_count/unresolved_count`，因为没有产生可信业务结论。
6. 读取失败时 dry-run 报告不得返回 `total_scanned/backfilled_count/...` 的成功结构；如需要返回错误上下文，只能返回安全字段：`stage`, `error_code`, `request_id`。
7. execute 模式读取失败时必须 rollback 当前事务。
8. execute 模式读取失败时不得写 `ly_operation_wage_rate_company_backfill_log`。
9. execute 模式读取失败时不得修改 `ly_operation_wage_rate.company/status`。
10. 读取失败必须记录脱敏后的服务端错误日志，便于排障。
11. 如果补数管理入口存在，必须把 `DATABASE_READ_FAILED` 透传为标准错误信封，不得包装成普通业务报告。
12. TASK-003N 的 dry-run 只读测试必须继续通过。

【验收标准】
□ 模拟 `_resolve_backfill_companies()` 查询 scoped 工价候选抛出 `SQLAlchemyError` 时，返回/抛出 `DATABASE_READ_FAILED`。
□ 上述场景不得返回 `WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS`。
□ 上述场景不得返回 `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED`。
□ 上述场景不得返回成功 dry-run 报告。
□ dry-run 读取失败后 `session.new` 为空。
□ dry-run 读取失败后 `session.dirty` 为空。
□ dry-run 读取失败后 `session.deleted` 为空。
□ dry-run 读取失败后调用 `session.commit()` 不新增补数日志。
□ execute 读取失败后不修改任何 `ly_operation_wage_rate.company/status`。
□ execute 读取失败后不新增 `ly_operation_wage_rate_company_backfill_log`。
□ execute 读取失败后事务 rollback，无部分补数结果。
□ 服务端日志不包含 SQL 原文、SQL 参数、连接串、密码、token、Authorization、Cookie。
□ 查询成功但业务多义时，仍按 `WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS` 处理。
□ 查询成功但业务无法解析时，仍按 `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED` 处理。
□ TASK-003L/TASK-003M/TASK-003N 全部回归测试继续通过。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_resolve_backfill_companies_sqlalchemy_error_returns_database_read_failed`
2. `test_resolve_backfill_companies_sqlalchemy_error_does_not_return_ambiguous`
3. `test_resolve_backfill_companies_sqlalchemy_error_does_not_return_unresolved`
4. `test_backfill_plan_database_read_failed_does_not_return_success_report`
5. `test_backfill_dry_run_database_read_failed_leaves_session_clean`
6. `test_backfill_dry_run_database_read_failed_commit_persists_no_logs`
7. `test_backfill_execute_database_read_failed_rolls_back_wage_rate_changes`
8. `test_backfill_execute_database_read_failed_writes_no_backfill_logs`
9. `test_backfill_database_read_failed_logs_sanitized_error`
10. `test_backfill_business_ambiguous_still_returns_ambiguous_when_queries_succeed`
11. `test_backfill_business_unresolved_still_returns_unresolved_when_queries_succeed`
12. `test_backfill_management_endpoint_propagates_database_read_failed_if_present`

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
- TASK-003N：工价补数 dry-run 只读语义已接入

【交付物】
1. `_resolve_backfill_companies()` 数据库读取失败 fail closed 实现。
2. dry-run / execute 读取失败无副作用测试。
3. 业务多义和系统读取失败的错误分类回归测试。
4. 脱敏日志测试。
5. 全量测试结果。

【禁止事项】
1. 禁止捕获 `SQLAlchemyError` 后返回空候选继续生成计划。
2. 禁止把数据库读取失败归类为 `ambiguous_company` 或 `company_unresolved`。
3. 禁止 dry-run 读取失败后返回成功报告。
4. 禁止 execute 读取失败后产生部分补数或部分日志。
5. 禁止错误日志记录 SQL 原文、参数、连接串或敏感凭证。
6. 禁止为了通过测试而吞掉异常不返回标准错误码。

════════════════════════════════════════════════════════════════════════════
