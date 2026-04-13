# 工程任务单：TASK-003L 历史工价 Company 补数与计薪一致性整改

- 任务编号：TASK-003L
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / 历史数据迁移 / 工价权限一致性
- 创建时间：2026-04-12 17:07 CST
- 作者：技术架构师
- 审计来源：TASK-003K 审计意见，历史 item 工价 `company=NULL` 的迁移/补数策略未闭环，存在“页面权限过滤看不到，但登记计薪仍可命中历史工价”的一致性风险

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003L
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
补齐历史 `ly_operation_wage_rate.company IS NULL` 的补数、拦截和计薪一致性策略，确保工价列表权限过滤、工票登记计薪匹配、工价维护接口使用同一套 `item_code/company` 资源口径。

【问题背景】
TASK-003B 已要求工价按 `item_code/company` 做资源级权限闭环，但历史数据中可能存在 `item_code IS NOT NULL AND company IS NULL` 的工价记录。页面列表按 company 过滤时看不到这些历史工价，但工票登记计薪如果只按 `item_code + process_name + effective_date` 匹配，就可能命中这些 `company=NULL` 工价，造成“用户页面不可见、计薪仍使用”的权限和业务口径不一致。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_003l_wage_rate_company_backfill.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/permission_service.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/routers/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/core/error_codes.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/audit_service.py`

测试文件：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_wage_permissions.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_ticket.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/tests/test_workshop_permissions.py`

【接口清单】
| 接口名称 | HTTP 方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 查询工价档案 | GET | `/api/workshop/wage-rates` | `item_code`, `company`, `process_name`, `status` | 分页工价列表 |
| 创建工价档案 | POST | `/api/workshop/wage-rates` | `item_code`, `company`, `process_name`, `wage_rate`, `effective_from`, `effective_to` | `id`, `item_code`, `company` |
| 停用工价档案 | POST | `/api/workshop/wage-rates/{id}/deactivate` | `id` | `id`, `status` |
| 登记工票 | POST | `/api/workshop/tickets/register` | `job_card`, `employee`, `process_name`, `qty`, `work_date` | `ticket_no`, `unit_wage`, `wage_amount` |
| 批量导入工票 | POST | `/api/workshop/tickets/batch` | 工票行数组 | `success_count`, `failed_count`, `failed_items` |

【数据库表设计】
| 表名 | 用途 | 关键字段 | 本任务要求 |
| --- | --- | --- | --- |
| `ly_schema.ly_operation_wage_rate` | 工价档案 | `id`, `item_code`, `company`, `process_name`, `wage_rate`, `effective_from`, `effective_to`, `status` | `item_code IS NOT NULL` 时 `company` 必须非空；计薪匹配必须带 company |
| `ly_schema.ly_operation_wage_rate_company_backfill_log` | 工价 company 补数日志 | `wage_rate_id`, `item_code`, `old_company`, `new_company`, `result`, `reason`, `created_at` | 记录补数、跳过、冲突、失败原因 |
| `ly_schema.ys_workshop_ticket` | 工票事实表 | `ticket_no`, `job_card`, `item_code`, `company`, `unit_wage`, `wage_amount` | 工票单价快照必须来自同 company 的工价 |
| `ly_schema.ly_security_audit_log` | 安全审计 | `event_type`, `resource_type`, `resource_id`, `reason_code` | 计薪命中历史脏工价、补数冲突必须留痕 |

【核心设计决策】
1. `ly_operation_wage_rate.item_code IS NOT NULL` 的工价必须绑定明确 `company`。
2. `company=NULL` 只允许用于真正的全局通用工价，且必须满足 `item_code IS NULL` 与全局工价权限要求。
3. `item_code IS NOT NULL AND company IS NULL` 定义为历史脏数据，不得继续被工票登记计薪匹配。
4. 工票登记、撤销重算、批量导入计薪匹配工价时，必须使用 ERPNext Job Card / Work Order 派生的 `company` 作为匹配条件。
5. 工价列表、工价维护、工票计薪必须使用同一套 `item_code/company` scope 口径。
6. 历史数据补数必须先 dry-run 生成报告，再执行正式补数。
7. 可以唯一解析 company 的历史 item 工价允许自动补数。
8. 无法唯一解析 company 的历史 item 工价必须标记为 `blocked_scope` 或 `inactive`，不得保持 active 且可被计薪命中。
9. 补数和阻断必须写迁移日志，方便审计复核。
10. 新增工价写接口必须禁止创建 `item_code IS NOT NULL AND company IS NULL`。

【Company 解析规则】
按以下优先级为历史工价补 company：
1. 若历史工价已有 `company`，不改动，只校验 company 有效性。
2. 若 `item_code` 对应 ERPNext Item 有唯一 `custom_ly_company` 或等价公司字段，使用该 company。
3. 若可从关联 BOM / Work Order / Job Card 历史引用中唯一推出 company，使用该 company。
4. 若同一 `item_code` 可对应多个 company，判定为 `ambiguous_company`，不得自动补数。
5. 若无法从 ERPNext 或历史引用解析 company，判定为 `company_unresolved`，不得自动补数。
6. `ambiguous_company/company_unresolved` 的 active 工价必须停用或标记 `blocked_scope`，并写补数日志与安全审计。

