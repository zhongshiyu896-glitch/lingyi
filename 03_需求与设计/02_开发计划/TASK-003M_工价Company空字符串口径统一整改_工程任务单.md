# 工程任务单：TASK-003M 工价 Company 空字符串口径统一整改

- 任务编号：TASK-003M
- 模块：工票/车间管理
- 优先级：P1
- 任务类型：审计整改 / 数据规范化 / 工价权限一致性
- 创建时间：2026-04-12 17:31 CST
- 作者：技术架构师
- 审计来源：TASK-003L 审计意见，历史工价 company 缺失口径只覆盖 `NULL`，未覆盖空字符串和空白字符串，导致列表过滤、补数扫描、计薪阻断口径不一致

════════════════════════════════════════════════════════════════════════════
【任务卡】TASK-003M
模块：工票/车间管理
优先级：P1（审计整改，必须先于 TASK-003 总体验收）
════════════════════════════════════════════════════════════════════════════

【任务目标】
将历史工价 company 缺失口径从单纯 `NULL` 扩展为 `NULL / 空字符串 / 空白字符串`，并统一迁移、列表过滤、补数扫描、计薪阻断、写入校验四处判断。

【问题背景】
TASK-003L 已完成 `company=NULL` 历史工价主线整改：不参与计薪、可迁移回填或阻断、列表过滤 active null-company item 工价。审计探针继续发现：`company=''` 的 active item 工价仍会出现在列表中，计薪返回 `WORKSHOP_WAGE_RATE_NOT_FOUND` 而不是 `WORKSHOP_WAGE_RATE_SCOPE_REQUIRED`。说明当前实现只把 SQL `NULL` 当作缺失，未把空字符串、空白字符串统一视为缺失 company。

【涉及文件】
新建或修改：
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/migrations/versions/task_003l_wage_rate_company_backfill.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/models/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/schemas/workshop.py`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service/app/services/workshop_service.py`
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
| 登记工票 | POST | `/api/workshop/tickets/register` | `job_card`, `employee`, `process_name`, `qty`, `work_date` | `ticket_no`, `unit_wage`, `wage_amount` |
| 批量导入工票 | POST | `/api/workshop/tickets/batch` | 工票行数组 | `success_count`, `failed_count`, `failed_items` |

【统一缺失口径】
必须新增或统一使用 `normalize_company(value)` / `is_missing_company(value)` 等等价函数：

```text
is_missing_company(company) = company IS NULL OR trim(company) = ''
normalize_company(company) = NULL if company IS NULL OR trim(company) = '' else trim(company)
```

统一适用范围：
1. 迁移补数扫描。
2. 工价列表过滤。
3. 工票登记计薪匹配。
4. 工价创建 / 更新 / 停用校验。
5. 历史脏数据安全审计判断。
6. 数据库约束或应用级约束。

【数据库规则】
| 字段状态 | 语义 | 允许场景 | 处理方式 |
| --- | --- | --- | --- |
| `company IS NULL` | company 缺失 | 仅历史脏数据扫描输入 | 补数或阻断 |
| `company = ''` | company 缺失 | 禁止新增，历史脏数据 | 先 normalize 为 NULL，再补数或阻断 |
| `company = '   '` | company 缺失 | 禁止新增，历史脏数据 | 先 normalize 为 NULL，再补数或阻断 |
| `company = 'COMPANY-A'` | company 已明确 | 款式专属工价 | 可参与列表和计薪 |

【核心设计决策】
1. `NULL`、`''`、`'   '` 在工价 company 语义上全部等价为“缺失 company”。
2. 所有入参 company 必须先 trim 再校验。
3. 款式专属工价 `item_code IS NOT NULL` 时，normalize 后 company 为空必须返回 `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED`。
4. 历史扫描条件必须从 `company IS NULL` 扩展为 `company IS NULL OR trim(company) = ''`。
5. 工价列表必须过滤掉 active `item_code IS NOT NULL AND is_missing_company(company)` 的记录。
6. 计薪匹配不得命中 active `item_code IS NOT NULL AND is_missing_company(company)` 的记录。
7. 如果计薪发现唯一候选是缺失 company 的历史 item 工价，必须返回 `WORKSHOP_WAGE_RATE_SCOPE_REQUIRED`，不是 `WORKSHOP_WAGE_RATE_NOT_FOUND`。
8. `WORKSHOP_WAGE_RATE_NOT_FOUND` 只用于确实不存在有效工价候选的场景。
9. 补数脚本必须先把空字符串 / 空白字符串 normalize 为 NULL，再执行 TASK-003L 的补数或阻断逻辑。
10. 数据库层建议增加 check constraint：`item_code IS NULL OR company IS NOT NULL AND btrim(company) <> ''`；如历史兼容不能立即加硬约束，必须用应用级强校验 + 迁移后约束实现。

【迁移要求】
1. 扫描范围必须包括：`item_code IS NOT NULL AND (company IS NULL OR btrim(company) = '')`。
2. 空字符串和空白字符串必须先 normalize 为 NULL，写入补数日志。
3. 可唯一解析 company 的记录补齐 company。
4. 无法解析或多 company 冲突的 active 记录停用或标记 `blocked_scope`。
5. 迁移后不得存在 active `item_code IS NOT NULL AND (company IS NULL OR btrim(company) = '')`。
6. 迁移日志必须区分：`normalized_blank_company`、`backfilled`、`ambiguous_company`、`company_unresolved`、`blocked`。
7. 迁移重复执行不得重复 normalize 或重复写大量日志。

