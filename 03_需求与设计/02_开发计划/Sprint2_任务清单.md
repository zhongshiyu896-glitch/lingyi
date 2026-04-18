# Sprint 2 任务清单草稿

- 版本：V0.1
- 更新时间：2026-04-16 08:26
- 作者：技术架构师
- 输入依据：Sprint 1 审计记录、`Sprint1_复盘报告.md`、`Sprint2_架构规范.md`
- 状态：草稿，需审计后才能派发工程实现

## 一、Sprint 2 总目标

Sprint 2 不直接扩散功能，而是先把 Sprint 1 暴露出的共性风险收口为公共基座，再进入 P1 模块。核心目标：

1. 统一权限、审计、ERPNext fail-closed、outbox、前端写入口门禁。
2. 将 TASK-S-002 从主路径 smoke 扩展为高危路径验收工具。
3. 启动 P1 模块：销售管理、库存管理、质量管理、权限治理、仪表盘/首页。
4. 所有任务先过任务单审计，再写代码。

## 二、任务依赖总览

| 任务 | 模块 | 优先级 | 前置依赖 | 是否允许直接实现 |
| --- | --- | --- | --- | --- |
| TASK-007 | 权限与审计统一基座 | P1 | Sprint2 架构规范审计通过 | 否，先任务单审计 |
| TASK-008 | ERPNext 集成 Fail-Closed Adapter | P1 | TASK-007 任务单审计通过 | 否，先任务单审计 |
| TASK-009 | Outbox 公共状态机规范与模板 | P1 | TASK-007、TASK-008 任务单审计通过 | 否，先任务单审计 |
| TASK-010 | 前端写入口门禁公共框架 | P1 | TASK-007 任务单审计通过 | 否，先任务单审计 |
| TASK-011 | 销售/库存只读集成 | P1 | TASK-007~010 至少设计冻结 | 否，先任务单审计 |
| TASK-012 | 质量管理基线 | P1 | TASK-007~010 至少设计冻结，TASK-002/TASK-006 本地封版完成 | 否，先任务单审计 |

## 三、TASK-007 权限与审计统一基座

════════════════════════════════════════════════════════════
【任务卡】TASK-007
模块：权限与审计统一基座
优先级：P1
════════════════════════════════════════════════════════════

【任务目标】
统一后端动作权限、资源权限、安全审计、操作审计和错误信封，为 Sprint 2 所有 P1 模块提供公共权限基线。

【任务范围】
1. 梳理现有 `permission_service`、`permissions.py`、安全审计、操作审计实现。
2. 输出统一权限动作命名规范：`module:action`。
3. 输出资源权限字段规范：`company/item_code/supplier/warehouse/work_order/sales_order`。
4. 输出安全审计事件规范：401、403、资源越权、权限源不可用、internal API 访问。
5. 输出操作审计规范：create/update/confirm/cancel/export/dry-run/diagnostic。

【涉及文件】
- 新建：`03_需求与设计/01_架构设计/TASK-007_权限与审计统一基座设计.md`
- 新建：`03_需求与设计/02_开发计划/TASK-007_权限与审计统一基座_工程任务单.md`
- 可能修改：`03_需求与设计/01_架构设计/Sprint2_架构规范.md`

【前置审计要求】
1. 任务单必须列出所有权限动作命名。
2. 必须明确开发环境 static role 与生产 ERPNext/Auth 聚合权限源边界。
3. 必须明确权限源不可用 fail-closed 错误码。
4. 必须明确安全审计不得记录 Authorization/Cookie/Token/Secret/密码。
5. 审计通过后才能进入代码实现。

【验收标准】
□ 权限动作命名表完成。
□ 资源权限字段表完成。
□ 安全审计/操作审计事件表完成。
□ fail-closed 错误码表完成。
□ 已列出 TASK-001~006 中需要回迁公共规范的点。

【预计工时】1-2 天

## 四、TASK-008 ERPNext 集成 Fail-Closed Adapter

════════════════════════════════════════════════════════════
【任务卡】TASK-008
模块：ERPNext 集成 Fail-Closed Adapter
优先级：P1
════════════════════════════════════════════════════════════

