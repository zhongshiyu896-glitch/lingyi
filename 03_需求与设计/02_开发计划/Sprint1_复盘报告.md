# Sprint 1 复盘报告

- 报告版本：V1.0
- 更新时间：2026-04-16 08:26
- 作者：技术架构师
- 输入依据：`03_需求与设计/05_审计记录.md`、`03_需求与设计/05_审计记录/审计官会话日志.md`、`03_需求与设计/02_开发计划/当前 sprint 任务清单.md`、`03_需求与设计/06_交付与验收/TASK-S-002/`
- 复盘范围：TASK-001 ~ TASK-006、TASK-004C 系列、TASK-005 系列、TASK-S-002
- 结论口径：仅复盘 Sprint 1 本地封版链路；不代表生产发布、GitHub required check、ERPNext 生产联调完成。

## 一、总体结论

Sprint 1 已完成 P0 主链路的本地封版：BOM、外发加工、车间工票、生产计划集成、款式利润报表、加工厂对账单均已形成可审计的本地证据链。审计记录显示，主要功能最终都能收敛，但审计轮次明显偏高，尤其是款式利润前端只读门禁与多个 outbox 状态机问题，说明 Sprint 1 的架构规范在三个方面前置不足：

1. 前端写入口门禁没有通用方案，导致 style-profit 从正则扫描一路补丁式演进到 AST 与运行时代码生成禁线。
2. ERPNext 集成 fail-closed 策略分散落在各模块，权限源、主数据源、docstatus 校验、外部服务不可用处理多次重复返工。
3. Outbox 状态机没有统一模板，event_key、claim、lease、retry、dry-run、诊断、active 防重在 TASK-002、TASK-003、TASK-006 中反复出现同类缺口。

Sprint 2 必须先收口公共架构规范，再派发 P1 模块，否则审计会继续在相同风险面上消耗轮次。

## 二、审计效率分析

### 2.1 审计轮次统计

| 模块 | 审计意见书范围 | 轮次 | 首次关键阻断 | 最终结论 | 主要审计消耗点 |
| --- | --- | ---: | --- | --- | --- |
| TASK-001 BOM 管理 | 第 3 ~ 14 份 | 12 | BOM 契约不一致、写/读鉴权缺失、权限源 fail-open | 通过 | 权限、资源级鉴权、审计日志、异常分类、request_id 脱敏 |
| TASK-002 外发加工管理 | 第 33 ~ 61 份 | 29 | 幂等契约缺失、旧演示路径残留、迁移不自洽、outbox/retry/docstatus/结算并发 | 通过 | Stock Entry outbox、验货幂等、结算锁定、PostgreSQL 并发门禁 |
| TASK-003 工票/车间管理 | 第 15 ~ 32 份 | 18 | 工票/工价资源权限缺口、批量异常吞错、Job Card 同步事务内调用 | 通过 | 资源权限、service account 最小权限、outbox worker、历史工价补数 |
| TASK-004 生产计划集成 | 第 62 ~ 79 份、第 83 份 | 19 | material-check/create-work-order 契约缺字段、前端 planned_start_date 漂移、CI 平台闭环阻塞 | 通过 | 前端契约门禁、Git 仓库根、平台 required check 改为本地门禁替代 |
| TASK-005 款式利润报表 | 第 80 ~ 159 份 | 80 | 利润口径旧公式、来源映射 fail-open、真实来源归属、前端只读门禁大量绕过 | 通过 | source_map 审计追溯、SLE/外发归属、PostgreSQL 门禁、style-profit 只读写入口门禁 |
| TASK-S-002 验收工具包 | 会话日志第 160 份 | 1 | 无高危阻断 | 通过 | 13 个接口冒烟工具、报告与退出码规则 |
| TASK-006 加工厂对账单 | 第 161 ~ 173 份 | 13 | active-scope 防重、取消后重建、payable outbox 状态机、前后端契约、CSV 公式注入 | 通过 | 对账来源粒度、payable outbox active 防重、前端按钮 fail-closed、导出安全 |

说明：上表按审计意见书编号和审计官会话日志统计。TASK-005 的 80 轮中，TASK-005J 前端只读门禁链路占比最高，是 Sprint 1 最大审计消耗来源。

### 2.2 高危问题来源分类

