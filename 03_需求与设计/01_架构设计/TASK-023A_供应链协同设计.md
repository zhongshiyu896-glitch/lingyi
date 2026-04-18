# TASK-023A 供应链协同设计

- 任务编号：TASK-023A
- 任务名称：供应链协同设计冻结
- 角色：架构师
- 优先级：P1
- 文档状态：审计通过（审计意见书第 215 份）
- 更新日期：2026-04-17
- 前置依赖：TASK-022A 审计通过
- 适用阶段：Sprint 3 设计冻结（不含实现）

## 1. 设计目标与冻结范围

冻结供应链协同模块边界，明确供应商协同、采购协同、物流跟踪、外部系统集成、ERPNext 集成策略、Adapter/Outbox 路径、权限审计与前端门禁。

本任务仅输出设计，不实现接口和页面，不做平台联调，不做生产发布。

```text
禁止写业务代码。
禁止修改前端、后端、.github、02_源码。
禁止连接生产 ERPNext。
禁止解冻 TASK-014C。
禁止声明 required checks / Hosted Runner / Branch Protection 闭环。
禁止声明生产发布完成。
```

## 2. 功能边界与责任边界

### 2.1 供应商侧（Supplier Collaboration）

供应商协同负责：

1. 供应商资料只读对齐（资质状态、联系人、交付能力、协同状态）。
2. 供应商确认信息接入（确认交期、确认数量、异常回告）作为协同事实输入。
3. 供应商履约状态追踪（按 PO 行、批次、交付节点）用于只读看板与告警。

供应商协同不负责：

1. 直接修改 ERPNext Supplier 主数据。
2. 直接写入财务事实（GL/Payment/AP/AR）。
3. 跳过审批链直接确认采购单或入库。

### 2.2 采购侧（Procurement Collaboration）

采购协同负责：

1. 采购订单协同状态（已下单/待确认/部分交付/完成/异常）建模。
2. 采购执行过程的节点对齐（下单、确认、发运、收货、差异处理）。
3. 采购异常归因（延期、短交、质量问题、物流中断）与责任归集。

采购协同不负责：

1. 直接创建或提交 ERPNext Purchase Order/Purchase Receipt/Purchase Invoice（当前阶段冻结）。
2. 直接执行库存入账或财务入账。
3. 替代 ERPNext 作为采购事实权威源。

### 2.3 物流侧（Logistics Tracking）

物流跟踪负责：

1. 运输节点采集与状态标准化（已发运/在途/签收/异常）。
2. 物流单号、承运商、运输批次与采购行/收货单映射。
3. 在途风险识别（超时、断点、回传缺失）和协同告警。

物流跟踪不负责：

1. 直接写 ERPNext 库存或财务。
2. 以物流状态替代收货事实。
3. 绕过资源权限展示跨公司/跨供应商链路。

## 3. 外部系统集成边界

### 3.1 外部协同对象

- 供应商门户（确认/回告）
- 物流服务商接口（节点/轨迹）
- 采购协同中台（可选）
- ERPNext（权威业务单据和主数据）

### 3.2 数据进入路径

1. 外部事件入站必须先进入“协同接入层”做签名校验、结构校验、幂等判定。
2. 校验通过后写入本地协同事实（仅协同域，不改 ERPNext 事实）。
3. 任一关键字段缺失/权限上下文缺失/来源不可用均 fail closed。

### 3.3 数据回写路径

1. 回写 ERPNext 的候选动作必须进入 Outbox（TASK-009），不得同步直写。
2. worker 执行前必须做资源权限重校验与状态重校验。
3. 未放行能力保持冻结，不得通过“内部接口”绕过门禁。

## 4. ERPNext 集成策略（TASK-008 / TASK-009）

### 4.1 能力矩阵

| 协同能力 | ERPNext DocType | 读/写 | Adapter | Outbox | 当前是否允许生产 |
|---|---|---|---|---|---|
| 供应商资料读取 | Supplier | 只读 | 必须 TASK-008 | 不适用 | 是（只读） |
| 采购单读取 | Purchase Order | 只读 | 必须 TASK-008 | 不适用 | 是（只读） |
| 收货单读取 | Purchase Receipt | 只读 | 必须 TASK-008 | 不适用 | 是（只读） |
| 采购发票读取 | Purchase Invoice | 只读 | 必须 TASK-008 | 不适用 | 是（只读） |
| 库存台账读取 | Stock Ledger Entry | 只读 | 必须 TASK-008 | 不适用 | 是（只读） |
| 协同状态回写候选 | Purchase Order / Purchase Receipt（候选） | 写入候选 | 必须 TASK-008 | 必须 TASK-009 | 否（冻结） |
| 物流状态驱动候选 | Delivery Note / Stock Entry（候选） | 写入候选 | 必须 TASK-008 | 必须 TASK-009 | 否（冻结） |

