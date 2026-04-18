# TASK-021A 生产管理边界设计

- 任务编号：TASK-021A
- 任务名称：生产管理边界设计冻结
- 角色：架构师
- 优先级：P1
- 更新时间：2026-04-17
- 前置依赖：Sprint 3 设计冻结文档 TASK-015A~020A 已审计通过；TASK-014C 仍冻结
- 设计定位：生产管理 P1 模块边界冻结，不代表功能实现、ERPNext 联调或生产发布完成

## 1. 总体目标

冻结生产管理模块的功能边界、ERPNext 集成策略、权限审计要求和禁止事项，为后续 Work Order / Job Card / BOM / Routing 相关任务提供前置设计。

本任务只输出设计文档：

```text
禁止写业务代码。
禁止连接生产 ERPNext。
禁止直接写 ERPNext 生产接口。
禁止绕过 TASK-008 Fail-Closed Adapter。
禁止绕过 TASK-009 Outbox 公共状态机。
禁止绕过 TASK-010 前端写入口门禁公共框架。
TASK-014C 未完成前，不允许进入真实平台联调或生产发布。
```

## 2. 功能边界

### 2.1 纳入设计范围

| 能力 | 范围 | 当前阶段结论 |
|---|---|---|
| Work Order 管理 | 生产工单读取、草稿创建建议、状态同步、与销售订单/生产计划/BOM 关联 | 设计冻结，写入默认冻结 |
| Job Card 管理 | 工序任务读取、同步、完成数量来源校验、与工票车间模块衔接 | 设计冻结，写入必须 outbox |
| BOM 关联 | 本地 BOM 与 ERPNext BOM 的映射、版本、启用状态、工序成本引用 | 设计冻结，BOM 主维护不在本任务实现 |
| Routing 关联 | 工艺路线、工序顺序、工作站、标准工时与 Job Card 生成依据 | 设计冻结，Routing 写入默认冻结 |
| 生产计划衔接 | Sales Order -> Production Plan -> Work Order -> Job Card 链路 | 设计冻结，沿用 TASK-004 既有链路 |
| 物料可用性检查 | 基于 BOM 展开、库存只读事实、仓库资源权限进行检查 | 只读检查，禁止直接扣库存 |
| 完工与异常 | 完工数量、报废、返工、暂停、取消的状态边界 | 仅设计状态语义，不实现写入 |

### 2.2 不纳入本阶段实现

1. 不实现 Work Order 生产写入。
2. 不实现 Job Card 完成数量直接写入 ERPNext。
3. 不实现 BOM / Routing 在 ERPNext 的创建或修改。
4. 不实现 Stock Entry 生产入库 / 领料 / 退料。
5. 不实现工单自动提交 ERPNext。
6. 不实现自动生成 GL / Payment / 财务凭证。
7. 不实现前端页面或后端接口。
8. 不做生产 ERPNext 联调。

## 3. 领域对象边界

### 3.1 Work Order

Work Order 是生产执行主对象。系统必须区分本地生产计划事实和 ERPNext Work Order 事实。

| 字段 / 事实 | 权威来源 | 说明 |
|---|---|---|
| company | ERPNext 或本地生产计划，二者必须一致 | 不一致 fail closed |
| sales_order | 本地生产计划 + ERPNext 只读校验 | 不得只信任前端传入 |
| item_code | BOM / Sales Order / Work Order 派生后交叉校验 | 不一致 fail closed |
| planned_qty | 本地生产计划草稿或 ERPNext Work Order 只读事实 | 写入前必须冻结 |
| produced_qty | ERPNext Work Order / Job Card 只读事实 | 前端不得重算为事实 |
| status / docstatus | ERPNext Fail-Closed Adapter | 缺失或非法 fail closed |
| bom_id | 本地 BOM 与 ERPNext BOM 映射 | 映射缺失时不得写入 |

Work Order 写入原则：