【任务目标】
为 Supplier、Account、Item、Sales Order、Stock Ledger Entry、Work Order、Job Card、Purchase Invoice 等 ERPNext 能力提供统一 fail-closed 集成规范和 adapter 任务单。

【任务范围】
1. 冻结 ERPNext REST API 调用规范。
2. 冻结 docstatus/status 校验规则。
3. 冻结外部服务不可用、404、空结果、权限失败的错误语义。
4. 冻结 ERPNext 查询日志脱敏规则。
5. 冻结生产环境禁止 static 权限源策略。

【涉及文件】
- 新建：`03_需求与设计/01_架构设计/TASK-008_ERPNext集成FailClosed规范.md`
- 新建：`03_需求与设计/02_开发计划/TASK-008_ERPNext集成FailClosedAdapter_工程任务单.md`

【前置审计要求】
1. 必须覆盖 Supplier/Account/Cost Center/Item/SLE/Work Order/Job Card/Purchase Invoice/User Permission。
2. 必须明确“查询失败”和“明确无数据”的区别。
3. 必须明确 docstatus 缺失默认 fail closed。
4. 必须列出 TASK-002/TASK-003/TASK-004/TASK-005/TASK-006 中已出现过的 ERPNext 风险。

【验收标准】
□ ERPNext 能力清单完成。
□ 统一错误码完成。
□ docstatus/status 校验矩阵完成。
□ fail-closed 测试矩阵完成。
□ 审计通过后才能进入代码实现。

【预计工时】1-2 天

## 五、TASK-009 Outbox 公共状态机规范与模板

════════════════════════════════════════════════════════════
【任务卡】TASK-009
模块：Outbox 公共状态机规范与模板
优先级：P1
════════════════════════════════════════════════════════════

【任务目标】
把 TASK-002、TASK-003、TASK-004、TASK-006 中反复出现的 outbox 风险收口为公共规范，形成统一字段、状态迁移、claim、retry、dry-run、diagnostic、审计和测试模板。

【任务范围】
1. 输出 outbox 标准字段表。
2. 输出 event_key 组成规则。
3. 输出 claim_due 原子更新规则。
4. 输出 worker 调 ERPNext 前置校验规则。
5. 输出 active outbox 防重规则。
6. 输出 PostgreSQL 并发测试要求。

【涉及文件】
- 新建：`03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md`
- 新建：`03_需求与设计/02_开发计划/TASK-009_Outbox公共状态机模板_工程任务单.md`

【前置审计要求】
1. 必须引用第 19/22/39/41/51/65/168 份等 outbox 相关审计问题。
2. 必须明确 event_key 不含易变字段。
3. 必须明确 claim 第二阶段重复校验 due/lease。
4. 必须明确 aggregate cancelled 不得调用 ERPNext。
5. 必须明确 dry-run/diagnostic 审计要求。

【验收标准】
□ outbox 状态机图完成。
□ 标准字段表完成。
□ event_key 规则完成。
□ claim/lease 规则完成。
□ worker 前置校验完成。
□ 必测矩阵完成。

【预计工时】1-2 天

## 六、TASK-010 前端写入口门禁公共框架

════════════════════════════════════════════════════════════
【任务卡】TASK-010
模块：前端写入口门禁公共框架
优先级：P1
════════════════════════════════════════════════════════════

【任务目标】
将 style-profit 与 factory-statement 的契约门禁经验抽象为通用前端写入口门禁框架，避免 Sprint 2 各模块重复补丁式审计。

【任务范围】
1. 设计模块门禁声明格式。
2. 统一 API 方法白名单、HTTP 方法白名单、路由扫描、权限动作扫描。
3. 统一 AST 检测规则：action key、runtime mutator、codegen、timer、dynamic import、Worker、CSV/XLSX 注入。
4. 统一正向/反向 fixture 格式。
5. 统一 `npm run verify` 接入规范。

【涉及文件】
- 新建：`03_需求与设计/01_架构设计/TASK-010_前端写入口门禁公共框架.md`
- 新建：`03_需求与设计/02_开发计划/TASK-010_前端写入口门禁公共框架_工程任务单.md`

【前置审计要求】
1. 必须复盘 TASK-005J1~J37 的绕过链路。
2. 必须明确正则不得作为唯一门禁。
3. 必须明确动态行为无法静态证明安全时 fail closed。
4. 必须列出每个新模块必须提供的 fixture 类型。