### 4.2 fail-closed 原则

必须统一执行：

1. timeout -> fail closed。
2. 401/403 -> fail closed。
3. 404 -> not found（不得伪成功）。
4. 5xx -> fail closed。
5. malformed response -> fail closed。
6. docstatus/status 缺失或非法（适用对象）-> fail closed。
7. 禁止 `200 + 空数据` 伪成功。
8. 禁止 `detail=str(exc)` 泄露。

## 5. Adapter / Outbox 边界

### 5.1 Adapter（TASK-008）

1. 所有 ERPNext 交互统一经 Adapter，禁止裸连 ERPNext API。
2. Adapter 只返回标准化结果或结构化异常。
3. 权限源或资源源不可用时统一 fail closed。

### 5.2 Outbox（TASK-009）

1. 所有写入候选必须走 Outbox，禁止同步直写。
2. `idempotency_key` 与 `event_key` 必须职责分离。
3. `event_key` 禁止包含运行态字段（attempts/status/locked_by/request_id/operator）。
4. claim/lease/retry/dead 必须遵守统一状态机。
5. dry-run 仅做验证，不改状态、不外调。

## 6. 资源权限字段与权限要求

### 6.1 资源权限字段（冻结）

- `company`
- `supplier`
- `purchase_order`
- `purchase_receipt`
- `purchase_invoice`
- `item_code`
- `warehouse`
- `logistics_provider`
- `tracking_no`
- `shipment_batch`

规则：

1. 列表与详情先动作权限，再资源权限。
2. 资源字段缺失默认拒绝（fail closed）。
3. 资源越权必须写安全审计。
4. 资源级详情查询必须先按 `scope` 过滤，再执行详情命中判定。
5. 对外语义冻结：`资源存在但越权` 与 `资源不存在` 统一返回 `not-found` 形态。
6. 内部仍必须写安全审计并保留拒绝原因，对外不得暴露可区分信息。

### 6.2 动作权限（冻结）

- `supply_chain:read`
- `supply_chain:export`
- `supply_chain:collaboration_sync`
- `supply_chain:logistics_track`
- `supply_chain:dry_run`
- `supply_chain:diagnostic`
- `supply_chain:worker`

## 7. 审计要求（TASK-007）

### 7.1 安全审计事件

- 401 未认证
- 403 禁止
- 资源越权
- 权限源不可用
- ERPNext 不可用
- 外部协同源签名失败 / 数据结构异常
- internal API 非授权访问
- request_id rejected

### 7.2 操作审计事件

- read
- export
- collaboration_sync
- logistics_track
- dry-run
- diagnostic
- worker dispatch
- worker claim
- worker succeeded
- worker failed
- retry scheduled
- dead marked

### 7.3 脱敏要求

日志与审计中禁止记录：

- Authorization
- Cookie
- Token
- Secret
- password
- 明文 DSN

## 8. 前端边界（继承 TASK-010）

1. 普通前端禁止暴露 `diagnostic / worker / internal` 入口。
2. 普通前端禁止暴露 `run-once` 类入口。
3. 前端禁止直连 ERPNext `/api/resource`。
4. 前端禁止裸 `fetch/axios` 绕过 API client。
5. 协同导出必须启用 CSV/Excel 公式注入防护。
6. 所有写入候选按钮默认隐藏，未放行能力不得出现可触发入口。

## 9. 禁止事项清单

1. 禁止绕过 TASK-008。
2. 禁止绕过 TASK-009。
3. 禁止绕过 TASK-010。
4. 禁止绕过 TASK-007。
5. 禁止连接生产 ERPNext。
6. 禁止直接写财务与库存事实。
7. 禁止在 TASK-014C 冻结状态下推进平台写链路。
8. 禁止声明 required checks 闭环。
9. 禁止声明 Hosted Runner 闭环。
10. 禁止声明 Branch Protection 闭环。
11. 禁止声明生产发布完成。
12. 禁止在 TASK-023A 复审通过前进入 TASK-023B。

## 10. 结论边界

1. 本文档仅冻结供应链协同边界，不代表业务代码已实现。
2. 本文档不代表 ERPNext 联调完成。
3. 本文档不解冻 TASK-014C。
4. 本文档不代表 required checks 平台闭环。
5. 本文档不代表生产发布完成。
