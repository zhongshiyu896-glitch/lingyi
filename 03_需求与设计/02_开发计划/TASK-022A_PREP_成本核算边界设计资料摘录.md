# TASK-022A PREP 成本核算边界设计资料摘录

- 任务编号：TASK-022A-PREP
- 任务名称：成本核算边界设计冻结材料准备
- 角色：工程师
- 执行日期：2026-04-17
- 文档性质：资料索引与现状摘录（供架构师产出 `TASK-022A_成本核算边界设计.md`）
- 当前状态：TASK-021A 已于审计意见书第212份正式通过；TASK-022A 允许启动并提交正式审计。
- 本资料可作为 `TASK-022A_成本核算边界设计.md` 的审计辅助输入，但不替代正式设计文档。
- TASK-022A 当前应进入正式审计链路，不进入实现。

---

## 1. 成本中心相关现状

### 1.1 财务边界中的 Cost Center 现状

来源：`03_需求与设计/01_架构设计/TASK-016A_财务管理边界设计.md`

- Cost Center 在财务边界中定位为 ERPNext 主数据只读对象，必须经 TASK-008 Adapter 读取，当前阶段不开放写入。  
  - 证据：集成策略表中 `Cost Center | 只读 | 必须(TASK-008) | 不适用 Outbox | 否`（第 7 章）。
- 财务权限资源字段中已冻结 `cost_center`，意味着成本核算模块若涉及成本中心过滤，应直接复用 TASK-016A 资源权限语义。  
  - 证据：第 8.2 节资源权限字段。
- 财务读取失败路径已冻结 fail-closed，不允许“空数据伪成功”。  
  - 证据：第 8.5 节“禁止 `200 + 空数据` 伪成功”。

### 1.2 生产与利润链路中的成本中心缺口

来源：`03_需求与设计/01_架构设计/TASK-021A_生产管理边界设计.md`、`03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`

- 生产边界重点冻结了 Work Order/Job Card/BOM/Routing/库存事实链路，但未单独冻结“成本中心分摊规则”。
- 款式利润文档冻结了成本口径（标准/实际）与幂等约束，但费用分摊为 V1 默认不纳入，需要后续 ADR。  
  - 证据：`06_模块设计_款式利润报表.md` 第 11.4、11.5。

结论：`TASK-022A` 需要补齐“成本中心分摊规则 + 审计口径 + 权限过滤字段”的统一冻结定义。

---

## 2. 标准成本来源现状

来源：`03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`、`03_需求与设计/01_架构设计/TASK-021A_生产管理边界设计.md`

### 2.1 BOM

- 标准材料成本公式已冻结：`standard_material_cost = sum(bom_exploded_required_qty * standard_unit_cost)`。  
- BOM 版本必须在生产写入前固定，禁止运行中漂移。  
- BOM 映射缺失时生产写入必须 fail closed。

### 2.2 工序

- 标准工序成本公式已冻结：`standard_operation_cost = sum(bom_operation_rate * planned_qty)`。
- 工序顺序/路由异常（缺失、重复、倒序）必须 fail closed。

### 2.3 工价

- 本厂工序使用 BOM 工序计件工价。  
- 工价与工票成本在后续实际成本计算中需保持同一快照语义（避免口径漂移）。

### 2.4 外发加工

- 标准成本侧可引用外发工序单件成本（`subcontract_cost_per_piece`）。
- 外发成本口径需与实际外发成本口径区分，避免“标准外发单价”与“实际结算净额”混用。

---

## 3. 实际成本来源现状

来源：`03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`、`03_需求与设计/01_架构设计/TASK-021A_生产管理边界设计.md`

### 3.1 Stock Ledger Entry（SLE）

- 实际材料成本 V1 口径已冻结为 SLE：`actual_material_cost = sum(abs(stock_value_difference))`。  
- `Purchase Receipt` 只作参考/排查，不直接计入实际材料成本。
- SLE 纳入必须满足归属约束（company/item/order/work_order 等），不满足则不可入账。

### 3.2 工票

- 实际工票成本公式已冻结：`actual_workshop_cost = sum(net_ticket_qty * wage_rate_snapshot)`。  
- 净数量定义：`net_ticket_qty = register_qty - reversal_qty`。
- 无法归属到目标订单/工单/工序链路时，必须 unresolved 标记，不得静默吞并。

### 3.3 外发扣款

- 实际外发成本口径：结算优先、验货兜底。  
- 扣款金额仅作明细展示；若已使用净额 `net_amount`，不得重复扣减。

### 3.4 质量损耗

- 在现有已读文档中，质量损耗尚未冻结为独立实际成本子项。  
- 生产边界仅给出“可关联质检对象（TASK-012）”，但未定义质量损耗入成本主公式的规则。  

建议：`TASK-022A` 需明确质量损耗是否进入实际成本，以及进入时的来源对象、分摊粒度、审计字段和 fail-closed 条件。

---

## 4. 与财务模块（TASK-016A）的边界

来源：`03_需求与设计/01_架构设计/TASK-016A_财务管理边界设计.md`