【验收标准】
□ 通用门禁声明格式完成。
□ 通用禁止项清单完成。
□ AST 检测范围完成。
□ fixture 模板完成。
□ verify 接入规则完成。

【预计工时】2-3 天

## 七、TASK-011 销售/库存只读集成

════════════════════════════════════════════════════════════
【任务卡】TASK-011
模块：销售/库存只读集成
优先级：P1
════════════════════════════════════════════════════════════

【任务目标】
基于 ERPNext Sales Order、Delivery Note、Stock Ledger Entry，提供销售与库存只读看板/查询能力，先不实现写入与财务动作。

【任务范围】
1. 设计销售订单只读查询接口。
2. 设计库存台账只读查询接口。
3. 设计库存异常提示：缺料、负库存、跨仓差异。
4. 设计前端只读页面契约。
5. 不创建/修改 ERPNext SO/DN/SLE。

【涉及文件】
- 新建：`03_需求与设计/01_架构设计/TASK-011_销售库存只读集成设计.md`
- 新建：`03_需求与设计/02_开发计划/TASK-011_销售库存只读集成_工程任务单.md`

【前置审计要求】
1. 必须引用 TASK-008 ERPNext fail-closed 规范。
2. 必须引用 TASK-010 前端写入口门禁规范。
3. 必须明确只读接口不得调用 ERPNext 写接口。
4. 必须明确 SLE 缺 `docstatus/status` 或来源不可用时的 fail-closed 策略。
5. 必须明确分页、筛选、权限字段。

【验收标准】
□ SO/DN/SLE 只读边界冻结。
□ API DTO 设计完成。
□ 前端只读契约完成。
□ 权限动作和资源权限完成。
□ 审计通过后才能实现。

【预计工时】3-5 天

## 八、TASK-012 质量管理基线

════════════════════════════════════════════════════════════
【任务卡】TASK-012
模块：质量管理基线
优先级：P1
════════════════════════════════════════════════════════════

【任务目标】
建立质量管理的基础模型与流程设计，覆盖来料检验、外发回料检验、成品检验和扣款/返工联动，但先冻结设计，不直接进入完整实现。

【任务范围】
1. 设计质量检验单模型。
2. 设计检验明细：合格、不合格、返工、报废、扣款。
3. 设计与外发验货、加工厂对账、库存入库的边界。
4. 设计权限与审计。
5. 设计前端页面和只读/写入门禁。

【涉及文件】
- 新建：`03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md`
- 新建：`03_需求与设计/02_开发计划/TASK-012_质量管理基线_工程任务单.md`

【前置审计要求】
1. 必须明确哪些质量数据来自外发验货，哪些由质量模块自建。
2. 必须明确对账单确认后质量/扣款事实不得被直接修改。
3. 必须引用 TASK-009 outbox 规范，若涉及库存/ERPNext 写入必须后续单独任务。
4. 必须引用 TASK-010 前端写入口门禁规范。
5. 必须明确质量数据与款式利润、加工厂对账的引用关系。

【验收标准】
□ 质量模型设计完成。
□ 与外发/对账/库存/利润边界完成。
□ 状态机完成。
□ 权限与审计完成。
□ 前端契约完成。
□ 审计通过后才能实现。

【预计工时】3-5 天

## 九、Sprint 2 验收门槛

1. 每个任务必须先有任务单审计意见。
2. 每个实现任务必须有交付证据。
3. 每个模块必须跑本地定向测试和 `py_compile`。
4. 前端模块必须跑 `npm run verify` 和模块 contract 反向测试。
5. 涉及 PostgreSQL 并发的任务必须提供 non-skip 证据，或明确本地封版限制。
6. 涉及 ERPNext 写入的任务必须走 outbox，不允许事务内直写。
7. 任何生产发布、remote、push、PR、required check 均必须单独任务单。

## 十、禁止自动推进清单

以下事项不得由 Sprint 2 任一任务自动解锁：

1. 生产发布。
2. GitHub required check 平台闭环。
3. ERPNext 生产联调完成。
4. Purchase Invoice submit。
5. Payment Entry / GL Entry 创建。
6. 前端 internal worker 入口。
7. failed/dead outbox 重建策略。
8. 权限源 static role 生产化。

