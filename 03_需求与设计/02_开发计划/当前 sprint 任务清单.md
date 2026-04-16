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
- TASK-004C13 GitHub 平台闭环管理员执行：已停止继续等待 GitHub URL，路径 `/03_需求与设计/02_开发计划/TASK-004C13_GitHub平台闭环管理员执行单.md`。用户确认项目没有 GitHub、一直按本地交付，继续等待 URL 会形成死循环；进入 TASK-004C14，以本地仓库门禁替代 GitHub 平台闭环。
- TASK-004C14 本地仓库门禁替代 GitHub 平台闭环：审计意见书第 83 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-004C14_本地仓库门禁替代GitHub平台闭环_工程任务单.md`。本地验证门禁通过，当前 HEAD `506fbfa` 为 docs-only 变更；允许 TASK-005B 从“等待 GitHub URL”阻塞中释放，但只能进入利润口径设计冻结，不得进入模型、迁移、API 或前端实现。

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
| ly_schema.ly_style_profit_snapshot | 利润快照 | snapshot_no, company, sales_order, item_code, revenue_status, estimated_revenue_amount, actual_revenue_amount, revenue_amount, standard_material_cost, standard_operation_cost, actual_material_cost, actual_workshop_cost, actual_subcontract_cost, allocated_overhead_amount, actual_total_cost, standard_total_cost, profit_amount, profit_rate, snapshot_status, formula_version | uk_snapshot_no, idx_item_order, idx_created_at |
| ly_schema.ly_style_profit_detail | 利润明细 | id, snapshot_id, cost_type, source_type, source_name, amount | idx_snapshot_id, idx_cost_type |
| ly_schema.ly_cost_allocation_rule | 费用分摊规则 | id, rule_name, cost_type, allocation_basis, status | idx_cost_type_status |
| public.tabSales Order | ERPNext 销售订单 | name, grand_total, status | ERPNext 标准索引 |
| public.tabPurchase Receipt | ERPNext 采购入库 | name, supplier, posting_date | ERPNext 标准索引 |
| public.tabStock Ledger Entry | ERPNext 库存成本 | item_code, actual_qty, stock_value_difference | ERPNext 标准索引 |

【接口清单】
| 接口名称 | HTTP方法 | 路径 | 入参 | 出参 |
| --- | --- | --- | --- | --- |
| 查询款式利润 | GET | /api/reports/style-profit/ | item_code, sales_order, from_date, to_date, page, page_size | items, total, page, page_size |
| 生成利润快照 | POST | /api/reports/style-profit/snapshot | company, item_code, sales_order, from_date, to_date, revenue_mode, include_provisional_subcontract, idempotency_key | snapshot_no, profit_amount, profit_rate |
| 查询利润明细 | GET | /api/reports/style-profit/{snapshot_id} | snapshot_id | summary, details |
| 标准实际对比 | GET | /api/reports/style-profit/compare | item_code, sales_order | standard_cost, actual_cost, variance_amount |

【业务规则】
1. `estimated_revenue_amount` 来自 ERPNext `Sales Order` 已提交订单行。
2. `actual_revenue_amount` 来自 ERPNext `Sales Invoice` 已提交发票行。
3. `revenue_amount` 优先使用 `actual_revenue_amount`，缺失时使用 `estimated_revenue_amount` 并标记 `revenue_status=estimated`。
4. `standard_material_cost = sum(bom_exploded_required_qty * standard_unit_cost)`，`standard_unit_cost` 来源为 `Item Price -> Item valuation_rate -> unresolved`。
5. `standard_operation_cost = sum(bom_operation_rate * planned_qty)`。
6. `actual_material_cost = sum(abs(stock_value_difference))`，来源 ERPNext `Stock Ledger Entry`。
7. `Purchase Receipt` 仅作采购成本参考和异常排查，不直接作为实际材料成本。
8. `actual_workshop_cost = sum((register_qty - reversal_qty) * wage_rate_snapshot)`。
9. `actual_subcontract_cost = sum(settlement_locked_net_amount or provisional_inspection_net_amount)`。
10. 扣款金额只做明细展示，已使用 `net_amount` 时不得重复扣减。
11. `allocated_overhead_amount = 0`，`allocation_status=not_enabled`。
12. `profit_amount = revenue_amount - actual_total_cost`；`revenue_amount=0` 时 `profit_rate=null`。
13. 快照不可变，重算必须生成新 `snapshot_no`。

【验收标准】
□ POST /api/reports/style-profit/snapshot 能生成利润快照，并返回 snapshot_no。
□ GET /api/reports/style-profit/{snapshot_id} 返回 summary 和 details。
□ `actual_revenue_amount` 存在时优先使用 actual。
□ 无 `Sales Invoice` 时使用 estimated，并标记 `revenue_status=estimated`。
□ `actual_material_cost` 使用 `Stock Ledger Entry`，不使用 `Purchase Receipt`。
□ 使用 `net_amount` 后扣款不重复扣减。
□ `allocated_overhead_amount=0` 且 `allocation_status=not_enabled`。
□ 同 `idempotency_key` + 不同 `request_hash` 返回 `STYLE_PROFIT_IDEMPOTENCY_CONFLICT`。
□ 利润快照重算生成新 `snapshot_no`，不覆盖旧快照。

【与 ERPNext 的接口】
| ERPNext 能力 | 调用方式 | 用途 |
| --- | --- | --- |
| Sales Order | REST API GET /api/resource/Sales Order/{name} | 获取预计收入（estimated_revenue_amount） |
| Sales Invoice | REST API GET /api/resource/Sales Invoice/{name} | 获取实际收入（actual_revenue_amount） |
| Stock Ledger Entry | REST API GET /api/resource/Stock Ledger Entry | 获取实际材料成本（actual_material_cost） |
| Purchase Receipt | REST API GET /api/resource/Purchase Receipt | 采购成本参考与异常排查，不直接计入 actual_material_cost |
| Item Price / Item | REST API GET /api/resource/Item Price, /api/resource/Item/{name} | 获取标准单价来源（Item Price 优先，Item valuation_rate 兜底） |

【前置依赖】
TASK-001：BOM 管理；TASK-002：外发加工管理；TASK-003：工票/车间管理；TASK-004：生产计划集成

【预计工时】
4-6 天

【TASK-005 拆分执行状态】
- TASK-005A 款式利润报表开发前基线盘点：审计意见书第 80 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-005A_款式利润报表开发前基线盘点_工程任务单.md`。只读盘点本身合格，但关键文档尚未进入 git 提交链，且不得误解为 TASK-005B 可开工；进入 TASK-005A1。
- TASK-005A1 利润盘点文档证据链补提交：审计意见书第 81 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-005A1_利润盘点文档证据链补提交_工程任务单.md`。证据入库问题已闭环，但存在未来时间口径问题，进入 TASK-005A2。
- TASK-005A2 利润盘点未来时间口径修正：审计意见书第 82 份已通过。未来时间口径已闭环，`59a55ec` 为 docs-only 提交；TASK-005A/A1/A2 文档问题已闭环。
- TASK-005B 款式利润口径设计冻结：审计意见书第 84 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-005B_款式利润口径设计冻结_工程任务单.md`。主体口径冻结合格，但 Sprint 主任务卡存在旧利润公式和旧 `Purchase Receipt` 实际材料成本口径，进入 TASK-005B1。
- TASK-005B1 Sprint 主任务卡利润旧口径修正：审计意见书第 85 份已通过。旧 `Purchase Receipt` 计实际材料成本口径、旧利润公式和 `profit_amount=4000` 示例已清理，已对齐 ADR-079 / TASK-005B 冻结口径。
- TASK-005C 利润模型迁移与来源映射设计：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005C_利润模型迁移与来源映射设计_工程任务单.md`。只允许模型、迁移、schema、来源映射骨架和测试；不得注册 API、不得实现完整利润计算服务、不得修改前端、不得进入 TASK-006。
- TASK-005C1 利润来源映射审计字段与状态 Fail Closed 整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005C1_利润来源映射审计字段与状态FailClosed整改_工程任务单.md`。先修复 source_map 审计追溯字段、`_is_submitted()` fail closed、snapshot 复核字段、费用分摊默认 disabled、SLE 款式/材料编码语义；审计通过前不得进入 TASK-005D/TASK-006。
- TASK-005C2 利润来源默认不纳入与字段契约收口整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005C2_利润来源默认不纳入与字段契约收口整改_工程任务单.md`。先修复 `include_in_profit=false` 默认值、source_map 字段契约、复合索引和 status-only 白名单；审计通过前不得进入 TASK-005D/TASK-006。
- TASK-005C3 利润快照期间索引补齐：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005C3_利润快照期间索引补齐_工程任务单.md`。只补 `idx_ly_style_profit_snapshot_company_item_period(company, item_code, from_date, to_date)` 和测试；审计通过前不得进入 TASK-005D/TASK-006。
- TASK-005C4 利润模型本地仓库基线提交：审计意见书第 90 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-005C4_利润模型本地仓库基线提交_工程任务单.md`。当前本地基线 HEAD `67a995c` 已纳入 TASK-005C~C3 利润模型、schema、来源映射服务、迁移、测试和配套文档；允许进入 TASK-005D 任务单准备。
- TASK-005D 利润快照计算服务：审计意见书第 92 份有条件通过但仍有 3 个 P1、3 个 P2 必改项，路径 `/03_需求与设计/02_开发计划/TASK-005D_利润快照计算服务_工程任务单.md`。不得进入 TASK-005E/API 层，不得进入 TASK-006。
- TASK-005D1 利润快照计算服务审计整改：审计意见书第 93 份有条件通过但仍有 2 个 P1、1 个 P2 必改项，路径 `/03_需求与设计/02_开发计划/TASK-005D1_利润快照计算服务审计整改_工程任务单.md`。request_hash、收入 unresolved、异常 SLE、缺工价、收入 source_status、idempotency_key 长度校验已通过复核；不得进入 TASK-005E/TASK-006。
- TASK-005D2 利润实际成本归属与事务兜底整改：审计意见书第 94 份有条件通过但仍有 1 个 P1 必改项，路径 `/03_需求与设计/02_开发计划/TASK-005D2_利润实际成本归属与事务兜底整改_工程任务单.md`。保存点回滚、空 sales_order、明确错范围来源已通过复核；不得进入 TASK-005E/TASK-006。
- TASK-005D3 利润实际成本关键归属字段 Fail Closed 整改：审计意见书第 95 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-005D3_利润实际成本关键归属字段FailClosed整改_工程任务单.md`。缺 company / 缺 item_code 不再仅凭 sales_order 计入利润，sales_order 非空、保存点、request_hash 来源输入均未回退；进入 TASK-005D4。
- TASK-005D4 利润快照服务本地仓库基线提交：审计意见书第 96 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-005D4_利润快照服务本地仓库基线提交_工程任务单.md`。commit `47c1728a4eb2ca16549f6478d3bdb5af95b12b1a` 已存在，利润服务与新增测试已纳入 git 跟踪；仅 D4 证据文件“提交后 HEAD”仍为占位符，进入 TASK-005D5。
- TASK-005D5 D4 证据提交后 HEAD 占位修正：审计意见书第 97 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-005D5_D4证据提交后HEAD占位修正_工程任务单.md`。D4 证据提交后 HEAD 已回填为 `47c1728a4eb2ca16549f6478d3bdb5af95b12b1a`，修正 commit `ff1f8dd` 未触碰后端、前端、`.github`、`02_源码`；但 D5 任务单本身仍需纳入文档基线，进入 TASK-005D6。
- TASK-005D6 D5 任务单文档基线提交：最新审计已通过，路径 `/03_需求与设计/02_开发计划/TASK-005D6_D5任务单文档基线提交_工程任务单.md`。commit `758d003` 已将 D5/D6 任务单纳入文档基线，提交范围 docs-only，未触碰后端、前端、`.github`、`02_源码`；允许准备 TASK-005E 任务单。
- TASK-005E 款式利润 API 权限与审计基线：待审计版任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005E_款式利润API权限与审计基线_工程任务单.md`。任务单必须先交审计官审查；审计通过前工程师不得进入 API 实现。TASK-006 继续阻塞。
- TASK-005E1 款式利润 API 权限审计基线实现：审计意见书第 99 份不通过，路径 `/03_需求与设计/02_开发计划/TASK-005E1_款式利润API权限审计基线实现_工程任务单.md`。阻断项包括来源采集器空实现、权限矩阵偏离冻结口径、鉴权顺序不正确、早期失败操作审计缺失；进入 TASK-005E2。
- TASK-005E2 款式利润 API 审计阻断整改：本轮审计有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-005E2_款式利润API审计阻断整改_工程任务单.md`。第 99 份 4 个主阻断项基本闭环，但详情接口仍存在先查 snapshot 再校验 `style_profit:read` 的存在性枚举风险；进入 TASK-005E3。
- TASK-005E3 款式利润详情接口鉴权前置整改：审计已通过，路径 `/03_需求与设计/02_开发计划/TASK-005E3_款式利润详情接口鉴权前置整改_工程任务单.md`。详情接口已先执行 `style_profit:read` 动作权限再查询 snapshot，无读权限访问存在/不存在 ID 均返回 403，存在性枚举风险已关闭；进入 TASK-005E4。
- TASK-005E4 款式利润 API 本地仓库基线提交：审计已通过，路径 `/03_需求与设计/02_开发计划/TASK-005E4_款式利润API本地仓库基线提交_工程任务单.md`。当前 HEAD `e8654f9` 已形成 API 权限审计稳定基线；允许进入 TASK-005F 真实服务端来源 Adapter，TASK-006 继续阻塞。
- TASK-005F 款式利润真实服务端来源 Adapter：审计意见书第 103 份不通过，路径 `/03_需求与设计/02_开发计划/TASK-005F_款式利润真实服务端来源Adapter_工程任务单.md`。高危阻断项为 SLE 状态默认 submitted、SLE 仅凭 BOM 白名单入账、外发成本静默空返回；进入 TASK-005F1。
- TASK-005F1 利润 SLE 归属与外发来源阻断整改：审计意见书第 104 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-005F1_利润SLE归属与外发来源阻断整改_工程任务单.md`。SLE 状态 fail closed、SLE BOM+桥接双门禁、外发来源不静默归零已闭环；但外发候选缺可信桥接，进入 TASK-005F2。
- TASK-005F2 外发利润归属桥接字段与补数：审计意见书第 105 份不通过，路径 `/03_需求与设计/02_开发计划/TASK-005F2_外发利润归属桥接字段与补数_工程任务单.md`。阻断项为 selector 带 Work Order 时外发成本仅凭同 SO 同款提前入账；进入 TASK-005F3。
- TASK-005F3 外发 Work Order 严格匹配与补数审计整改：审计意见书第 106 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-005F3_外发WorkOrder严格匹配与补数审计整改_工程任务单.md`。Work Order 严格匹配、profit_scope_status fail closed、inspected_at 口径、补数操作审计已闭环；进入 TASK-005F4。
- TASK-005F4 外发利润查询下推与 PostgreSQL 证据：审计意见书第 107 份不通过，路径 `/03_需求与设计/02_开发计划/TASK-005F4_外发利润查询下推与PostgreSQL证据_工程任务单.md`。查询下推主体通过，但 PostgreSQL hard gate 覆盖了 TASK-002H 外发结算门禁；进入 TASK-005F5。
- TASK-005F5 PostgreSQL 门禁目标恢复与双 JUnit 断言：审计意见书第 108 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-005F5_PostgreSQL门禁目标恢复与双JUnit断言_工程任务单.md`。双门禁脚本已恢复，但 workflow 仍上传旧 `.pytest-postgresql.xml`，且 PostgreSQL 非 skip 证据仍未回填；进入 TASK-005F6。
- TASK-005F6 Workflow 双 JUnit 上传与 PostgreSQL 证据回填：审计意见书第 109 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-005F6_Workflow双JUnit上传与PG证据回填_工程任务单.md`。workflow 双 JUnit 上传、本地门禁和静态测试已闭环，但真实 PostgreSQL 非 skip 实跑证据仍缺失；进入 TASK-005F7。
- TASK-005F7 PostgreSQL 真实非 Skip 证据闭环：审计意见书第 110 份不通过，路径 `/03_需求与设计/02_开发计划/TASK-005F7_PostgreSQL真实非Skip证据闭环_工程任务单.md`。真实 PG 下 settlement 门禁失败，原因是测试迁移链缺 TASK-005F2 外发利润桥接字段，style-profit JUnit 未生成；进入 TASK-005F8。
- TASK-005F8 PostgreSQL 外发 Schema 基线与双门禁复跑：审计意见书第 111 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-005F8_PostgreSQL外发Schema基线与双门禁复跑_工程任务单.md`。外发 PG schema 基线已纳入 TASK-005F2 桥接字段，settlement/style-profit 两份真实 PG JUnit 均 non-skip 通过；进入 TASK-005F9 本地基线提交。
- TASK-005F9 款式利润 F 阶段本地基线提交：审计意见书第 112 份已通过，路径 `/03_需求与设计/02_开发计划/TASK-005F9_款式利润F阶段本地基线提交_工程任务单.md`。本地基线 commit `81c3cfa25acc77b0a57ae00a282fecb8dca81550` 已通过，但 F9 证据文件仍未跟踪；进入 TASK-005F10。
- TASK-005F10 F9 证据 Docs-Only 补提交：审计意见书第 113 份有条件通过，路径 `/03_需求与设计/02_开发计划/TASK-005F10_F9证据DocsOnly补提交_工程任务单.md`。提交范围 docs-only 合格，但 F9 证据正文存在格式损坏和字段缺失；进入 TASK-005F11。
- TASK-005F11 F9 证据格式修正：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005F11_F9证据格式修正_工程任务单.md`。只允许修复 `TASK-005F9_本地基线提交证据.md` 的孤立字符、乱码、命令名、JUnit 文件名和结论字段；不得修改后端、前端、workflow、运行时 JUnit、`02_源码` 或 TASK-006。

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
- TASK-005G 款式利润前端只读联调：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005G_款式利润前端只读联调_工程任务单.md`。前置审计意见书第 114 份，F9/F10/F11 证据链已闭环；本任务只允许实现利润快照列表/详情只读页面、前端 API 封装、路由和 style-profit 前端契约门禁，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005H 款式利润全局只读边界门禁收口：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005H_款式利润全局只读边界门禁收口_工程任务单.md`。前置审计意见书第 115 份，TASK-005G 前端只读联调已通过；本任务只允许扩大 style-profit 契约扫描范围、补全局绕过反向测试和治理内部审计字段展示，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005I 款式利润中文泛化写入口门禁：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005I_款式利润中文泛化写入口门禁_工程任务单.md`。前置审计意见书第 116 份，TASK-005H 全局只读边界门禁已通过；本任务只允许增强中文语义禁线和反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005I1 中文语义白名单绕过整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005I1_中文语义白名单绕过整改_工程任务单.md`。前置审计意见书第 117 份，TASK-005I 存在高危白名单绕过；本任务只允许修复 `shouldIgnoreSemanticMatch()` 与补三条审计复现反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J 款式利润只读说明文案防误杀与门禁基线：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J_款式利润只读说明文案防误杀与门禁基线_工程任务单.md`。前置审计意见书第 118 份，TASK-005I1 已通过；本任务只允许补合法说明文案成功 fixture、交互入口反向测试和门禁基线，不得恢复 substring 白名单，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J1 多行交互上下文门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J1_多行交互上下文门禁整改_工程任务单.md`。前置审计意见书第 119 份，TASK-005J 存在高危多行交互标签绕过；本任务只允许扩展交互上下文跨行识别并补多行反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J2 Action 对象级交互上下文门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J2_Action对象级交互上下文门禁整改_工程任务单.md`。前置审计意见书第 120 份，TASK-005J1 存在高危长 action 配置绕过；本任务只允许升级 action 对象级/block 级检测并补长间隔反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J3 Action 祖先对象链门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J3_Action祖先对象链门禁整改_工程任务单.md`。前置审计意见书第 121 份，TASK-005J2 存在高危父 action + 子 meta label 绕过；本任务只允许升级祖先对象链检测并补嵌套 metadata 反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J4 JSON 风格引号键与真实长距离 Fixture 门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J4_JSON风格引号键与真实长距离Fixture门禁整改_工程任务单.md`。前置审计意见书第 122 份，TASK-005J3 存在高危双引号键绕过且长距离 fixture 证据偏弱；本任务只允许补引号键识别和真实 1200 字符距离反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J5 对象方法简写交互字段门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J5_对象方法简写交互字段门禁整改_工程任务单.md`。前置审计意见书第 123 份，TASK-005J4 存在高危对象方法简写绕过；本任务只允许补 `onClick()/handler()/submit()` 等方法简写识别与反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J6 计算属性键交互字段门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J6_计算属性键交互字段门禁整改_工程任务单.md`。前置审计意见书第 124 份，TASK-005J5 存在高危计算属性键绕过；本任务只允许补 `'[onClick]':`、`["handler"]()`、`['submit']()` 等合法 JS 计算属性键识别与反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J7 非字面量计算属性 Action 键禁用门禁：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J7_非字面量计算属性Action键禁用门禁_工程任务单.md`。前置审计意见书第 125 份，TASK-005J6 已通过但保留非字面量 computed action key 风险；本任务只允许补 `[ACTION_KEY]`、`[actionMap.onClick]`、`[getActionKey()]` 等动态 key 禁用门禁与反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J8 跨行非字面量计算属性 Action 键门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J8_跨行非字面量计算属性Action键门禁整改_工程任务单.md`。前置审计意见书第 126 份，TASK-005J7 存在高危跨行 computed key 绕过；本任务只允许补 `[actionMap\n  .onClick]` 等跨行 `[...]` 捕获与反向测试，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J9 Style Profit 契约门禁 AST 化 Computed Key 收口：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J9_StyleProfit契约门禁AST化ComputedKey收口_工程任务单.md`。前置审计意见书第 127 份，TASK-005J8 存在高危内部方括号 computed key 绕过；本任务要求使用现有 TypeScript compiler API 解析对象成员和 computed key，停止继续叠正则补丁，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J10 Style Profit 动态 Computed Key 全域 Fail Closed 门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J10_StyleProfit动态ComputedKey全域FailClosed门禁整改_工程任务单.md`。前置审计意见书第 128 份，TASK-005J9 存在高危中性容器名绕过；本任务要求 style-profit surface 内 dynamic/unknown computed key 全域 fail closed，不再依赖 actions/menu/button 等容器名，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J11 运行时动态属性注入门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J11_运行时动态属性注入门禁整改_工程任务单.md`。前置审计意见书第 129 份，TASK-005J10 存在高危运行时动态属性注入绕过；本任务要求检测 `item[ACTION_KEY] = ...`、`Object.defineProperty`、`Object.defineProperties`、`Reflect.set`、`Object.assign` 等动态写入路径，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J12 运行时显式 Action Key 注入门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J12_运行时显式ActionKey注入门禁整改_工程任务单.md`。前置审计意见书第 130 份，TASK-005J11 存在高危显式 action key 运行时注入绕过；本任务要求检测 `item['onClick'] = ...`、`item.onClick = ...`、`Object.defineProperty`、`Object.assign`、`Reflect.set` 等显式 action key 注入，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J13 运行时 ActionKey 等价语法门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J13_运行时ActionKey等价语法门禁整改_工程任务单.md`。前置审计意见书第 131 份，TASK-005J12 存在高危等价语法绕过；本任务要求检测 `Object['defineProperty']`、`Reflect['set']`、`Object['assign']`、本地别名调用和 `Object.assign` 变量 source 合并，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J14 解构与命名空间别名门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J14_解构与命名空间别名门禁整改_工程任务单.md`。前置审计意见书第 132 份，TASK-005J13 存在高危解构别名与命名空间别名绕过；本任务要求检测 `const { defineProperty } = Object`、`const { assign } = Object`、`const { set } = Reflect`、`const Obj = Object`、`const R = Reflect` 等别名调用，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J15 Runtime Mutator 高级别名门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J15_RuntimeMutator高级别名门禁整改_工程任务单.md`。前置审计意见书第 133 份，TASK-005J14 存在高危赋值式解构、bind/call/apply、globalThis/window 命名空间绕过；本任务要求按源 API 等价拦截这些 runtime mutator 高级别名，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J16 Runtime Mutator Sink 变体门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J16_RuntimeMutatorSink变体门禁整改_工程任务单.md`。前置审计意见书第 134 份，TASK-005J15 存在高危 Reflect.apply、字符串/计算属性解构、globalThis/window 解构命名空间绕过；本任务要求按源 API 等价拦截这些 runtime mutator sink 变体，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J17 Runtime Mutator 中转调用门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J17_RuntimeMutator中转调用门禁整改_工程任务单.md`。前置审计意见书第 135 份，TASK-005J16 存在高危逗号表达式、条件表达式命名空间、数组/对象容器中转绕过；本任务要求按源 API 等价拦截这些 runtime mutator 中转调用，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J18 Runtime Mutator 源引用禁用门禁收口：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J18_RuntimeMutator源引用禁用门禁收口_工程任务单.md`。前置审计意见书第 136 份，TASK-005J17 存在高危函数返回、IIFE、内联/嵌套/包装/条件容器绕过；本任务要求停止逐语法追踪，改为 style-profit surface 内禁用 runtime mutator 源引用，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J19 动态成员名与源引用隐藏门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J19_动态成员名与源引用隐藏门禁整改_工程任务单.md`。前置审计意见书第 137 份，TASK-005J18 存在高危动态成员名、字符串拼接、globalThis/window 多级 element access、Reflect.get、optional chain 绕过；本任务要求对 Object/Reflect/globalThis/window 的动态成员访问做静态归一或 fail closed，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J20 运行时代码生成入口禁用门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J20_运行时代码生成入口禁用门禁整改_工程任务单.md`。前置审计意见书第 138 份，TASK-005J19 存在高危 eval、Function、new Function、globalThis/window Function/eval 及其别名/间接调用绕过；本任务要求在 style-profit surface 内禁用运行时代码生成入口，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J21 字符串定时器与 Constructor 链禁用门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J21_字符串定时器与Constructor链禁用门禁整改_工程任务单.md`。前置审计意见书第 139 份，TASK-005J20 存在高危字符串 setTimeout/setInterval 与 .constructor/.constructor.constructor 派生 Function 链绕过；本任务要求在 style-profit surface 内禁用字符串 timer 和 constructor 链代码生成入口，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J22 Timer call/apply 等价调用门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J22_TimerCallApply等价调用门禁整改_工程任务单.md`。前置审计意见书第 140 份，TASK-005J21 存在高危 setTimeout/setInterval call/apply 字符串 callback 绕过；本任务要求 timer codegen 接入统一 call descriptor 和参数归一逻辑，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J23 动态模块加载禁用门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J23_动态模块加载禁用门禁整改_工程任务单.md`。前置审计意见书第 141 份，TASK-005J22 存在高危 data/blob 动态 import、变量动态 import、Blob URL module loading 绕过；本任务要求禁用动态模块加载高危入口，仅允许静态本地懒加载 import，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J24 Blob URL 与 Worker 加载门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J24_BlobURL与Worker加载门禁整改_工程任务单.md`。前置审计意见书第 142 份，TASK-005J23 存在高危 URL.createObjectURL call/apply/别名、Blob URL 变量传播、Worker/SharedWorker data/blob/http(s)/未知 URL 绕过；本任务要求收口 Blob URL 与 Worker/script 代码加载入口，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J25 Worker 构造器别名门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J25_Worker构造器别名门禁整改_工程任务单.md`。前置审计意见书第 143 份，TASK-005J24 存在高危 Worker/SharedWorker 构造器别名、命名空间别名、条件别名和容器中转绕过；本任务要求 Worker 构造器识别接入统一 alias/namespace/conditional alias 解析体系并复用同一 URL 校验逻辑，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J26 Worker 等价构造入口门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J26_Worker等价构造入口门禁整改_工程任务单.md`。前置审计意见书第 144 份，TASK-005J25 存在高危 Worker.bind、绑定构造器别名、Reflect.construct 与 Reflect.construct 别名绕过；本任务要求将 Worker 构造 sink 统一为 constructor descriptor 并复用同一 URL 校验逻辑，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J27 动态构造器返回值门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J27_动态构造器返回值门禁整改_工程任务单.md`。前置审计意见书第 145 份，TASK-005J26 存在高危函数返回 Worker/SharedWorker 构造器、IIFE 返回构造器和未知构造目标兜底不一致绕过；本任务要求将 new、Reflect.construct、bind、函数返回和 IIFE 统一收敛到 constructor invocation descriptor，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J28 Unknown Constructor 字符串 URL 严格门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J28_UnknownConstructor字符串URL严格门禁整改_工程任务单.md`。前置审计意见书第 146 份，TASK-005J27 存在高危 unknown constructor 放行普通字符串 Worker URL 绕过；本任务要求 unknown constructor + URL-like 参数 fail closed，并与 known Worker URL 判定同口径，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J29 NewExpression Spread 参数归一化门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J29_NewExpressionSpread参数归一化门禁整改_工程任务单.md`。前置审计意见书第 147 份，TASK-005J28 存在高危 `new unknownCtor(...args)` spread 参数绕过；本任务要求 NewExpression 与 Reflect.construct 复用同一套 invocation arguments descriptor，SpreadElement 必须静态展开或 fail closed，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J30 Spread 数组状态跟踪门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J30_Spread数组状态跟踪门禁整改_工程任务单.md`。前置审计意见书第 148 份，TASK-005J29 存在高危数组字面量缓存未跟踪元素写入、别名写入和 mutating method 绕过；本任务要求 arrayLiteralVariableMap 从值缓存升级为数组状态跟踪，tainted/escaped/unknown 数组必须 fail closed，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J31 函数调用副作用数组污染门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J31_函数调用副作用数组污染门禁整改_工程任务单.md`。前置审计意见书第 149 份，TASK-005J30 存在高危函数声明提升、闭包副作用和无参函数调用导致数组污染顺序误判绕过；本任务要求函数副作用按调用点污染数组，未知函数调用和数组逃逸 conservative fail closed，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J32 解构 Alias 数组状态跟踪门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J32_解构Alias数组状态跟踪门禁整改_工程任务单.md`。前置审计意见书第 150 份，TASK-005J31 存在高危 ArrayBindingPattern/ObjectBindingPattern 解构 alias 未进入数组状态图绕过；本任务要求解构 alias 与原数组共享 array_id，无法静态还原时 fail closed，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J33 循环与参数解构 Alias 门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J33_循环与参数解构Alias门禁整改_工程任务单.md`。前置审计意见书第 151 份，TASK-005J32 仍存在 for...of、函数参数和回调参数解构 alias 未进入数组状态图绕过；本任务要求补齐循环绑定、函数参数、箭头函数参数和回调参数解构 alias 跟踪，无法静态还原时 fail closed，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J34 同步数组迭代方法 Callback Alias 门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J34_同步数组迭代方法CallbackAlias门禁整改_工程任务单.md`。前置审计意见书第 152 份，TASK-005J33 仍存在 `reduce/reduceRight/flatMap/findIndex/findLast/findLastIndex` 同步 callback 参数解构 alias 未进入数组状态图绕过；本任务要求同步数组迭代方法从简单白名单升级为 method descriptor map，按方法映射 current item 参数位，无法静态还原时 fail closed，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J35 同步数组迭代方法等价调用门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J35_同步数组迭代方法等价调用门禁整改_工程任务单.md`。前置审计意见书第 153 份，TASK-005J34 仍存在 `Array.prototype.reduce.call/apply`、`Reflect.apply(Array.prototype.reduce, ...)` 等价调用未进入 method descriptor 路径绕过；本任务要求 direct call、call、apply、Reflect.apply 统一还原为数组迭代调用 descriptor，无法静态还原时 fail closed，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J36 同步数组迭代方法 Bind 与 CallCall 门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J36_同步数组迭代方法Bind与CallCall门禁整改_工程任务单.md`。前置审计意见书第 154 份，TASK-005J35 仍存在 `Array.prototype.reduce.bind(...)` 预绑定和 `Function.prototype.call.call(...)` / `Array.prototype.reduce.call.call(...)` 中转未进入 iteration descriptor 绕过；本任务要求 direct/call/apply/Reflect.apply/bind/call.call 统一进入 IterationInvocationDescriptor，无法静态还原时 fail closed，不得开放创建快照入口，不得进入 TASK-006。
- TASK-005J37 J36 最小范围本地基线提交：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005J37_J36最小范围本地基线提交_工程任务单.md`。前置审计意见书第 155 份，TASK-005J36 已通过但改动仍在工作区；本任务只允许提交 3 个白名单文件：`check-style-profit-contracts.mjs`、`test-style-profit-contracts.mjs`、`TASK-005J36_同步数组迭代方法Bind与CallCall门禁整改证据.md`，禁止提交 `App.vue`、后端、workflow、审计记录、TASK-006 或运行生成物；TASK-006 继续阻塞。
- TASK-005K 款式利润模块封版盘点：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点_工程任务单.md`。前置审计意见书第 156 份，TASK-005J37 已通过且提交 `f0fc6c92e46354eeb44add119267359ea919a74e` 可作为当前本地基线；本任务只允许输出封版盘点证据文档，汇总 TASK-005 全链路证据并判断是否建议进入本地封版复审，不得修改前后端业务代码，不得开放创建快照入口，TASK-006 继续阻塞。
- TASK-005K1 K 证据本地基线提交：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005K1_K证据本地基线提交_工程任务单.md`。前置审计意见书第 157 份，TASK-005K 已通过且可进入 TASK-005 本地封版复审；但 K 证据文件仍未跟踪。本任务只允许提交 `/03_需求与设计/02_开发计划/TASK-005K_款式利润模块封版盘点证据.md`，禁止提交前端、后端、workflow、审计记录、运行产物、历史未跟踪目录或 TASK-006；TASK-006 继续阻塞。
- TASK-005L TASK-005 本地封版复审：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005L_TASK-005本地封版复审_工程任务单.md`。前置审计意见书第 158 份，TASK-005K1 已通过，K 证据已纳入本地基线 commit `1da795333d20ed8ecfb2308da623358668272458`；本任务只允许输出本地封版复审证据，核验 TASK-005 全链路是否可标记为本地封版完成，不得修改前端、后端、workflow、迁移、TASK-006 或运行产物；TASK-006 继续阻塞。
- TASK-005L1 TASK-005 本地封版复审证据审计：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-005L1_TASK-005本地封版复审证据审计_任务单.md`。TASK-005L 工程侧已输出封版复审证据并建议 TASK-005 标记为本地封版完成；本任务要求审计官复核 L 证据、Git 基线、前端门禁、后端回归、PostgreSQL 证据披露、禁改范围和 TASK-006 阻塞状态。审计通过后才允许架构师输出 TASK-005 本地封版完成记录；TASK-006 继续阻塞。
- TASK-006A 加工厂对账单开发前基线盘点与设计冻结：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006A_加工厂对账单开发前基线盘点与设计冻结_工程任务单.md`。前置状态：TASK-005 已允许标记为本地封版完成，TASK-002 外发加工管理已完成；本任务只允许盘点 TASK-002 对账出口、冻结对账来源粒度、金额公式、幂等、权限审计和 ERPNext 应付边界。不得修改后端、前端、迁移、workflow 或 `02_源码`，不得直接创建 ERPNext `Purchase Invoice`，通过审计后才允许进入 TASK-006B。
- TASK-006B 加工厂对账单后端模型迁移与草稿 API：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006B_加工厂对账单后端模型迁移与草稿API_工程任务单.md`。前置审计意见书第 161 份，TASK-006A 已通过；本任务只允许实现本地模型、迁移、草稿生成、列表、详情、权限审计和测试。确认、取消、调整、ERPNext `Purchase Invoice`、前端页面继续冻结到后续任务。
- TASK-006B1 对账草稿重复防护与取消后重建约束整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006B1_对账草稿重复防护与取消后重建约束整改_工程任务单.md`。前置状态：TASK-006B 审计不通过；本任务只允许修复同范围 active-scope 重复防护和 `inspection_id` 无条件唯一约束问题。不得进入 TASK-006C，不得实现确认、取消、调整、ERPNext `Purchase Invoice`、前端页面。
- TASK-006C 对账确认取消与 Active Scope 冲突语义收口：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006C_对账确认取消与ActiveScope冲突语义收口_工程任务单.md`。前置状态：TASK-006B1 审计通过；本任务只允许实现本地 confirm/cancel 状态机、取消释放来源 inspection、幂等 operation 和 active-scope 业务冲突错误码。ERPNext `Purchase Invoice`、`payable-draft`、前端页面、打印页面继续冻结。
- TASK-006C1 Create 路由未知异常兜底修复：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006C1_Create路由未知异常兜底修复_工程任务单.md`。前置状态：TASK-006C 审计不通过；本任务只允许修复 `POST /api/factory-statements/` 未知异常兜底中 `statement_id` 未定义导致二次 `NameError` 的问题，并补防回归测试。不得进入 TASK-006D，不得实现 ERPNext `Purchase Invoice`、`payable-draft` 或前端页面。
- TASK-006D ERPNext 应付草稿 Outbox 集成：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006D_ERPNext应付草稿Outbox集成_工程任务单.md`。前置状态：TASK-006C1 审计通过；本任务只允许实现 confirmed statement 创建本地 payable outbox、内部 worker 创建 ERPNext Purchase Invoice 草稿、幂等、权限、审计、错误信封和测试。前端页面、打印页面、Purchase Invoice 提交、Payment Entry、GL Entry 继续冻结。
- TASK-006D1 Worker/Outbox 状态机安全整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006D1_WorkerOutbox状态机安全整改_工程任务单.md`。前置状态：TASK-006D 审计不通过；本任务只允许修复 payable outbox 创建后仍可 cancel、worker 调 ERPNext 前未校验本地 statement 状态、claim_due 可抢占未过期 lease 三类问题。不得进入 TASK-006E，不得修改前端，不得提交 Purchase Invoice、创建 Payment Entry 或 GL Entry。
- TASK-006E 加工厂对账单前端联调与契约门禁：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006E_加工厂对账单前端联调与契约门禁_工程任务单.md`。前置状态：TASK-006D1 审计通过；本任务只允许实现前端 API、列表页、详情页、权限按钮、payable-draft outbox 创建入口和前端契约门禁。不得调用 internal worker，不得直连 ERPNext，不得提交 Purchase Invoice，不得创建 Payment Entry/GL Entry，不得修改后端、.github、02_源码。
- TASK-006E1 前后端契约补齐与 Payable 摘要门禁整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006E1_前后端契约补齐与Payable摘要门禁整改_工程任务单.md`。前置状态：TASK-006E 审计不通过；本任务只允许修复创建对账单缺 `company`、后端 list/detail 缺 payable outbox 摘要、前端按钮基于缺失字段乐观放行的问题。不得调用 internal worker，不得直连 ERPNext，不得提交 Purchase Invoice，不得创建 Payment Entry/GL Entry，不得进入 TASK-006F。
- TASK-006E2 Payable Draft 同 Statement Active Outbox 防重整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006E2_PayableDraft同StatementActiveOutbox防重整改_工程任务单.md`。前置状态：TASK-006E1 审计不通过；本任务只允许修复同一 confirmed statement 可用不同 idempotency_key 创建多条 active payable outbox 的问题，要求 event_key 不含 idempotency_key，并补并发/唯一冲突防重测试。不得进入 TASK-006F，不得调用 internal worker，不得提交 Purchase Invoice，不得创建 Payment Entry/GL Entry。
- TASK-006F 打印导出与封版前证据盘点：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006F_打印导出与封版前证据盘点_工程任务单.md`。前置状态：TASK-006E2 审计通过；本任务只允许实现加工厂对账单打印友好视图、当前详情快照 CSV 导出、前端契约门禁补强和封版前证据盘点。不得新增后端财务口径，不得调用 internal worker，不得直连 ERPNext，不得提交 Purchase Invoice，不得创建 Payment Entry/GL Entry，不得进入 TASK-006G。
- TASK-006F1 CSV 公式注入防护整改：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006F1_CSV公式注入防护整改_工程任务单.md`。前置状态：TASK-006F 审计不通过；本任务只允许修复 CSV 导出公式注入防护和 factory-statement contract 反向测试，要求所有 CSV 单元格对 `= + - @ tab CR LF` 等危险前缀前置安全单引号。不得修改后端、不得新增导出接口、不得进入 TASK-006G。
- TASK-006G 加工厂对账单本地封版复审：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006G_加工厂对账单本地封版复审_工程任务单.md`。前置状态：TASK-006F1 审计通过；本任务只允许输出本地封版复审证据，汇总 TASK-006A~F1 任务链路、审计闭环、测试结果、禁止能力扫描和剩余风险。不得新增功能，不得修改前端/后端业务代码、.github、02_源码，不得提交运行产物，不得自行宣布封版通过。
- TASK-006H 加工厂对账单本地封版审计：任务单已下发，路径 `/03_需求与设计/02_开发计划/TASK-006H_加工厂对账单本地封版审计_任务单.md`。前置状态：TASK-006G 审计通过；本任务为审计任务，只允许复核 TASK-006A~G 全链路证据、测试结果、禁止能力扫描和剩余风险。不得新增功能，不得修改前端/后端业务代码、.github、02_源码；审计通过后才允许架构师记录 TASK-006 本地封版完成。
- TASK-006 本地封版完成：审计意见书第 173 份已通过，允许架构师记录 TASK-006 本地封版完成。该状态仅表示本地仓库、本地测试和本地证据链封版完成，不代表生产发布、ERPNext 生产联调或平台 required check 闭环。保留风险包括 `datetime.utcnow()` warnings、failed/dead payable outbox 重建策略未实现、工作区历史 diff/运行产物需白名单治理。

## TASK-REL-001 本地封版后白名单提交与运行产物清理

- 状态：已下发任务单
- 优先级：P0
- 前置依赖：TASK-005 本地封版完成、TASK-006 本地封版完成
- 任务单路径：/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-001_本地封版后白名单提交与运行产物清理_工程任务单.md
- 目标：固定本地封版后的仓库基线，清理或隔离运行产物，禁止非白名单暂存，避免历史 diff、缓存、构建产物、JUnit 运行产物混入提交。
- 边界：本任务不代表生产发布，不配置 remote，不 push，不创建 PR，不声明平台 required check 闭环。

## TASK-REL-002 本地封版白名单基线提交

- 状态：已下发任务单
- 优先级：P0
- 前置依赖：TASK-REL-001 已完成，TASK-005/TASK-006 已记录本地封版完成
- 任务单路径：/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-REL-002_本地封版白名单基线提交_工程任务单.md
- 目标：按严格白名单逐文件暂存并建立本地封版基线 commit。提交前必须回显 staged 清单并等待确认；禁止 `git add .` / `git add -A`；不 push、不配置 remote、不声明生产发布完成。

## TASK-007 权限与审计统一基座

- 状态：已下发任务单
- 优先级：P1
- 前置依赖：Sprint2_架构规范.md 已审计确认
- 设计文档：/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-007_权限与审计统一基座设计.md
- 工程任务单：/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-007_权限与审计统一基座_工程任务单.md
- 边界：只输出设计文档和任务单，不写业务代码；审计通过后才允许拆分 TASK-007B 进入实现。

════════════════════════════════════════════════════════════════════════════

## Sprint 2 补充状态（2026-04-16）

- TASK-007：文档层已审计通过。
- TASK-007B：已下发（权限与审计统一基座工程实现第一阶段），当前状态为待工程实现、待审计。
- 门禁：TASK-007B 审计通过前，不得进入 TASK-007C；TASK-007~010 基座未全通过前，不得进入 TASK-011/TASK-012。