1. 创建建议可以在本地生成 draft intent。
2. 任何 ERPNext Work Order 创建必须走 Outbox。
3. Outbox worker 调 ERPNext 前必须重新读取本地计划状态、资源权限、BOM/Routing 映射。
4. ERPNext 返回缺失 `docstatus`、非法 `docstatus`、malformed response、timeout、401、403、5xx 均 fail closed。
5. 成功只允许在 ERPNext 明确返回可信外部单据号和合法状态后记录。

### 3.2 Job Card

Job Card 是工序级执行对象，必须与 Work Order、Routing、工票车间模块保持一致。

| 字段 / 事实 | 权威来源 | 说明 |
|---|---|---|
| job_card | ERPNext Job Card | 只读读取或 outbox 同步结果 |
| work_order | ERPNext Job Card -> Work Order | 不得由前端任意输入 |
| operation | Routing / ERPNext Job Card | 必须与工序定义一致 |
| operation_sequence | Routing | 缺失或重复必须 fail closed |
| expected_qty | Work Order / Job Card | 不得前端重算 |
| completed_qty | 工票事实 + ERPNext Job Card 校验 | 重复同步必须幂等 |
| status | ERPNext Job Card | 状态缺失或异常 fail closed |

Job Card 写入原则：

1. 工票登记、撤销、批量导入不得在本地事务提交前调用 ERPNext Job Card 写接口。
2. Job Card 完成数量同步必须 after-commit + Outbox。
3. Worker 必须使用服务账号最小权限，并按 `company/item_code/work_order/job_card` 校验资源 scope。
4. 服务账号资源越权时不得调用 ERPNext，不得把 outbox 标记为 succeeded。
5. dry-run 不得锁定 outbox，不得增加 attempts，不得更新 next_retry_at，不得调用 ERPNext。
6. 生产 dry-run 禁用判断必须在 ERPNext 权限源读取之前完成。

### 3.3 BOM

BOM 在生产管理中的职责是生产结构与物料需求依据，不在本任务中实现 BOM 主维护。

| BOM 能力 | 边界 |
|---|---|
| 本地 BOM | 款式 BOM、物料用量、损耗、工序成本等本地业务口径 |
| ERPNext BOM | 生产工单外部事实和主数据校验来源之一 |
| BOM 映射 | 必须记录本地 BOM 与 ERPNext BOM 的关联、版本、启用状态 |
| BOM 展开 | 可用于物料需求检查，不得直接扣库存 |
| BOM 版本 | 创建 Work Order 前必须固定版本，禁止运行中漂移 |

BOM fail-closed 规则：

1. 未找到 active/default BOM，不允许创建 Work Order intent。
2. 本地 BOM 与 ERPNext BOM 映射缺失，不允许生产写入。
3. BOM item 与 Sales Order item / Work Order production_item 不一致，必须 fail closed。
4. BOM 展开失败不得返回空物料清单伪成功。
5. ERPNext BOM 只读校验不可用时，生产写入冻结。

### 3.4 Routing

Routing 是工艺路线与 Job Card 生成依据。

| Routing 能力 | 边界 |
|---|---|
| 工序顺序 | 必须唯一且可排序 |
| 工作站 / 车间 | 必须映射到可授权资源 |
| 标准工时 | 可用于计划和看板，不得作为实际完工事实 |
| 计件工价关联 | 与工票车间模块衔接，不在本任务重算工资 |
| ERPNext Routing | 只读校验或后续 outbox 写入候选，生产写入冻结 |

Routing fail-closed 规则：

1. 工序序号缺失、重复、倒序异常时不得生成 Job Card 写入 intent。
2. Routing 与 BOM 版本不匹配时不得写入。
3. 工作站或车间资源权限不可用时不得写入。
4. ERPNext Routing 响应 malformed、timeout、401/403/5xx 时 fail closed。

## 4. ERPNext 集成策略