## 十一、子任务拆分与串行审计门禁（2026-04-16）

说明：以下为 Sprint 2 执行级子任务拆分。每个子任务都必须先审计通过，再进入下一个子任务；阶段一基座未全部通过前，不进入阶段二 P1 业务模块。

### 11.1 阶段一：公共基座

| 主任务 | 子任务编号 | 子任务目标 | 前置门禁 | 下一步门禁 |
| --- | --- | --- | --- | --- |
| TASK-007 | TASK-007B | 权限动作注册、fail-closed 错误信封、安全审计事件统一落地 | TASK-007 文档审计通过 | TASK-007B 审计通过后进入 TASK-007C |
| TASK-007 | TASK-007C | 资源权限字段统一校验与模块接入（company/item_code/supplier/warehouse/work_order/sales_order/bom_id） | TASK-007B 审计通过 | TASK-007C 审计通过后进入 TASK-007D |
| TASK-007 | TASK-007D | 操作审计统一事件与回迁清单落地、兼容性回归封版 | TASK-007C 审计通过 | TASK-007D 审计通过后 TASK-007 完成 |
| TASK-008 | TASK-008A | ERPNext fail-closed adapter 接口定义与错误语义冻结 | TASK-007D 审计通过 | TASK-008A 审计通过后进入 TASK-008B |
| TASK-008 | TASK-008B | Supplier/Account/Cost Center/Item 读校验适配器实现 | TASK-008A 审计通过 | TASK-008B 审计通过后进入 TASK-008C |
| TASK-008 | TASK-008C | SLE/Work Order/Job Card/Purchase Invoice docstatus 与外部不可用收口 | TASK-008B 审计通过 | TASK-008C 审计通过后 TASK-008 完成 |
| TASK-009 | TASK-009A | Outbox 标准字段、event_key、active 防重规范落地模板 | TASK-008C 审计通过 | TASK-009A 审计通过后进入 TASK-009B |
| TASK-009 | TASK-009B | claim_due 原子条件、lease 安全、worker 前置校验模板实现 | TASK-009A 审计通过 | TASK-009B 审计通过后进入 TASK-009C |
| TASK-009 | TASK-009C | dry-run/diagnostic/审计模板与并发回归矩阵封版 | TASK-009B 审计通过 | TASK-009C 审计通过后 TASK-009 完成 |
| TASK-010 | TASK-010A | 前端写入口门禁声明格式与扫描范围模板落地 | TASK-009C 审计通过 | TASK-010A 审计通过后进入 TASK-010B |
| TASK-010 | TASK-010B | AST 检测主规则（action key/runtime mutator/codegen/timer/import/Worker）公共化 | TASK-010A 审计通过 | TASK-010B 审计通过后进入 TASK-010C |
| TASK-010 | TASK-010C | 模块反向 fixture 模板与 verify 全量接入封版 | TASK-010B 审计通过 | TASK-010C 审计通过后 TASK-010 完成 |

### 11.2 阶段二：P1 业务模块（阶段一全部通过后）

| 主任务 | 子任务编号 | 子任务目标 | 前置门禁 |
| --- | --- | --- | --- |
| TASK-011 | TASK-011A | 销售/库存只读接口设计冻结与权限动作落地 | TASK-007~010 全部审计通过 |
| TASK-011 | TASK-011B | 销售/库存只读后端实现与 fail-closed 回归 | TASK-011A 审计通过 |
| TASK-011 | TASK-011C | 前端只读联调与契约门禁接入 | TASK-011B 审计通过 |
| TASK-012 | TASK-012A | 质量管理模型与边界冻结（外发/对账/库存/利润） | TASK-007~010 全部审计通过 |
| TASK-012 | TASK-012B | 质量管理基线后端实现（不含支付与财务写入） | TASK-012A 审计通过 |
| TASK-012 | TASK-012C | 前端基线联调、门禁和审计证据封版 | TASK-012B 审计通过 |

### 11.3 当前执行入口

- 当前执行子任务：`TASK-007B`
- 串行规则：`TASK-007B` 审计通过后才允许下发 `TASK-007C`
- 阶段边界：基座阶段（TASK-007~010）未全通过前，禁止启动 `TASK-011` 和 `TASK-012`