【计薪匹配规则】
1. 工票登记前必须从 ERPNext `Job Card -> Work Order` 派生真实 `item_code/company`。
2. 工价匹配必须包含 `company == derived_company`。
3. 款式专属工价匹配条件：`item_code == derived_item_code AND company == derived_company AND process_name == process_name AND effective_from <= work_date AND effective_to >= work_date AND status='active'`。
4. 通用工价匹配条件：`item_code IS NULL AND company == derived_company AND process_name == process_name AND status='active'`；如业务确需跨公司全局工价，必须单独配置 `workshop:wage_rate_read_all/manage_all` 且不得默认启用。
5. `item_code IS NOT NULL AND company IS NULL` 的工价不得被计薪匹配。
6. 如果只存在历史 `company=NULL` 款式工价，登记工票必须返回 `WORKSHOP_WAGE_RATE_SCOPE_REQUIRED` 或 `WORKSHOP_WAGE_RATE_NOT_FOUND`，不得静默使用该工价。
7. 返回错误时必须写安全审计或业务审计，记录 `item_code/company/process_name/work_date/reason_code`。

【迁移要求】
1. 新增 Alembic 迁移 `task_003l_wage_rate_company_backfill.py`。
2. 迁移必须支持 dry-run 报告模式和正式执行模式；如果现有迁移框架不支持运行时参数，需提供独立 service/command 并在迁移中只加结构约束。
3. 新增补数日志表 `ly_operation_wage_rate_company_backfill_log` 或等价审计记录。
4. 对可唯一解析 company 的历史工价执行补数。
5. 对无法解析或多公司冲突的 active 历史工价执行 fail closed：停用或标记 `blocked_scope`。
6. 迁移后新增数据库约束或应用级强校验：禁止 active `item_code IS NOT NULL AND company IS NULL`。
7. 迁移必须可重复执行，重复执行不得重复补数或重复写大量日志。
8. 迁移报告必须输出：`total_scanned`、`backfilled_count`、`blocked_count`、`ambiguous_count`、`unresolved_count`、`unchanged_count`。

【错误码要求】
| 场景 | HTTP 状态 | code | 要求 |
| --- | --- | --- | --- |
| 创建 item 工价但 company 为空 | 422 | `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED` | 不落库 |
| 计薪仅命中历史 company=NULL item 工价 | 409 | `WORKSHOP_WAGE_RATE_SCOPE_REQUIRED` | 不创建工票，写审计 |
| item_code -> company 多义 | 409 | `WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS` | 不自动补数，不计薪 |
| item_code -> company 无法解析 | 409 | `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED` | 不自动补数，不计薪 |
| 权限来源不可用 | 503 | `PERMISSION_SOURCE_UNAVAILABLE` | fail closed |

【验收标准】
□ `ly_operation_wage_rate` 中 `item_code IS NOT NULL AND company IS NULL AND status='active'` 的记录迁移后数量为 0。
□ 可唯一解析 company 的历史 item 工价被补齐 company。
□ 多 company 或无法解析 company 的历史 item 工价被停用或标记 `blocked_scope`，不得保持 active 可用。
□ 补数、跳过、冲突、失败均写入 `ly_operation_wage_rate_company_backfill_log` 或等价审计记录。
□ `POST /api/workshop/wage-rates` 创建 item 工价时 company 为空返回 `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED`。
□ 工票登记计薪不会命中 `item_code IS NOT NULL AND company IS NULL` 的历史工价。
□ 当唯一可用工价是历史 `company=NULL` item 工价时，工票登记返回 `WORKSHOP_WAGE_RATE_SCOPE_REQUIRED` 或 `WORKSHOP_WAGE_RATE_NOT_FOUND`。
□ 工票登记使用 `Job Card -> Work Order` 派生 company 匹配同 company 工价。
□ 工价列表可见的工价集合与登记计薪可命中的工价集合在 `item_code/company` 口径上一致。
□ 仅授权 `COMPANY-A + ITEM-A` 的用户不能通过登记 `COMPANY-B + ITEM-A` 的 Job Card 命中 `COMPANY-A` 工价。
□ 通用工价 `item_code IS NULL` 的 company 规则明确，不能被历史 item 工价混用。
□ 迁移脚本重复执行不会重复补数或重复放大日志。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_wage_rate_create_requires_company_for_item_specific_rate`
2. `test_ticket_register_does_not_match_item_rate_with_null_company`
3. `test_ticket_register_matches_wage_rate_with_derived_company`
4. `test_ticket_register_fails_when_only_legacy_null_company_rate_exists`
5. `test_wage_rate_list_and_ticket_matching_use_same_company_scope`
6. `test_backfill_sets_company_for_uniquely_resolved_item_rate`
7. `test_backfill_blocks_ambiguous_company_item_rate`
8. `test_backfill_blocks_unresolved_company_item_rate`
9. `test_backfill_is_idempotent`
10. `test_company_b_job_card_cannot_use_company_a_item_wage_rate`
11. `test_legacy_null_company_rate_denial_writes_audit`
12. `test_no_active_item_specific_wage_rate_with_null_company_after_migration`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【前置依赖】
- TASK-003B：工价资源权限闭环已接入
- TASK-003G：服务账号最小权限策略已接入
- TASK-003K：dry-run 禁用判断前置已接入

【交付物】
1. 历史 item 工价 company 补数迁移或补数脚本。
2. 历史工价补数/阻断日志。
3. 工价创建接口 company 强校验。
4. 工票登记计薪 company 匹配修复。
5. 页面列表和计薪匹配一致性测试。
6. 全量测试结果。

【禁止事项】
1. 禁止 `item_code IS NOT NULL AND company IS NULL` 的 active 工价继续参与计薪。
2. 禁止页面列表按 company 过滤、计薪匹配却忽略 company。
3. 禁止无法解析 company 的历史工价自动猜测补数。
4. 禁止多 company item 工价自动选择任意 company。
5. 禁止用前端传入 company 作为计薪权限依据，必须使用 ERPNext Job Card / Work Order 派生 company。
6. 禁止迁移重复执行时重复写大量日志。

════════════════════════════════════════════════════════════════════════════