【列表过滤要求】
1. `GET /api/workshop/wage-rates` 不得返回 active `item_code IS NOT NULL AND is_missing_company(company)` 记录。
2. 显式传入 `company=''` 或空白字符串时，后端必须 normalize 并返回 `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED` 或按缺失参数处理，不得作为合法 company 查询。
3. 列表权限过滤必须基于 normalize 后 company。

【计薪阻断要求】
1. 工票登记计薪匹配条件必须包含 `company == derived_company`。
2. 计薪前必须额外检测是否存在同 `item_code/process_name/effective_date` 且 `is_missing_company(company)` 的 active 历史工价。
3. 若没有 scoped 工价但存在缺失 company 的历史候选，返回 `WORKSHOP_WAGE_RATE_SCOPE_REQUIRED`。
4. 若既没有 scoped 工价，也没有缺失 company 历史候选，返回 `WORKSHOP_WAGE_RATE_NOT_FOUND`。
5. 缺失 company 历史候选被阻断时必须写安全审计或业务审计，记录 `wage_rate_id/item_code/process_name/work_date/reason_code`。

【错误码要求】
| 场景 | HTTP 状态 | code | 要求 |
| --- | --- | --- | --- |
| 创建 item 工价 company 为 `NULL/''/'   '` | 422 | `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED` | trim 后校验，不落库 |
| 计薪仅命中缺失 company 的历史 item 工价 | 409 | `WORKSHOP_WAGE_RATE_SCOPE_REQUIRED` | 不创建工票，写审计 |
| 查询传入空白 company | 422 | `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED` | 不执行脏查询 |
| 迁移发现多 company | 409 或迁移日志 | `WORKSHOP_WAGE_RATE_COMPANY_AMBIGUOUS` | 不自动补数 |
| 迁移无法解析 company | 409 或迁移日志 | `WORKSHOP_WAGE_RATE_COMPANY_UNRESOLVED` | 不自动补数 |

【验收标准】
□ `company=NULL`、`company=''`、`company='   '` 全部被 `is_missing_company()` 判定为缺失。
□ `POST /api/workshop/wage-rates` 创建 item 工价时，company 为 `NULL/''/'   '` 均返回 `WORKSHOP_WAGE_RATE_COMPANY_REQUIRED`。
□ `GET /api/workshop/wage-rates` 不返回 active `item_code IS NOT NULL AND company=''` 的历史工价。
□ `GET /api/workshop/wage-rates` 不返回 active `item_code IS NOT NULL AND company='   '` 的历史工价。
□ 补数扫描包含 `company IS NULL OR btrim(company)=''`。
□ 空字符串 / 空白字符串 company 会先 normalize 为 NULL，再进入补数或阻断流程。
□ 迁移后 active `item_code IS NOT NULL AND (company IS NULL OR btrim(company)='')` 数量为 0。
□ 工票登记不会命中 `company=''` 或 `company='   '` 的历史 item 工价。
□ 当唯一候选是 `company=''` 或空白字符串历史 item 工价时，计薪返回 `WORKSHOP_WAGE_RATE_SCOPE_REQUIRED`。
□ 真正不存在任何工价候选时，计薪仍返回 `WORKSHOP_WAGE_RATE_NOT_FOUND`。
□ 缺失 company 历史工价阻断写入审计，且审计不包含敏感明文。
□ TASK-003L 的 `company=NULL` 回归测试继续通过。
□ 全量测试继续通过。

【测试要求】
必须新增或补齐以下测试：
1. `test_is_missing_company_treats_none_empty_and_whitespace_as_missing`
2. `test_wage_rate_create_rejects_empty_company_for_item_rate`
3. `test_wage_rate_create_rejects_whitespace_company_for_item_rate`
4. `test_wage_rate_list_filters_empty_company_item_rate`
5. `test_wage_rate_list_filters_whitespace_company_item_rate`
6. `test_backfill_scans_null_empty_and_whitespace_company`
7. `test_backfill_normalizes_blank_company_before_resolution`
8. `test_no_active_item_rate_with_null_empty_or_whitespace_company_after_migration`
9. `test_ticket_register_does_not_match_empty_company_item_rate`
10. `test_ticket_register_empty_company_legacy_candidate_returns_scope_required`
11. `test_ticket_register_missing_all_candidates_returns_wage_rate_not_found`
12. `test_legacy_empty_company_rate_denial_writes_audit`

【回归命令】
在 `/Users/hh/Desktop/领意服装管理系统/07_后端/lingyi_service` 下执行：

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m unittest discover
.venv/bin/python -m py_compile $(find app tests -name '*.py' -print)
```

【前置依赖】
- TASK-003B：工价资源权限闭环已接入
- TASK-003L：历史 `company=NULL` 工价补数与计薪一致性整改已接入

【交付物】
1. company 缺失规范化函数或等价统一实现。
2. 迁移补数扫描口径扩展到 `NULL/空字符串/空白字符串`。
3. 工价列表过滤修复。
4. 工票登记计薪阻断修复。
5. 新增测试与全量测试结果。

【禁止事项】
1. 禁止只判断 `company IS NULL`，不处理 `''` 和空白字符串。
2. 禁止 active `item_code IS NOT NULL AND btrim(company)=''` 工价出现在列表中。
3. 禁止计薪命中空字符串或空白字符串 company 的历史 item 工价。
4. 禁止把缺失 company 的历史候选误报为普通 `WORKSHOP_WAGE_RATE_NOT_FOUND`。
5. 禁止新建或更新款式专属工价时写入空字符串 / 空白字符串 company。
6. 禁止迁移重复执行时重复放大补数日志。

════════════════════════════════════════════════════════════════════════════
