# 工程任务单：TASK-003P 工价补数 ERPNext Item 候选查询 Fail Closed 整改

- 任务编号：TASK-003P
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / 数据修复链路 / ERPNext 主数据源异常分类
- 创建时间：2026-04-12 18:30 CST
- 作者：技术架构师
- 审计来源：TASK-003O 审计意见，ERPNext Item 候选查询不可用时仍静默当成“无候选”，execute 会把历史工价停用为 `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED`

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003P
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
修复工价 company 补数链路中的 ERPNext Item 候选查询异常：ERPNext Item 主数据不可用时必须 fail closed，返回 `ERPNEXT_SERVICE_UNAVAILABLE` 或 `DATABASE_READ_FAILED`，不得当成“无候选”并停用历史工价。

【问题背景】
TASK-003O 已修复 scoped 工价候选数据库读取失败 fail closed。审计继续发现：`_resolve_backfill_companies()` 在调用 ERPNext Item 候选查询失败时捕获 `ERPNextServiceUnavailableError` 后返回空集合，后续 execute 会把历史工价按 `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED` 停用。ERPNext Item 是外部主数据事实源；查询不可用不等于业务上确实没有候选 company，必须中断补数流程，避免数据修复误伤 active 工价。

【涉及文件】
修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/exceptions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/logging.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_permissions.py`

【接口 / 函数清单】
| 名称 | 类型 | 当前风险 | 本任务要求 |
| --- | --- | --- | --- |
| `_resolve_backfill_companies` | internal function | `ERPNextServiceUnavailableError` 被吞掉后返回空集合 | ERPNext Item 查询不可用必须向上抛出标准系统异常 |
| `ERPNextJobCardAdapter.get_item` | adapter method | Item 主数据不可用与 404/无记录需明确区分 | 404 可返回 `None`，服务不可用/响应异常必须抛 `ERPNextServiceUnavailableError` |
| `build_wage_rate_company_backfill_plan` | service/function | 空候选会进入 unresolved 业务计划 | 主数据源不可用时必须中断，不生成 blocked/unresolved 计划行 |
| `backfill_wage_rate_company_scope(dry_run=True)` | service/function | 可能返回成功预演报告 | 主数据源不可用时不得返回成功报告，session 保持只读 |
| `backfill_wage_rate_company_scope(dry_run=False)` | service/function | 可能停用历史工价并写补数日志 | 主数据源不可用时 rollback，不改工价、不写补数日志 |

【核心设计决策】
1. ERPNext Item 候选查询不可用是系统级失败，不是业务解析失败。
2. `ERPNextServiceUnavailableError` 不得转换成空候选集合。
3. ERPNext REST 超时、连接失败、HTTP 非成功、响应结构异常、JSON 解析失败，必须返回 `ERPNEXT_SERVICE_UNAVAILABLE` 或等价系统错误。
4. 如果工程实现实际通过共享 PostgreSQL 读取 `public.tabItem`，SQLAlchemy 读取失败必须返回 `DATABASE_READ_FAILED`。
5. ERPNext Item 404 或查询成功但无 company 候选，才允许进入业务上的 `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED`。
6. `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED` 只能表示“主数据源可用且事实完整，但无法解析 company”。
7. 主数据源不可用时不得停用工价、不得标记 `blocked_scope`、不得写补数日志。
8. dry-run 仍必须保持 TASK-003N 的零写入语义。
9. execute 失败必须保持事务一致性：无部分补数、无部分日志、无部分审计。
10. 日志和审计上下文必须脱敏，不得记录 ERPNext token、Cookie、Authorization、响应敏感原文。

【错误分类】
| 场景 | code | 是否生成补数计划 | 是否允许停用工价 | 是否写补数日志 |
| --- | --- | --- | --- | --- |
| ERPNext Item REST 超时/连接失败 | `ERPNEXT_SERVICE_UNAVAILABLE` | 否 | 否 | 否 |
| ERPNext Item HTTP 5xx/非成功响应 | `ERPNEXT_SERVICE_UNAVAILABLE` | 否 | 否 | 否 |
| ERPNext Item 响应结构异常/JSON 解析失败 | `ERPNEXT_SERVICE_UNAVAILABLE` | 否 | 否 | 否 |
| 共享 PostgreSQL `tabItem` 查询 `SQLAlchemyError` | `DATABASE_READ_FAILED` | 否 | 否 | 否 |
| ERPNext Item 404 / 不存在 | `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED` | 是，作为业务阻断项 | 可按既有阻断策略处理 | execute 时按规则写 |
| ERPNext Item 查询成功但无 company 候选 | `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED` | 是，作为业务阻断项 | 可按既有阻断策略处理 | execute 时按规则写 |
| scoped 工价候选查询成功且唯一 | `unique_company` | 是 | 否，执行补齐 company | 是 |
| scoped 工价候选查询成功但多 company | `WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS` | 是，作为业务阻断项 | 可按既有阻断策略处理 | execute 时按规则写 |

【业务规则】
1. `_resolve_backfill_companies()` 中 `except ERPNextServiceUnavailableError: return set()` 必须删除或改为向上抛出系统异常。
2. ERPNext Item 查询不可用时，不得返回空 `set()`、空 list、`None` 或默认 company。
3. ERPNext Item 查询不可用时，不得追加 `WageRateCompanyBackfillPlanRow(reason_code=WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED)`。
4. ERPNext Item 查询不可用时，不得增加 `unresolved_count/blocked_count`，因为没有产生可信业务结论。
5. dry-run 遇到 ERPNext Item 查询不可用时，必须返回标准错误信封或抛标准异常，不得返回 `code=0` 成功报告。
6. dry-run 失败后 `session.new/session.dirty/session.deleted` 必须为空。
7. dry-run 失败后调用方执行 `session.commit()`，不得新增补数日志，不得修改工价。
8. execute 遇到 ERPNext Item 查询不可用时必须 rollback。
9. execute 失败后 `ly_operation_wage_rate.company/status` 不得变化。
10. execute 失败后 `ly_operation_wage_rate_company_backfill_log` 不得新增。
11. 只有当 ERPNext Item 查询成功并明确返回 404、无 Item 或无 company 候选时，才能进入 `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED`。
12. 服务端日志必须使用 `log_safe_error()` 或等价脱敏封装，不得记录 ERPNext URL query 中的 token、响应原文敏感字段、Authorization、Cookie。
13. 现有 TASK-003L/TASK-003M/TASK-003N/TASK-003O 回归测试必须继续通过。

【验收标准】
□ 模拟 `erp_adapter.get_item()` 抛出 `ERPNextServiceUnavailableError` 时，`_resolve_backfill_companies()` 不返回空集合。
□ 上述场景必须向上返回/抛出 `ERPNEXT_SERVICE_UNAVAILABLE` 或等价系统异常。
□ 上述场景不得返回 `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED`。
□ 上述场景不得生成 `planned_action=blocked` 的补数计划行。
□ dry-run 遇到 ERPNext Item 查询不可用时不得返回成功报告。
□ dry-run 遇到 ERPNext Item 查询不可用后 `session.new` 为空。
□ dry-run 遇到 ERPNext Item 查询不可用后 `session.dirty` 为空。
□ dry-run 遇到 ERPNext Item 查询不可用后 `session.deleted` 为空。
□ dry-run 失败后调用 `session.commit()` 不新增补数日志。
□ dry-run 失败后调用 `session.commit()` 不修改工价 company/status。
□ execute 遇到 ERPNext Item 查询不可用时不修改任何历史工价 company/status。
□ execute 遇到 ERPNext Item 查询不可用时不新增 `ly_operation_wage_rate_company_backfill_log`。
□ execute 遇到 ERPNext Item 查询不可用时事务 rollback，无部分补数结果。
□ ERPNext Item 404 或查询成功但无 company 候选时，仍可按业务规则返回 `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED`。
□ scoped 工价候选唯一时仍能正常生成 backfill 计划并执行补齐。
□ scoped 工价候选多 company 时仍返回 `WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS`。
□ 服务端日志不包含 ERPNext token、Authorization、Cookie、Secret、Password、响应敏感原文。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_resolve_backfill_companies_erpnext_item_unavailable_raises_service_unavailable`
2. `test_resolve_backfill_companies_erpnext_item_unavailable_does_not_return_empty_candidates`
3. `test_backfill_plan_erpnext_item_unavailable_does_not_return_unresolved`
4. `test_backfill_plan_erpnext_item_unavailable_does_not_create_blocked_plan_row`
5. `test_backfill_dry_run_erpnext_item_unavailable_does_not_return_success_report`
6. `test_backfill_dry_run_erpnext_item_unavailable_leaves_session_clean`
7. `test_backfill_dry_run_erpnext_item_unavailable_commit_persists_no_logs`
8. `test_backfill_execute_erpnext_item_unavailable_rolls_back_wage_rate_changes`
9. `test_backfill_execute_erpnext_item_unavailable_writes_no_backfill_logs`
10. `test_backfill_erpnext_item_unavailable_logs_sanitized_error`
11. `test_backfill_item_404_still_returns_company_unresolved_when_query_succeeds`
12. `test_backfill_item_success_without_company_still_returns_company_unresolved`
13. `test_backfill_scoped_wage_rate_unique_company_still_backfills`
14. `test_backfill_scoped_wage_rate_multiple_companies_still_ambiguous`
15. `test_backfill_management_endpoint_propagates_erpnext_service_unavailable_if_present`

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
- TASK-003O：scoped 工价候选数据库读取失败 fail closed 已接入

【交付物】
1. ERPNext Item 候选查询不可用 fail closed 实现。
2. dry-run / execute 主数据源不可用无副作用测试。
3. `unavailable` 与 `unresolved` 错误分类回归测试。
4. 日志脱敏测试。
5. 全量测试结果。

【禁止事项】
1. 禁止捕获 `ERPNextServiceUnavailableError` 后返回空候选继续生成计划。
2. 禁止把 ERPNext Item 查询不可用归类为 `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED`。
3. 禁止因 ERPNext Item 查询不可用停用历史工价或标记 `blocked_scope`。
4. 禁止 dry-run 失败后返回成功报告。
5. 禁止 execute 失败后产生部分补数或部分日志。
6. 禁止错误日志记录 ERPNext token、Authorization、Cookie、响应敏感原文。
7. 禁止为了通过测试把 ERPNext Item 404 与服务不可用混为一类；404/无候选是业务 unresolved，服务不可用是系统 fail closed。

════════════════════════════════════════════════════════════════════════════