| 来源分类 | 典型任务 | 典型问题 | 是否应前置到架构设计 |
| --- | --- | --- | --- |
| 架构设计遗漏 | TASK-001、TASK-004、TASK-005、TASK-006 | 表/路由契约不一致；`planned_start_date` 事实字段未定义；利润来源默认是否纳入未冻结；对账单 `company` 与 payable 摘要字段未前置定义 | 是。应在任务单阶段冻结 DTO、表字段、状态机、默认值、索引和响应字段。 |
| 实现偏差 | TASK-001、TASK-002、TASK-003、TASK-006 | `operator="system"`、旧 demo 成功路径、旧净额公式、回料/验货越过任务边界、service 内 commit、前端缺必填字段 | 是。应在任务卡中列“禁入实现”和“旧代码禁复用路径”。 |
| 边界条件未覆盖 | TASK-002、TASK-003、TASK-005、TASK-006 | 幂等 hash 缺关键字段；event_key 截断碰撞；stale claim 抢占 lease；cancel 后 worker 仍调 ERPNext；company NULL/空字符串历史脏数据 | 是。应统一 idempotency、event_key、claim/lease、fail-closed、历史数据补数规范。 |
| 前端绕过 | TASK-004C、TASK-005J、TASK-006E/F | 内部 worker 入口暴露；style-profit 写入口通过动态 key、runtime mutator、Worker、动态 import 绕过；CSV 公式注入 | 是。应建立通用 AST 门禁与反向 fixture，不再每个模块临时补正则。 |
| 平台/环境门禁 | TASK-002H、TASK-004C、TASK-005F | PostgreSQL 非 skip 证据、workflow JUnit 路径、仓库根策略、required check 无远端条件 | 部分是。应区分“本地封版”与“平台闭环”，任务单不得把平台动作作为默认前置。 |

### 2.3 本应在架构设计阶段消除的问题

1. API/DTO 契约：`company`、`planned_start_date`、`warehouse/fg_warehouse/wip_warehouse/start_date`、payable outbox 摘要等字段应在任务卡阶段冻结。
2. 业务唯一性：默认 BOM 唯一、外发幂等键、statement active-scope、payable active outbox 等唯一策略应在模型设计中同步定义索引和冲突错误码。
3. Outbox 状态机：event_key 组成、claim_due 原子条件、docstatus 校验、cancel 前置拦截、dry-run 审计、retry 目标选择应进入通用规范。
4. ERPNext fail-closed：Supplier/Account/Item/SLE/Work Order/Purchase Invoice 查询失败必须统一返回外部服务不可用，不得伪装成“无数据”。
5. 前端写入口门禁：只读模块不得靠页面自觉，必须统一 AST 扫描、反向 fixture、API 方法白名单、路由/权限动作双门禁。
6. 审计证据链：任务单应先规定交付证据模板、禁止提交清单、白名单暂存规则，避免封版后再补 REL 任务。

## 三、技术债务与重复风险

### 3.1 ERPNext 集成 fail-closed 一致性

| 模块 | 已出现的 ERPNext 风险 | 当前状态 | Sprint 2 要求 |
| --- | --- | --- | --- |
| TASK-001 BOM | User Permission 查询失败曾 fail-open | 已改为 `503 + PERMISSION_SOURCE_UNAVAILABLE` | 权限源不可用必须统一 fail-closed。 |
| TASK-002 外发 | Stock Entry 草稿/docstatus 判断、Supplier/Item/Company 归属 | 已收口 docstatus 和 outbox | 所有 ERPNext doc 必须校验 `docstatus`，草稿不得视为成功。 |
| TASK-003 工票 | Job Card 同步曾在本地事务内调用 ERPNext | 已改 outbox/worker | 本地事务提交前不得调用 ERPNext。 |
| TASK-004 生产 | Work Order outbox、material-check 仓库字段 | 已收口本地门禁 | Work Order 创建字段必须从冻结 DTO 来，不得由前端任意 payload 决定。 |
| TASK-005 利润 | SLE/Sales/外发来源缺状态或归属字段曾 fail-open | 已改关键归属 fail-closed | 利润来源缺 `company/item/work_order` 等关键归属字段必须 unresolved，不得纳入利润。 |
| TASK-006 对账 | Supplier/Account/PI 草稿、payable outbox | 已收口草稿创建与 active 防重 | Supplier/Account/Cost Center/PI 外部校验不可用必须业务失败，不得落半事实。 |

结论：各模块最终趋于一致，但实现方式分散。Sprint 2 必须提供公共 ERPNext adapter 规范，统一错误码、日志脱敏、docstatus 校验、权限源不可用语义。

### 3.2 前端契约门禁是否可抽象

style-profit 门禁从 TASK-005I 到 TASK-005J37 连续经历中文语义、跨行交互、对象祖先链、computed key、runtime mutator、codegen、timer、dynamic import、Worker、数组污染等多轮修复。它证明两个事实：

1. 单靠正则扫描不可持续。
2. 每个模块单独写门禁会重复踩坑。