| 生产能力 | ERPNext DocType | 只读/写入 | Adapter | Outbox | 是否允许生产 |
|---|---|---|---|---|---|
| Work Order 查询 | Work Order | 只读 | 必须 TASK-008 | 否 | 是，仅读取 |
| Work Order 草稿创建 | Work Order | 写入草稿候选 | 必须 TASK-008 | 必须 TASK-009 | 否，当前冻结 |
| Work Order 提交 | Work Order | 写入提交候选 | 必须 TASK-008 | 必须 TASK-009 | 否，单独任务放行 |
| Job Card 查询 | Job Card | 只读 | 必须 TASK-008 | 否 | 是，仅读取 |
| Job Card 完成数量同步 | Job Card | 写入候选 | 必须 TASK-008 | 必须 TASK-009 | 否，当前冻结 |
| BOM 查询 | BOM | 只读 | 必须 TASK-008 | 否 | 是，仅读取 |
| BOM 创建/修改 | BOM | 写入候选 | 必须 TASK-008 | 必须 TASK-009 | 否，当前冻结 |
| Routing 查询 | Routing | 只读 | 必须 TASK-008 | 否 | 是，仅读取 |
| Routing 创建/修改 | Routing | 写入候选 | 必须 TASK-008 | 必须 TASK-009 | 否，当前冻结 |
| 物料库存事实 | Stock Ledger Entry / Bin | 只读 | 必须 TASK-008 | 否 | 是，仅读取 |
| 生产领料/完工入库 | Stock Entry | 写入候选 | 必须 TASK-008 | 必须 TASK-009 | 否，归 TASK-018 后续任务 |

## 5. Adapter 策略

所有 ERPNext 读取和写入候选都必须经过 TASK-008 Fail-Closed Adapter。

必须遵守：

1. timeout -> `ERPNEXT_TIMEOUT` 或业务层 `EXTERNAL_SERVICE_UNAVAILABLE`。
2. 401/403 -> `ERPNEXT_AUTH_FAILED`，不得继续流程。
3. 404 -> `ERPNEXT_RESOURCE_NOT_FOUND`，不得伪装为空数据。
4. 5xx -> `EXTERNAL_SERVICE_UNAVAILABLE`。
5. malformed response -> `ERPNEXT_RESPONSE_INVALID`。
6. docstatus 缺失 -> `ERPNEXT_DOCSTATUS_REQUIRED`。
7. docstatus 非法 -> `ERPNEXT_DOCSTATUS_INVALID`。
8. 禁止 `detail=str(exc)` 泄露。
9. 禁止 `200 + 空数据` 伪成功。

## 6. Outbox 策略

所有 ERPNext 写入候选都必须经过 TASK-009 Outbox 公共状态机。

### 6.1 event_key 与 idempotency_key

| 字段 | 职责 | 禁止事项 |
|---|---|---|
| `idempotency_key` | 客户端请求重放识别 | 不得作为业务事实唯一性唯一依据 |
| `event_key` | 业务事实去重 | 不得包含 attempts、status、locked_by、operator、request_id 等运行态字段 |

Work Order event_key 建议业务口径：

```text
production.work_order.create:v1:{company}:{sales_order}:{sales_order_item}:{item_code}:{bom_id}:{planned_qty}:{planned_start_date}
```

Job Card sync event_key 建议业务口径：

```text
production.job_card.sync:v1:{company}:{work_order}:{job_card}:{operation}:{completed_qty_delta_source_id}
```

### 6.2 状态机

必须使用统一状态：

```text
pending -> processing -> succeeded
pending -> processing -> failed -> pending retry
failed -> dead
pending/failed -> cancelled（仅业务允许时）
```

安全约束：

1. claim 二阶段 UPDATE 必须重复校验 due/lease 条件。
2. processing lease 未过期不得被 stale claim 抢占。
3. worker 外调 ERPNext 前必须重新校验本地业务状态、资源权限、金额/数量/单据关键字段一致性。
4. cancelled / dead / succeeded 的状态转换必须受控。
5. failed/dead 重建必须单独任务设计，不得绕过 event_key。

## 7. 权限要求

### 7.1 动作权限

