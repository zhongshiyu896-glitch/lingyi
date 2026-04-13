# 当前 sprint 任务清单

- Sprint：Sprint 1 - P0 核心业务闭环
- 版本：V2.0
- 更新时间：2026-04-11 21:01 CST
- 作者：技术架构师
- 项目根目录：`/Users/hh/Desktop/领意服装管理系统/`
- 工作原则：只输出任务卡和设计要求，不写代码。

════════════════════════════════════════════════════════════════════════════

【任务卡】第 1 张 / 共 6 张
模块：BOM 管理（TASK-001）
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
实现款式物料清单管理，支持尺码配比展开、含损耗的物料需求计算、工序定义（分本厂和外发）。

【模块概述】
款式 BOM 是整个服装 ERP 的地基。一个款式对应一个默认生效 BOM，BOM 包含面料、辅料、用量、损耗率、加工工序、外发标识和工价。BOM 展开后输出物料采购需求，也是生产计划、外发加工、工票派工和款式利润计算的数据来源。该模块只维护服装 BOM 业务数据，款式资料本身继续使用 ERPNext `Item`。

【涉及文件】
新建：
- /07_后端/lingyi_service/app/models/bom.py
- /07_后端/lingyi_service/app/schemas/bom.py
- /07_后端/lingyi_service/app/routers/bom.py
- /07_后端/lingyi_service/app/services/bom_service.py
- /06_前端/lingyi-pc/src/views/bom/*.vue
- /06_前端/lingyi-pc/src/api/bom.ts
修改：
- /07_后端/lingyi_service/app/main.py（注册路由）
- /06_前端/lingyi-pc/src/router/index.ts（添加路由）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引 |
| --- | --- | --- | --- |
| ly_schema.ly_apparel_bom | BOM 主表 | id, bom_no, item_code, is_default, status, effective_date | uk_bom_no, idx_item_default, idx_status, uk_one_active_default |
| ly_schema.ly_apparel_bom_item | BOM 物料明细 | id, bom_id, material_item_code, color, size, qty_per_piece, loss_rate | idx_bom_id, idx_material_item |
| ly_schema.ly_bom_operation | BOM 工序明细 | id, bom_id, process_name, is_subcontract, wage_rate, subcontract_cost_per_piece | idx_bom_process, idx_subcontract_flag |
| public.tabItem | ERPNext 款式/物料 | name, item_code, item_name, stock_uom, item_group | ERPNext 标准索引 |

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 创建 BOM | POST | /api/bom/ | item_code, bom_items, operations | code, message, data.name |
| 查询 BOM 列表 | GET | /api/bom/ | item_code, status, page, page_size | items, total, page, page_size |
| 获取 BOM 详情 | GET | /api/bom/{bom_id} | bom_id | bom, items, operations |
| 设置默认 BOM | POST | /api/bom/{bom_id}/set-default | bom_id | name, is_default |
| 展开 BOM | POST | /api/bom/{bom_id}/explode | size_ratio, order_qty | material_requirements, operation_costs |

【业务规则】
1. 款式只能有一个生效的默认 BOM，设置新默认 BOM 时必须取消同款式其他默认 BOM。
2. 含损耗用量 = qty_per_piece × (1 + loss_rate)。
3. 工序成本 = 本厂计件工价 + 制造费用分摊，外发工序使用 subcontract_cost_per_piece。
4. BOM 展开 = 按尺码分布计算每种尺码的数量 × 含损耗用量，最后按物料合并。
5. BOM 发布后不可直接修改，只能复制生成新版本。
6. BOM 唯一契约冻结为 `ly_apparel_bom / ly_apparel_bom_item / ly_bom_operation` 和 `/api/bom/`，禁止再引用 `ly_style_*`、`/api/bom/styles`、`/api/bom/style-boms`。

【验收标准】
□ POST /api/bom/ 能创建 BOM，并返回 data.name。
□ 同一 item_code 设置第二个默认 BOM 后，旧默认 BOM 的 is_default 自动变为 false。
□ POST /api/bom/{bom_id}/explode 输入 order_qty=100、loss_rate=0.05 时，返回的物料需求包含损耗后数量。
□ GET /api/bom/ 支持 page 和 page_size，并返回 items、total、page、page_size。
□ BOM 明细中的 material_item_code 必须能在 ERPNext public.tabItem 中找到。

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| Item | REST API GET /api/resource/Item/{name} | 校验款式和物料是否存在 |
| Item | REST API GET /api/resource/Item | 查询面辅料和成品物料 |
| Workflow | REST API 或 method API | BOM 发布审批时复用 ERPNext 审批能力 |

【前置依赖】
无

【预计工时】
4-6 天

【工程师完成标记】
| 项目 | 内容 |
| --- | --- |
| 完成时间 | 2026-04-11 21:45 CST |
| 交付物路径 | /07_后端/lingyi_service/app/models/bom.py；/07_后端/lingyi_service/app/schemas/bom.py；/07_后端/lingyi_service/app/services/bom_service.py；/07_后端/lingyi_service/app/routers/bom.py；/07_后端/lingyi_service/app/main.py；/07_后端/lingyi_service/migrations/versions/task_001_create_bom_tables.py；/06_前端/lingyi-pc/src/api/bom.ts；/06_前端/lingyi-pc/src/views/bom/BomList.vue；/06_前端/lingyi-pc/src/views/bom/BomDetail.vue；/06_前端/lingyi-pc/src/router/index.ts |
| 遗留问题 | 无 |

════════════════════════════════════════════════════════════════════════════

【任务卡】第 2 张 / 共 6 张
模块：外发加工管理（TASK-002）
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
实现外发加工全链路管理，从发外单创建到发料、回料、验货、扣款、对账全部覆盖。

【模块概述】
外发加工是服装工厂的核心业务链路。款式的洗水、印花、绣花等工序通常外发给专业加工厂。外发单记录发给哪个加工厂、发了什么料、收了多少货、验货扣了多少钱。外发过程中的发料和回料必须进入 ERPNext `Stock Entry`，对账金额由 FastAPI 汇总后进入加工厂对账单。

【涉及文件】
新建：
- /07_后端/lingyi_service/app/models/subcontract.py
- /07_后端/lingyi_service/app/schemas/subcontract.py
- /07_后端/lingyi_service/app/routers/subcontract.py
- /07_后端/lingyi_service/app/services/subcontract_service.py
- /06_前端/lingyi-pc/src/views/subcontract/*.vue
- /06_前端/lingyi-pc/src/api/subcontract.ts
修改：
- /07_后端/lingyi_service/app/main.py（注册路由）
- /06_前端/lingyi-pc/src/router/index.ts（添加路由）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引 |
| --- | --- | --- | --- |
| ly_schema.ly_subcontract_order | 外发加工单 | id, subcontract_no, supplier, item_code, bom_id, status, planned_qty | uk_subcontract_no, idx_supplier_status, idx_item_code |
| ly_schema.ly_subcontract_material | 外发发料明细 | id, subcontract_id, material_item_code, required_qty, issued_qty, stock_entry_name | idx_subcontract_id, idx_stock_entry |
| ly_schema.ly_subcontract_receipt | 外发回料验货 | id, subcontract_id, received_qty, inspected_qty, rejected_qty, deduction_amount | idx_subcontract_id, idx_inspect_status |
| ly_schema.ly_subcontract_status_log | 外发状态日志 | id, subcontract_id, from_status, to_status, operator, operated_at | idx_subcontract_time |
| public.tabStock Entry | ERPNext 库存单据 | name, stock_entry_type, docstatus | ERPNext 标准索引 |

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 创建外发单 | POST | /api/subcontract/ | supplier, item_code, bom_id, planned_qty, process_name | code, message, data.name |
| 查询外发单 | GET | /api/subcontract/ | supplier, status, from_date, to_date, page, page_size | items, total, page, page_size |
| 创建发料单 | POST | /api/subcontract/{id}/issue-material | warehouse, materials | stock_entry_name, status |
| 登记回料 | POST | /api/subcontract/{id}/receive | received_qty, inspected_qty, rejected_qty | receipt_name, rejected_rate |
| 完成验货 | POST | /api/subcontract/{id}/inspect | inspected_qty, rejected_qty, deduction_rate | deduction_amount, net_amount |

【业务规则】
1. 外发单状态机：草稿 → 加工中 → 待回料 → 待验货 → 已完成 → 已取消。
2. 发料时创建 ERPNext Stock Entry（Material Issue）。
3. 回料时创建 ERPNext Stock Entry（Material Receipt）。
4. 验货时计算不合格率 = rejected_qty / inspected_qty。
5. 扣款 = 不合格数量 × 单件扣款金额。
6. 实付金额 = 加工费合计 - 扣款金额。

【验收标准】
□ POST /api/subcontract/ 能创建外发单，并返回 data.name。
□ POST /api/subcontract/{id}/issue-material 成功后返回 ERPNext stock_entry_name。
□ POST /api/subcontract/{id}/receive 成功后状态从待回料流转到待验货。
□ inspected_qty=100、rejected_qty=5 时 rejected_rate 返回 0.05。
□ 外发单状态为已完成后，不允许再次执行发料接口。

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| Supplier | REST API GET /api/resource/Supplier/{name} | 校验加工厂供应商 |
| Stock Entry | REST API POST /api/resource/Stock Entry | 创建发料和回料库存单据 |
| Stock Ledger Entry | REST API GET /api/resource/Stock Ledger Entry | 查询库存台账回写结果 |

【前置依赖】
TASK-001：BOM 管理

【预计工时】
5-7 天

【开发前门禁】
TASK-002A 外发模块设计契约冻结必须先完成并通过审阅，才允许进入 TASK-002B~TASK-002H 工程实现。

TASK-002A 必须冻结：
- 写接口幂等契约：`idempotency_key` / 业务唯一键、`SUBCONTRACT_IDEMPOTENCY_CONFLICT`、重复提交验收用例
- 对账结算边界：`statement_id/settlement_no/settled_by/settled_at`、结算后锁定、调整/反冲规则
- 内部库存同步 worker 安全契约：生产开关、服务账号最小资源权限、dry-run/诊断审计、越权 outbox 处理策略

【TASK-002 拆分执行状态】
- TASK-002A 外发模块设计契约冻结：已封版，通过审计意见书第34份。
- TASK-002B 外发权限与审计基线：TASK-002B1 已通过审计，允许进入 TASK-002C。
- TASK-002C 外发数据模型与迁移：TASK-002C1 已通过审计，允许进入 TASK-002D。
- TASK-002D 发料 Stock Entry Outbox：TASK-002D1 已通过审计，允许进入 TASK-002E。
- TASK-002D/ADR-034 契约同步：`event_key` 以幂等事件为单位生成，不包含 `issue_batch_no`，已同步任务单与 ADR。
- TASK-002E 回料 Stock Entry Outbox：TASK-002E1 已通过审计，回料 outbox 与精确 retry 闭环通过。
- TASK-002E1 回料同步重试精确定位整改：已通过审计意见书第42份；遗留风险 `get_retry_target()` 清理纳入 TASK-002F 前置清理。
- TASK-002F 验货扣款金额口径：TASK-002F1 已有条件通过，验货主路径、金额公式、幂等批次隔离和详情 inspections 已闭环。
- TASK-002F1 验货幂等批次隔离与详情闭环整改：审计意见书第44份有条件通过；高危已闭环。
- TASK-002F2 并发验货不超量回归测试：TASK-002F3 已通过审计，默认测试与 PostgreSQL marker 门禁闭环。
- TASK-002F3 PostgreSQL 并发验货集成测试门禁整改：已通过审计意见书第46份；后续风险为提供 `POSTGRES_TEST_DSN` 后补跑真实非 skip PostgreSQL 并发测试并记录结果。
- TASK-002G 前端状态与权限联动：审计意见书第47份不通过；阻断项为外发前端 API 裸 `fetch()` 未接入统一鉴权与错误信封，中危项为列表页逐行拉详情。
- TASK-002G1 前端外发 API 统一鉴权与列表摘要整改：审计意见书第48份确认 N+1 与鉴权高危已修复，剩余低危为后端 list 未返回 latest issue/receipt 同步摘要字段。
- TASK-002G2 外发列表同步摘要字段封版整改：审计意见书第49份确认功能修复通过，剩余低危为缺少列表摘要字段和 latest outbox 选择规则自动化测试。
- TASK-002G3 外发列表摘要自动化测试补齐：已通过审计意见书第50份；列表摘要字段和 latest outbox 选择规则测试已闭环。
- TASK-002H 对账数据出口：审计意见书第51份不通过；阻断项为结算锁定/释放共用可变幂等字段导致旧锁定请求可重放。
- TASK-002H1 结算幂等重放漏洞整改：审计意见书第52份有条件通过；主漏洞已修复，剩余中危为同 key 并发唯一冲突可能返回 DATABASE_WRITE_FAILED。
- TASK-002H2 结算并发幂等 Replay 整改：已通过审计意见书第53份；常规测试 414 passed，剩余风险为 PostgreSQL 并发语义未非 skip 验证。
- TASK-002H3 PostgreSQL 结算并发集成验证：审计意见书第54份不通过；阻断项为 destructive 测试仅凭 DSN 即执行 `DROP SCHEMA ly_schema CASCADE`，缺少双重安全门禁。
- TASK-002H4 PostgreSQL 测试库破坏性操作门禁整改：已通过审计意见书第55份；destructive gate 已闭环。
- TASK-002H5 PostgreSQL 非 Skip 实跑验证：已通过审计意见书第56份；工程师已提供一次性测试库非 skip `4 passed, 0 skipped` 证据，审计窗口本地无 DSN 仅复核安全 skip 与全量回归。
- TASK-002H6 PostgreSQL 非 Skip CI 硬门禁：已通过审计意见书第57份；JUnit 硬断言闭环，剩余风险为 GitHub hosted runner artifact 与 required check 平台配置确认。
- TASK-002H7 GitHub Actions 实跑与 Required Check 固化：审计意见书第58份有条件通过；本地 hard gate 与证据 README 合格，但 Hosted Runner run URL、artifact 核验和 required check 仍受权限阻塞。
- TASK-002H7A Hosted Runner 与 Required Check 管理员闭环：审计意见书第59份通过；作为管理员闭环前模板化处理合格，但平台真实 run URL、artifact 与 required check 仍需管理员实际回填。
- TASK-002H7B GitHub 平台最终闭环证据提交：审计意见书第60份通过；作为管理员平台闭环前证据模板拆分合格，但三份证据文档 pending 字段仍需真实清零。
- TASK-002H7C GitHub 平台 Pending 清零与最终复审：审计已通过其“Pending 清零 + 最终复审”模板；但 GitHub hosted runner、artifact、required check 真实平台闭环仍未完成。
- TASK-006 加工厂对账单：继续阻塞；必须等待管理员完成 hosted runner 实跑、artifact 核验、required check 配置、三份证据 pending 清零，并经审计最终确认后再进入。

════════════════════════════════════════════════════════════════════════════

【任务卡】第 3 张 / 共 6 张
模块：工票/车间管理（TASK-003）
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
实现工票登记、撤销、批量操作，支持按工单和员工统计日薪。

【模块概述】
工票是车间执行层。工人刷卡或扫码登记当天完成的数量，系统按工价计算日薪。模块支持批量登记和撤销，兼容来自 PDA 或 MES 系统的推送，也支持人工页面操作。工票与 ERPNext `Job Card` 关联，用于把实际完成数量回写到工序执行闭环。

【涉及文件】
新建：
- /07_后端/lingyi_service/app/models/workshop.py
- /07_后端/lingyi_service/app/schemas/workshop.py
- /07_后端/lingyi_service/app/routers/workshop.py
- /07_后端/lingyi_service/app/services/workshop_service.py
- /06_前端/lingyi-pc/src/views/workshop/*.vue
- /06_前端/lingyi-pc/src/api/workshop.ts
修改：
- /07_后端/lingyi_service/app/main.py（注册路由）
- /06_前端/lingyi-pc/src/router/index.ts（添加路由）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引 |
| --- | --- | --- | --- |
| ly_schema.ys_workshop_ticket | 工票记录 | id, ticket_key, job_card, employee, process_name, color, size, operation_type, qty, work_date | uk_ticket_idempotent, idx_employee_date, idx_job_card |
| ly_schema.ys_workshop_daily_wage | 日薪汇总 | id, employee, work_date, net_qty, wage_rate, wage_amount | uk_employee_date_process, idx_work_date |
| ly_schema.ly_operation_wage_rate | 工价档案 | id, process_name, item_code, wage_rate, effective_from, effective_to | idx_process_item, idx_effective_date |
| public.tabJob Card | ERPNext 工序卡 | name, work_order, operation, status | ERPNext 标准索引 |
| public.tabEmployee | ERPNext 员工 | name, employee_name, status | ERPNext 标准索引 |

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 登记工票 | POST | /api/workshop/tickets/register | ticket_key, job_card, employee, process_name, color, size, qty | code, message, data.name |
| 撤销工票 | POST | /api/workshop/tickets/reversal | ticket_key, job_card, employee, process_name, color, size, qty | reversal_name, net_qty |
| 批量导入工票 | POST | /api/workshop/tickets/batch | tickets | success_count, failed_items |
| 查询工票 | GET | /api/workshop/tickets | employee, job_card, work_date, page, page_size | items, total, page, page_size |
| 查询日薪 | GET | /api/workshop/daily-wages | employee, from_date, to_date | items, total_amount |

【业务规则】
1. 工票类型：登记（Register）和撤销（Reversal）。
2. 幂等性：同一 ticket_key + process_name + color + size + operation_type + date 只允许一条记录。
3. 日薪 = 当日净数量（登记数量 - 撤销数量）× 计件单价。
4. 与 ERPNext Job Card 关联（Link 字段）。
5. 撤销数量不得大于同维度已登记未撤销数量。

【验收标准】
□ POST /api/workshop/tickets/register 能创建登记工票，并返回 data.name。
□ 相同 ticket_key、process_name、color、size、operation_type、work_date 重复提交时返回幂等结果，不新增第二条。
□ 登记 100 件、撤销 10 件、计件单价 0.5 时，GET /api/workshop/daily-wages 返回 wage_amount=45。
□ job_card 不存在时，登记接口返回错误 code=WORKSHOP_JOB_CARD_NOT_FOUND。
□ 批量导入接口返回 success_count 和 failed_items。

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| Job Card | REST API GET /api/resource/Job Card/{name} | 校验工序卡存在并读取工序 |
| Employee | REST API GET /api/resource/Employee/{name} | 校验员工有效 |
| Job Card | REST API PUT 或 method API | 汇总工票数量后更新工序卡完成进度 |

【前置依赖】
TASK-001：BOM 管理

【预计工时】
4-6 天

【工程师完成标记】
| 项目 | 内容 |
| --- | --- |
| 完成时间 | 2026-04-12 12:53 CST |
| 交付物路径 | /07_后端/lingyi_service/app/models/workshop.py；/07_后端/lingyi_service/app/schemas/workshop.py；/07_后端/lingyi_service/app/services/workshop_service.py；/07_后端/lingyi_service/app/services/erpnext_job_card_adapter.py；/07_后端/lingyi_service/app/routers/workshop.py；/07_后端/lingyi_service/app/main.py；/07_后端/lingyi_service/app/core/permissions.py；/07_后端/lingyi_service/app/services/permission_service.py；/07_后端/lingyi_service/app/services/audit_service.py；/07_后端/lingyi_service/migrations/versions/task_003_create_workshop_tables.py；/07_后端/lingyi_service/tests/test_workshop_ticket.py；/07_后端/lingyi_service/tests/test_workshop_wage.py；/07_后端/lingyi_service/tests/test_workshop_permissions.py；/07_后端/lingyi_service/tests/test_workshop_job_card_sync.py；/06_前端/lingyi-pc/src/api/workshop.ts；/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketList.vue；/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketRegister.vue；/06_前端/lingyi-pc/src/views/workshop/WorkshopTicketBatch.vue；/06_前端/lingyi-pc/src/views/workshop/WorkshopDailyWage.vue；/06_前端/lingyi-pc/src/views/workshop/OperationWageRate.vue；/06_前端/lingyi-pc/src/router/index.ts；/06_前端/lingyi-pc/src/stores/permission.ts；/06_前端/lingyi-pc/src/api/auth.ts |
| 遗留问题 | 无 |

════════════════════════════════════════════════════════════════════════════

【任务卡】第 4 张 / 共 6 张
模块：生产计划集成（TASK-004）
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
打通 Sales Order → BOM 展开 → 生产工单 → 工序卡 → 工票执行 的完整链路。

【模块概述】
生产计划集成把销售订单转化为车间可执行任务。销售订单审批通过后，系统按款式 BOM 展开生成生产计划，再调用 ERPNext 创建 `Work Order`。`Work Order` 按 BOM 工序生成 `Job Card`，工人通过工票系统登记执行结果。该模块负责跨 ERPNext 和 FastAPI 的状态同步。

【涉及文件】
新建：
- /07_后端/lingyi_service/app/models/production.py
- /07_后端/lingyi_service/app/schemas/production.py
- /07_后端/lingyi_service/app/routers/production.py
- /07_后端/lingyi_service/app/services/production_service.py
- /06_前端/lingyi-pc/src/views/production/*.vue
- /06_前端/lingyi-pc/src/api/production.ts
修改：
- /07_后端/lingyi_service/app/main.py（注册路由）
- /06_前端/lingyi-pc/src/router/index.ts（添加路由）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引 |
| --- | --- | --- | --- |
| ly_schema.ly_production_plan | 生产计划 | id, plan_no, sales_order, item_code, bom_id, planned_qty, status | uk_plan_no, idx_sales_order, idx_status |
| ly_schema.ly_production_plan_item | 计划物料需求 | id, plan_id, material_item_code, required_qty, available_qty, shortage_qty | idx_plan_id, idx_material_item |
| ly_schema.ly_work_order_link | ERPNext 工单映射 | id, plan_id, work_order, sync_status, last_synced_at | uk_work_order, idx_plan_id |
| public.tabSales Order | ERPNext 销售订单 | name, customer, status, docstatus | ERPNext 标准索引 |
| public.tabWork Order | ERPNext 生产工单 | name, production_item, qty, status | ERPNext 标准索引 |
| public.tabJob Card | ERPNext 工序卡 | name, work_order, operation, status | ERPNext 标准索引 |

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 创建生产计划 | POST | /api/production/plans | sales_order, item_code, bom_id, planned_qty | code, message, data.name |
| BOM 展开检查 | POST | /api/production/plans/{id}/material-check | warehouse | material_items, shortage_items |
| 创建 Work Order | POST | /api/production/plans/{id}/create-work-order | fg_warehouse, wip_warehouse, start_date | work_order, status |
| 同步 Job Card | POST | /api/production/work-orders/{work_order}/sync-job-cards | work_order | job_cards, sync_status |
| 查询生产计划 | GET | /api/production/plans | sales_order, status, page, page_size | items, total, page, page_size |

【业务规则】
1. SO 审批通过后自动生成或手动生成 Production Plan。
2. Production Plan 按款式展开 BOM，生成 Work Order。
3. Work Order 按 BOM 工序生成 Job Card。
4. Job Card 完工数量与工票系统对接。
5. 工票数量汇总更新 Job Card 的完成状态。

【验收标准】
□ POST /api/production/plans 输入有效 sales_order 和 bom_id 后返回 data.name。
□ 未审批通过的 Sales Order 不允许生成生产计划，并返回 code=PRODUCTION_SO_NOT_APPROVED。
□ POST /api/production/plans/{id}/create-work-order 成功后返回 ERPNext work_order。
□ Work Order 创建成功后，ly_work_order_link 中能查到 plan_id 和 work_order 映射。
□ 同一个生产计划重复创建 Work Order 时，接口返回已有 work_order，不创建第二个。

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| Sales Order | REST API GET /api/resource/Sales Order/{name} | 读取销售订单和审批状态 |
| Work Order | REST API POST /api/resource/Work Order | 创建生产工单 |
| Job Card | REST API GET /api/resource/Job Card | 查询工序卡状态 |

【前置依赖】
TASK-001：BOM 管理；TASK-003：工票/车间管理

【预计工时】
4-6 天

【TASK-004 拆分执行状态】
- TASK-004A 生产计划后端基线与 Work Order Outbox：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-004A_生产计划后端基线与WorkOrderOutbox_工程任务单.md`。本任务只做后端基线、权限审计、迁移、Work Order outbox/worker 和 Job Card 本地映射；不做前端、不做生产入库、不进入 TASK-005/TASK-006。
- TASK-004A1 生产计划审计阻断整改：审计意见书第 63 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004A1_生产计划审计阻断整改_工程任务单.md`。第 62 份的 5 个必改问题已闭环，允许进入 TASK-004B；TASK-005/TASK-006 仍未放行。
- TASK-004B 生产计划前端联动：审计意见书第 64 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-004B_生产计划前端联动_工程任务单.md`。主要遗留为 planned_start_date 契约、内部 worker 按钮权限、详情 DTO 字段和状态标签。
- TASK-004B1 生产计划前端契约整改：审计意见书第 65 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004B1_生产计划前端契约整改_工程任务单.md`。第 64 份 4 个问题已闭环，允许进入 TASK-004C；TASK-005/TASK-006 仍未放行。
- TASK-004C 前端最小构建与契约校验基建：审计意见书第 66 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C_前端最小构建与契约校验基建_工程任务单.md`。`package.json/typecheck/build/check:production-contracts` 已补齐，允许进入 TASK-004C1；TASK-005/TASK-006 仍未放行。
- TASK-004C1 前端契约扫描盲区整改：审计意见书第 67 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C1_前端契约扫描盲区整改_工程任务单.md`。`src/router/src/stores` 已纳入脚本门禁，允许进入 TASK-004C2；TASK-005/TASK-006 仍未放行。
- TASK-004C2 前端契约脚本自动反向测试：审计意见书第 68 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C2_前端契约脚本自动反向测试_工程任务单.md`。10 个场景已通过，允许进入 TASK-004C3；TASK-005/TASK-006 仍未放行。
- TASK-004C3 前端契约反向测试独立用例补齐：审计意见书第 69 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C3_前端契约反向测试独立用例补齐_工程任务单.md`。`work-order-sync/run-once` 和敏感关键字独立 fixture 已补齐，允许进入 TASK-004C4；TASK-005/TASK-006 仍未放行。
- TASK-004C4 前端 Verify CI 与 Node 版本锁定：审计意见书第 70 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C4_前端VerifyCI与Node版本锁定_工程任务单.md`。`npm run verify` 已进入 GitHub Actions，Node `22.22.1` / npm `10.9.4` 已完成本地与 CI 双侧锁定；允许进入 TASK-004C5。
- TASK-004C5 前端 CI 平台 Required Check 闭环：审计意见书第 71 份有条件通过但平台未闭环，路径 `/03_需求与设计/02_开发计划/TASK-004C5_前端CI平台RequiredCheck闭环_工程任务单.md`。证据文件作为阻塞说明合格，但 hosted runner 实跑、Run URL、Commit SHA、required check 仍未完成；进入 TASK-004C6。
- TASK-004C6 Git 仓库根与 CI 可见性整改：审计意见书第 72 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C6_Git仓库根与CI可见性整改_工程任务单.md`。阻塞态证据确认项目根不是 git repo，真实可检测 git root 是 `/02_源码`，但 workflow、前端、后端交付目录不在当前 git root 跟踪范围内；进入 TASK-004C7。
- TASK-004C7 项目根 GitHub 仓库根策略落地：审计意见书第 73 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-004C7_项目根GitHub仓库根策略落地_工程任务单.md`。项目根 git root 已立起来，`02_源码/.git` 已备份迁出，关键 workflow 和部分关键文件已进入根仓库索引；进入 TASK-004C8。
- TASK-004C8 根仓库首个提交清单与离线 CI 模拟：审计意见书第 74 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C8_根仓库首个提交清单与离线CI模拟_工程任务单.md`。根仓库首个提交已完成，tracked 文件从 6 个补齐到 236 个，审计 snapshot 前后端验证通过；进入 TASK-004C9。
- TASK-004C9 GitHub 远端推送与前端 Required Check 闭环：审计意见书第 75 份有条件通过但平台未闭环，路径 `/03_需求与设计/02_开发计划/TASK-004C9_GitHub远端推送与前端RequiredCheck闭环_工程任务单.md`。本地基线属实，但缺 GitHub URL、origin、push、hosted runner、required check；进入 TASK-004C10，先补 C9 证据与最新审计记录 docs-only commit。
- TASK-004C10 C9 证据与审计记录补提交：审计意见书第 76 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C10_C9证据与审计记录补提交_工程任务单.md`。C9 证据和第 75 份审计记录已完成 docs-only commit，当前本地基线为 `b32585c docs: record frontend platform gate blocker`；进入 TASK-004C11。
- TASK-004C11 GitHub 平台最终闭环：审计意见书第 77 份有条件通过但平台未闭环，路径 `/03_需求与设计/02_开发计划/TASK-004C11_GitHub平台最终闭环_工程任务单.md`。管理员仍需提供 GitHub URL、配置 `origin`、push `main`、hosted runner 实跑和 required check；另需修正 C11 证据中 `fc0dc2c`、`62e70bd` 与“待推送 HEAD”的 SHA 口径，进入 TASK-004C12。
- TASK-004C12 C11 证据 SHA 口径修正：审计意见书第 78 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C12_C11证据SHA口径修正_工程任务单.md`。SHA 口径问题已闭环，`64fdfe4` 为当前新的本地待推送 HEAD；GitHub 平台闭环仍未完成，进入 TASK-004C13。
- TASK-004C13 GitHub 平台闭环管理员执行：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-004C13_GitHub平台闭环管理员执行单.md`。要求管理员提供 GitHub URL，完成 docs-only 准备提交、配置 `origin`、非强推 `main`、Hosted Runner 实跑、main required check 和平台证据回填；审计复审通过前不进入 TASK-005/TASK-006。

════════════════════════════════════════════════════════════════════════════

【任务卡】第 5 张 / 共 6 张
模块：款式利润报表（TASK-005）
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
实现款式维度的利润分析报表，含标准成本和实际成本对比。

【模块概述】
款式利润报表用于判断每个款式、每张订单是否赚钱。利润来自 ERPNext 销售收入、采购和库存实际成本，也来自 FastAPI 自建的 BOM、工票、外发和对账数据。报表既要支持标准成本预估，也要支持实际成本回算。每次计算需要保留快照，确保财务和业务可以追溯同一口径。

【涉及文件】
新建：
- /07_后端/lingyi_service/app/models/style_profit.py
- /07_后端/lingyi_service/app/schemas/style_profit.py
- /07_后端/lingyi_service/app/routers/style_profit.py
- /07_后端/lingyi_service/app/services/style_profit_service.py
- /06_前端/lingyi-pc/src/views/style_profit/*.vue
- /06_前端/lingyi-pc/src/api/style_profit.ts
修改：
- /07_后端/lingyi_service/app/main.py（注册路由）
- /06_前端/lingyi-pc/src/router/index.ts（添加路由）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引 |
| --- | --- | --- | --- |
| ly_schema.ly_style_profit_snapshot | 利润快照 | id, snapshot_no, sales_order, item_code, revenue_amount, standard_cost_amount, actual_cost_amount, profit_amount | uk_snapshot_no, idx_item_order, idx_created_at |
| ly_schema.ly_style_profit_detail | 利润明细 | id, snapshot_id, cost_type, source_type, source_name, amount | idx_snapshot_id, idx_cost_type |
| ly_schema.ly_cost_allocation_rule | 费用分摊规则 | id, rule_name, cost_type, allocation_basis, status | idx_cost_type_status |
| public.tabSales Order | ERPNext 销售订单 | name, grand_total, status | ERPNext 标准索引 |
| public.tabPurchase Receipt | ERPNext 采购入库 | name, supplier, posting_date | ERPNext 标准索引 |
| public.tabStock Ledger Entry | ERPNext 库存成本 | item_code, actual_qty, stock_value_difference | ERPNext 标准索引 |

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 查询款式利润 | GET | /api/reports/style-profit/ | item_code, sales_order, from_date, to_date, page, page_size | items, total, page, page_size |
| 生成利润快照 | POST | /api/reports/style-profit/snapshot | item_code, sales_order | snapshot_no, profit_amount, profit_rate |
| 查询利润明细 | GET | /api/reports/style-profit/{snapshot_id} | snapshot_id | summary, details |
| 标准实际对比 | GET | /api/reports/style-profit/compare | item_code, sales_order | standard_cost, actual_cost, variance_amount |

【业务规则】
1. 标准材料成本 = BOM 展开用量 × 采购单价（来自 ERPNext Item）。
2. 标准工序成本 = BOM 工序成本 × 订单数量。
3. 实际材料成本 = 采购实际入库成本（来自 ERPNext Purchase Receipt）。
4. 实际工序成本 = 工票实际工价 × 实际完成数量。
5. 款式利润 = 销售单价 × 数量 - 标准材料成本 - 实际工序成本 - 外发加工费。

【验收标准】
□ POST /api/reports/style-profit/snapshot 能生成利润快照，并返回 snapshot_no。
□ GET /api/reports/style-profit/{snapshot_id} 返回 summary 和 details。
□ 销售金额 10000、标准材料成本 3000、实际工序成本 2000、外发加工费 1000 时，profit_amount 返回 4000。
□ 标准成本和实际成本必须分别展示，不允许混为一个字段。
□ 利润快照生成后再次重算必须生成新快照，不覆盖旧快照。

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| Sales Order | REST API GET /api/resource/Sales Order/{name} | 获取销售收入和订单数量 |
| Purchase Receipt | REST API GET /api/resource/Purchase Receipt | 获取采购实际入库成本 |
| Stock Ledger Entry | REST API GET /api/resource/Stock Ledger Entry | 获取库存成本变动 |

【前置依赖】
TASK-001：BOM 管理；TASK-002：外发加工管理；TASK-003：工票/车间管理；TASK-004：生产计划集成

【预计工时】
4-6 天

【TASK-005 拆分执行状态】
- TASK-005A 款式利润报表开发前基线盘点：审计意见书第 80 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-005A_款式利润报表开发前基线盘点_工程任务单.md`。只读盘点本身合格，但关键文档尚未进入 git 提交链，且不得误解为 TASK-005B 可开工；进入 TASK-005A1。
- TASK-005A1 利润盘点文档证据链补提交：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005A1_利润盘点文档证据链补提交_工程任务单.md`。只做 docs-only 白名单提交，目标是让 TASK-005A 任务单、基线盘点报告、模块设计、ADR、Sprint、审计记录和日志进入提交链；TASK-004C13 平台闭环和审计复审通过前，不进入 TASK-005B/TASK-006。

════════════════════════════════════════════════════════════════════════════

【任务卡】第 6 张 / 共 6 张
模块：加工厂对账单（TASK-006）
优先级：P0（第一阶段核心）
════════════════════════════════════════════════════════════════════════════

【任务目标】
按加工厂汇总指定时间段内的所有外发单，输出对账单。

【模块概述】
加工厂对账单服务于月底财务对账。系统按加工厂汇总本月发了哪些外发单、每单交货多少、验货扣了多少、最终应付多少。对账单需要支持打印和确认，确认后才能进入 ERPNext 应付建议。该模块依赖外发加工的收货、验货和扣款数据。

【涉及文件】
新建：
- /07_后端/lingyi_service/app/models/factory_statement.py
- /07_后端/lingyi_service/app/schemas/factory_statement.py
- /07_后端/lingyi_service/app/routers/factory_statement.py
- /07_后端/lingyi_service/app/services/factory_statement_service.py
- /06_前端/lingyi-pc/src/views/factory_statement/*.vue
- /06_前端/lingyi-pc/src/api/factory_statement.ts
修改：
- /07_后端/lingyi_service/app/main.py（注册路由）
- /06_前端/lingyi-pc/src/router/index.ts（添加路由）

【数据库表设计】
| 表名 | 用途 | 关键字段 | 索引 |
| --- | --- | --- | --- |
| ly_schema.ly_factory_statement | 加工厂对账单 | id, statement_no, supplier, from_date, to_date, total_qty, gross_amount, deduction_amount, net_amount, status | uk_statement_no, idx_supplier_period, idx_status |
| ly_schema.ly_factory_statement_item | 对账明细 | id, statement_id, subcontract_id, delivered_qty, accepted_qty, rejected_rate, gross_amount, deduction_amount, net_amount | idx_statement_id, idx_subcontract_id |
| ly_schema.ly_factory_statement_log | 对账操作日志 | id, statement_id, action, operator, operated_at, remark | idx_statement_action_time |
| public.tabSupplier | ERPNext 加工厂 | name, supplier_name, supplier_group | ERPNext 标准索引 |
| public.tabPurchase Invoice | ERPNext 应付发票 | name, supplier, grand_total, docstatus | ERPNext 标准索引 |

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 生成对账单 | POST | /api/factory-statements/ | supplier, from_date, to_date | code, message, data.name |
| 查询对账单 | GET | /api/factory-statements/ | supplier, status, from_date, to_date, page, page_size | items, total, page, page_size |
| 查询对账详情 | GET | /api/factory-statements/{id} | id | statement, items |
| 确认对账单 | POST | /api/factory-statements/{id}/confirm | confirmed_by, remark | name, status |
| 生成应付建议 | POST | /api/factory-statements/{id}/payable-draft | payable_account, cost_center | purchase_invoice_draft, net_amount |

【业务规则】
1. 按供应商（加工厂）汇总。
2. 按时间段筛选（从日期 / 到日期）。
3. 汇总项：订单数量、已交货数量、合格数量、不合格率、加工费合计、扣款合计、实付金额。
4. 明细列出每个外发单的分项数据。
5. 实付金额 = 加工费合计 - 扣款合计。

【验收标准】
□ POST /api/factory-statements/ 输入 supplier、from_date、to_date 后能生成对账单并返回 data.name。
□ 同一 supplier、同一日期范围、同一外发单明细不得重复生成未取消对账单。
□ 加工费 5000、扣款 300 时，net_amount 返回 4700。
□ GET /api/factory-statements/{id} 返回 statement 和 items。
□ 对账单确认后不允许修改明细金额，只允许生成调整记录或取消后重建。

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| Supplier | REST API GET /api/resource/Supplier/{name} | 校验加工厂供应商 |
| Purchase Invoice | REST API POST /api/resource/Purchase Invoice | 对账确认后生成应付草稿 |
| Account | REST API GET /api/resource/Account | 校验应付科目 |

【前置依赖】
TASK-002：外发加工管理

【预计工时】
3-5 天

════════════════════════════════════════════════════════════════════════════