Sprint 2 应把 style-profit 经验抽象为通用前端写入口门禁：

- 基于 TypeScript AST，而不是纯正则。
- 每个模块声明：允许 API 方法、允许路由、允许权限动作、禁止写动作词、禁止 internal worker、禁止 ERPNext 直连。
- 所有写入口默认 fail closed，包括动态 action key、runtime mutator、eval/Function、字符串 timer、dynamic import、Worker data/blob URL。
- 每个模块必须提供反向 fixture，覆盖 direct/call/apply/bind/alias/computed/runtime mutation。
- `npm run verify` 必须统一跑全部模块 contract。

### 3.3 Outbox 状态机是否统一

TASK-002、TASK-003、TASK-004、TASK-006 都实现了 outbox，但多次出现同类问题：

- event_key 使用易变字段或截断导致碰撞/不能 replay。
- claim_due 第二阶段 UPDATE 没有重复校验 due/lease。
- worker 调 ERPNext 前未重新检查本地 aggregate 状态。
- dry-run/diagnostic 审计缺失或开关顺序不对。
- succeeded/draft/cancelled ERPNext docstatus 判定不一致。
- active outbox 防重规则缺失。

Sprint 2 应抽取公共 outbox 规范，而不是强行抽公共代码。先统一表字段、状态迁移、claim 条件、事件键、幂等、worker 前置校验和测试矩阵；是否抽象基类由工程实现评估，但任务卡必须引用同一规范。

## 四、TASK-S-002 验收工具包使用情况

### 4.1 工具包能力

TASK-S-002 目录记录显示，验收工具包覆盖 BOM、Workshop、Production、Subcontract 四类共 13 个关键接口：

- BOM：`POST /api/bom/`、`GET /api/bom/`、`GET /api/bom/{bom_id}`。
- Workshop：`tickets/register`、`tickets/reversal`、`tickets`、`daily-wages`。
- Production：`plans` POST/GET、`plans/{plan_id}/material-check`。
- Subcontract：`POST /api/subcontract/`、`GET /api/subcontract/`、`POST /api/subcontract/{order_id}/issue-material`。

工具支持 `--module`、`--base-url`、`--token`、`--report-dir`、`--config`，仅通过 HTTP 调用，不 import 主业务代码，能输出 `report.json/report.md`，并用退出码区分全通过和失败/跳过/环境阻塞。

### 4.2 使用不足

审计记录显示，各任务主要依赖模块定向 pytest、py_compile、前端 contract、PostgreSQL gate，而 TASK-S-002 作为统一冒烟工具没有贯穿 TASK-005/TASK-006 封版链路。原因是工具最初覆盖四个模块，不覆盖款式利润和加工厂对账单，也不覆盖前端写入口、outbox worker、ERPNext docstatus、PostgreSQL 并发语义。

### 4.3 13 个接口 case 是否覆盖高危路径

结论：未覆盖所有高危路径。

已覆盖：
- BOM 基础 CRUD/读取入口。
- 工票登记/撤销/列表/日薪主路径。
- 生产计划创建/列表/物料检查主路径。
- 外发创建/列表/发料主路径。

未覆盖：
- 后端资源级权限负向路径。
- ERPNext 权限源/主数据源不可用 fail-closed。
- outbox claim/lease/retry/dead/dry-run/diagnostic。
- PostgreSQL 并发和唯一约束等待语义。
- TASK-005 利润快照来源归属、只读前端门禁。
- TASK-006 对账确认/取消/payable outbox/CSV 导出安全。

Sprint 2 必须把 TASK-S-002 扩展为“主路径冒烟 + 高危负向用例索引”，不能仅作为 happy path 工具。

## 五、Sprint 2 架构收口要求

1. 所有 P1 模块任务卡必须引用 `Sprint2_架构规范.md`。
2. 未完成设计冻结的模块不得进入实现。
3. 每个模块必须先交任务单审计，再实现代码。
4. 任务单必须列出：权限动作、资源权限、ERPNext 依赖、outbox 事件键、幂等键、前端写入口禁线、测试矩阵。
5. 任意新前端模块必须提供 contract check + contract negative fixture。
6. 任意 ERPNext 写入必须走 outbox，不得在业务事务中直接调用 ERPNext。
7. 任意 PostgreSQL 并发语义必须提供 non-skip 证据或明确本地封版限制。

## 六、Sprint 1 经验总结

Sprint 1 的核心成果不是单个模块完成，而是把服装 ERP 的关键风险面暴露出来：权限、ERPNext 集成、outbox、前端写入口、审计证据链。这些风险如果继续分散在任务内临时修复，Sprint 2 会重复消耗。下一阶段必须先统一规范，再派任务。