| 动作 | 权限 |
|---|---|
| 读取生产计划 / Work Order / Job Card | `production:read` |
| 导出生产数据 | `production:export` |
| 创建生产计划草稿 | `production:plan_create` |
| 创建 Work Order intent | `production:work_order_draft` |
| 确认 Work Order 写入候选 | `production:work_order_confirm` |
| 取消 Work Order intent | `production:work_order_cancel` |
| 同步 Job Card intent | `production:job_card_sync` |
| 物料可用性检查 | `production:material_check` |
| dry-run | `production:dry_run` |
| diagnostic | `production:diagnostic` |
| worker | `production:worker` |

### 7.2 资源权限字段

必须至少覆盖：

- company
- item_code
- warehouse
- work_order
- job_card
- sales_order
- bom_id
- routing
- operation
- work_center

资源权限规则：

1. company 为空时 fail closed。
2. item_code 为空时，涉及生产写入必须 fail closed。
3. Work Order / Job Card 派生的 company/item_code 与请求体不一致时 fail closed。
4. 权限源不可用时 fail closed。
5. 未知 resource scope 字段必须 fail closed。
6. 服务账号必须使用最小资源权限。

## 8. 安全审计与操作审计

### 8.1 安全审计事件

必须记录：

- 401 未认证
- 403 禁止
- 资源越权
- 权限源不可用
- ERPNext 不可用
- ERPNext malformed response
- internal API 非授权访问
- request_id rejected
- unknown resource scope
- worker 越权跳过

安全审计字段：

- timestamp
- user
- event_type
- action
- resource
- company
- item_code
- work_order
- job_card
- ip
- request_id

禁止记录：

- Authorization
- Cookie
- Token
- Secret
- Password
- ERPNext API Key / Secret
- 原始异常敏感详情

### 8.2 操作审计事件

必须记录：

- create
- update
- confirm
- cancel
- export
- dry-run
- diagnostic
- worker claim
- worker succeeded
- worker failed
- retry scheduled
- dead marked

操作审计必须包含：

- 操作人
- 时间戳
- 业务关联 ID
- 变更前后值摘要
- 幂等键
- event_key
- request_id
- 外部单据号（如有）

## 9. 前端门禁要求

1. 必须接入 TASK-010 前端写入口门禁公共框架。
2. 未实现阶段不得出现 production 相关写入口页面。
3. `production:diagnostic`、`production:worker` 不得暴露给普通前端菜单。
4. 前端禁止直连 ERPNext `/api/resource`。
5. 前端禁止裸 `fetch/axios` 绕过 API client。
6. 前端禁止 runtime codegen、动态 import 高危加载、Worker 不可信代码加载。
7. 导出必须防 CSV / Excel 公式注入。
8. positive / negative fixtures 必须覆盖写入口禁线、diagnostic 禁线、ERPNext 直连禁线。

## 10. 与既有模块关系

| 既有模块 | 关系 | 边界 |
|---|---|---|
| TASK-001 BOM 管理 | 提供本地 BOM、物料、工序成本基础 | 本任务不修改 BOM 主数据 |
| TASK-003 工票车间 | 提供工票事实与 Job Card 同步经验 | 本任务不重算工资，不绕过工票事务边界 |
| TASK-004 生产计划 | 提供 Sales Order -> Production Plan -> Work Order 链路基础 | 本任务冻结后续增强边界 |
| TASK-005 款式利润 | 依赖 Work Order / Job Card 归属桥 | 本任务不得改变利润口径 |
| TASK-011 销售库存只读 | 提供 Sales Order / SLE / Warehouse 只读事实 | 本任务不得写库存事实 |
| TASK-012 质量管理 | 可关联生产检验对象 | 本任务不实现质检写入 |
| TASK-018 仓库增强 | 负责 Stock Entry / 盘点 / 预警后续设计 | 本任务不实现库存写入 |

## 11. 状态与错误语义

### 11.1 本地生产 intent 状态