- 成本核算不应绕过财务边界直接改写 Payment Entry / GL / AP / AR 事实。  
- 当前阶段 GL 与 Payment Entry 均为只读/冻结写入，成本核算模块应输出“核算结果视图/候选分录”，不得直接入账。  
- 所有 ERPNext 访问必须走 TASK-008 Adapter；所有未来写入候选必须走 TASK-009 Outbox。  
- 资源权限应至少继承 `company/account/cost_center/supplier/customer`。  
- 安全要求必须继承：禁止 `detail=str(exc)`、禁止 `200 + 空数据` 伪成功、禁止 secret 入库。

---

## 5. 与款式利润（TASK-005）的边界

来源：`03_需求与设计/01_架构设计/06_模块设计_款式利润报表.md`

- TASK-005 已冻结“利润快照”口径与幂等规则（`company + idempotency_key`），`TASK-022A` 不应重复定义利润快照主公式。  
- `TASK-022A` 更适合作为“成本事实治理层”补强：
  - 成本中心口径；
  - 分摊规则；
  - 成本事实分层（标准/实际/未结算 provisional）；
  - 与财务只读事实映射关系。
- 边界建议：
  - TASK-005 继续负责“利润结果与快照”；
  - TASK-022A 负责“成本核算边界与成本事实规则”；
  - 两者通过统一 source_map / 审计字段衔接，避免重复实现。

---

## 6. ERPNext Adapter 适用点（TASK-008）

来源：`03_需求与设计/01_架构设计/TASK-008_ERPNext集成FailClosed规范.md`

成本核算设计中建议强制适配的 DocType/能力：

- Account（会计科目）
- Cost Center（成本中心）
- Stock Ledger Entry（实际材料成本）
- Purchase Invoice（应付相关只读/草稿候选）
- Payment Entry（付款相关只读）
- GL Entry（总账只读）
- Supplier / Item / Work Order / Job Card（归属与维度校验）

必须继承的 fail-closed 语义：

- timeout / 401 / 403 / 5xx / malformed / docstatus 缺失或非法 -> fail closed；
- not found 与 unavailable 区分；
- 不得吞异常返回“空结果成功”。

---

## 7. Outbox 需要性与继续冻结项（TASK-009）

来源：`03_需求与设计/01_架构设计/TASK-009_Outbox公共状态机规范.md`、`TASK-016A`、`TASK-021A`

### 7.1 是否需要 Outbox

需要。凡成本核算触发 ERPNext 写入候选（例如未来的会计草稿、成本调整单、对账联动单据）均应接入 TASK-009 公共状态机。

### 7.2 关键约束

- `idempotency_key` 与 `event_key` 职责分离。  
- `event_key` 禁止运行态字段（attempts/status/locked_by/request_id/operator 等）。  
- claim/lease/retry/dead 必须遵守统一语义。  
- worker 外调前必须重校验本地业务状态与权限。

### 7.3 当前必须继续冻结的写入

在 `TASK-014C` 未解冻前，以下写入仍应保持冻结：

- Payment Entry 提交/取消/生产写入；
- GL Entry 创建/改写；
- Journal Entry 写入；
- 任何绕过 Adapter/Outbox 的直写 ERPNext 财务或库存动作。

---

## 8. 禁止事项候选清单（供 TASK-022A 直接复用）

1. 禁止写业务代码（本阶段仅设计冻结）。  
2. 禁止连接生产 ERPNext。  
3. 禁止直接写 ERPNext 财务/库存接口。  
4. 禁止绕过 TASK-008 Adapter。  
5. 禁止绕过 TASK-009 Outbox。  
6. 禁止 `detail=str(exc)` 泄露。  
7. 禁止 `200 + 空数据` 伪成功。  
8. 禁止把本地/mock 结果冒充平台/生产证据。  
9. 禁止在 `TASK-014C` 未闭环前推进真实平台联调写链路。  
10. 禁止声明 required checks 闭环。  
11. 禁止声明生产发布完成。  
12. 禁止跳过权限审计与操作审计。  
13. 禁止在前端暴露 diagnostic/internal/run-once 普通入口。  
14. 禁止将未结算 provisional 成本与已结算成本无标识混算。

---

## 9. 供架构师直接带入 TASK-022A 的建议骨架

1. 成本核算总边界（只设计、不实现、不联调）。  
2. 成本中心与分摊规则（组织、科目、中心、维度、版本）。  
3. 标准成本规则（BOM/工序/工价/外发标准）。  
4. 实际成本规则（SLE/工票/外发/质量损耗）。  
5. 与财务边界一致性（GL/AP/AR/Payment 只读关系）。  
6. Adapter 与 fail-closed 统一策略。  
7. Outbox 写入候选与冻结边界。  
8. 权限资源字段与审计字段。  
9. 前端门禁与导出安全。  
10. 生产发布前置条件（必须保留 `TASK-014C` 门禁）。

---

## 10. 本次准备结论

- 已完成成本核算边界设计前的资料摘录与索引。  
- 本文档不代表 `TASK-022A` 已完成。  
- 本文档不代表 `TASK-014C` 已解冻。  
- 本文档不代表生产发布完成。