| 状态 | 含义 | 是否允许写 ERPNext |
|---|---|---|
| draft | 本地草稿 | 否 |
| validated | 本地校验通过 | 否 |
| pending_outbox | 已生成 outbox | 由 worker 控制 |
| processing | worker 持有 lease | 由 worker 控制 |
| synced | ERPNext 明确成功 | 否，最终态 |
| failed | 可重试失败 | 否，等待重试 |
| dead | 不再自动重试 | 否 |
| cancelled | 已取消 | 否 |

### 11.2 错误码建议

| 错误码 | 场景 |
|---|---|
| `PRODUCTION_PERMISSION_DENIED` | 动作或资源权限不足 |
| `PRODUCTION_PERMISSION_SOURCE_UNAVAILABLE` | 权限源不可用 |
| `PRODUCTION_BOM_REQUIRED` | 缺少有效 BOM |
| `PRODUCTION_BOM_MISMATCH` | BOM 与 SO/WO item 不一致 |
| `PRODUCTION_ROUTING_REQUIRED` | 缺少有效 Routing |
| `PRODUCTION_ROUTING_INVALID` | Routing 工序异常 |
| `PRODUCTION_WORK_ORDER_CONFLICT` | Work Order 业务事实冲突 |
| `PRODUCTION_JOB_CARD_CONFLICT` | Job Card 同步事实冲突 |
| `PRODUCTION_ERPNEXT_UNAVAILABLE` | ERPNext 不可用 |
| `PRODUCTION_ERPNEXT_RESPONSE_INVALID` | ERPNext 返回结构非法 |
| `PRODUCTION_OUTBOX_ACTIVE` | 已存在 active outbox |
| `PRODUCTION_IDEMPOTENCY_CONFLICT` | 同 key 异 hash |

## 12. 测试与审计要求

后续实现任务必须至少覆盖：

1. ERPNext timeout / 401 / 403 / 5xx fail closed。
2. Work Order docstatus 缺失 / 非法 fail closed。
3. Job Card malformed response fail closed。
4. BOM 映射缺失 fail closed。
5. Routing 工序重复 fail closed。
6. 服务账号资源越权不得调用 ERPNext。
7. event_key 不受 idempotency_key、attempts、locked_by 等运行态影响。
8. stale claim 不得抢占未过期 lease。
9. pending outbox 存在时不得重复创建 active outbox。
10. 前端禁止 ERPNext 直连、diagnostic、worker、runtime codegen。
11. 导出公式注入防护。
12. 操作审计和安全审计均脱敏。

## 13. 生产发布前置条件

1. TASK-014C 完成。
2. Hosted Runner required checks 平台闭环。
3. Branch Protection 已配置。
4. ERPNext 只读联调通过。
5. 沙箱写入验证通过。
6. 生产管理实现任务单独设计、单独审计、单独放行。
7. Work Order / Job Card / BOM / Routing 写入必须由总调度书面批准。
8. 生产写入前必须有回滚方案和演练证据。

## 14. 禁止事项清单

- 禁止写业务代码。
- 禁止实现后端接口。
- 禁止实现前端页面。
- 禁止连接生产 ERPNext。
- 禁止直接写 ERPNext 生产接口。
- 禁止绕过 TASK-008 Adapter。
- 禁止绕过 TASK-009 Outbox。
- 禁止绕过 TASK-007 权限审计基座。
- 禁止绕过 TASK-010 前端门禁。
- 禁止把 ERPNext 失败伪装为成功。
- 禁止 `200 + 空数据` 伪成功。
- 禁止记录真实凭据。
- 禁止生产发布语义。
- 禁止解冻 TASK-014C。

## 15. 审计结论建议口径

若本文件通过审计，结论应为：

```text
TASK-021A 审计通过。
生产管理边界设计已冻结。
本结论不代表生产管理功能已实现。
本结论不代表 ERPNext 生产联调完成。
本结论不解冻 TASK-014C。
允许继续 TASK-022A 成本核算边界设计冻结。
```
