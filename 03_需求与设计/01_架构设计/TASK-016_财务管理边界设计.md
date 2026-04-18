# TASK-016 财务管理边界设计

- 任务编号：TASK-016
- 任务名称：财务管理设计冻结
- 文档版本：V1.0
- 日期：2026-04-17
- 状态：待审计

## 1. 目标

冻结财务管理模块的边界、权限、数据来源、ERPNext 集成方式、审计要求与禁止事项，为后续 Payment Entry Adapter、财务只读报表、应收应付治理提供设计基线。

## 2. 总原则

1. 财务写入必须通过 fail-closed adapter 与 outbox，不允许前端直连 ERPNext。
2. Payment Entry / GL Entry / Journal Entry 属于高风险写入，必须单独设计、单独审计、单独上线。
3. 财务只读报表优先，写入能力后置。
4. 所有财务操作必须有操作审计，权限失败必须有安全审计。
5. 本设计不实现代码，不开放任何支付、过账、冲销能力。

## 3. 范围划分

| 范围 | 本阶段定位 | 说明 |
|---|---|---|
| Accounts Receivable | 设计冻结 | 应收账龄、客户余额、销售单据只读 |
| Accounts Payable | 设计冻结 | 供应商应付、Purchase Invoice 草稿状态只读 |
| Payment Entry | 后续独立设计 | 禁止本阶段实现 |
| GL Entry | 只读分析 | 禁止写入 |
| Journal Entry | 不进入 Sprint 3 P1 | 需要独立审计 |
| Cost Center / Account | 主数据只读 | 必须校验 company 归属 |

## 4. 权限动作

建议权限动作矩阵：

| 动作 | 类型 | 说明 |
|---|---|---|
| `finance:read` | 读 | 财务只读报表 |
| `finance:export` | 导出 | 导出只读报表，必须脱敏与 CSV 注入防护 |
| `finance:diagnostic` | 诊断 | 仅管理员可用，必须操作审计 |
| `finance:payment_draft_create` | 写 | 后续 Payment Entry 草稿设计，默认冻结 |
| `finance:payment_cancel` | 写 | 后续独立设计，默认冻结 |

## 5. 资源权限字段

| 字段 | 必填场景 | 说明 |
|---|---|---|
| company | 全部 | 财务资源必须归属公司 |
| customer | 应收 | 客户维度权限 |
| supplier | 应付 | 供应商维度权限 |
| account | GL/账户 | 必须匹配 company |
| cost_center | 成本中心 | 必须匹配 company |
| currency | 多币种 | 只读展示，不作为授权唯一依据 |

未知资源字段必须 fail closed。

## 6. ERPNext 集成边界

| ERPNext DocType | 本阶段能力 | 写入限制 |
|---|---|---|
| Sales Invoice | 只读 | 禁止 submit/cancel |
| Purchase Invoice | 只读/草稿状态读取 | 禁止 submit |
| Payment Entry | 不实现 | 禁止创建 |
| GL Entry | 只读 | 禁止创建 |
| Account | 只读 | 禁止修改 |
| Cost Center | 只读 | 禁止修改 |

所有 ERPNext 访问必须使用 TASK-008 fail-closed adapter。

## 7. Outbox 规则

未来如实现金融写入，必须使用 TASK-009 公共 outbox 状态机：

1. `event_key` 不得包含 idempotency、attempts、locked_by、status 等运行态字段。
2. worker 外调前必须重新校验本地聚合状态、权限、金额、资源归属。
3. 本地 claim 提交后才允许外调。
4. 成功写入 ERPNext 后必须记录 external_docname / docstatus。
5. failed/dead 重建必须单独任务设计。

## 8. 报表口径

| 报表 | 口径 |
|---|---|
| 应收账龄 | 以 ERPNext Sales Invoice / Payment Entry 只读数据为准 |
| 应付账龄 | 以 Purchase Invoice / Payment Entry 只读数据为准 |
| 现金流预估 | 仅读取已确认业务单据，不做自动支付 |
| GL 明细 | 仅读取 GL Entry，不写入 |

## 9. 前端门禁

后续前端必须接入 TASK-010 公共门禁：

1. 禁止 `/api/resource`。
2. 禁止 Payment Entry / GL Entry 写入口出现在未审计页面。
3. 导出必须防 CSV 公式注入。
4. diagnostic 不得向普通角色暴露。
5. 每条规则必须有 positive / negative fixture。

## 10. 审计关注点

1. 是否存在财务写入绕过 outbox。
2. 是否存在前端直连 ERPNext。
3. 是否混淆草稿创建与 submit。
4. 是否错误声明生产支付能力已完成。
5. 是否泄露账户、token、DSN、Cookie。

## 11. 结论

本设计建议进入 TASK-016A 审计。审计通过后，只允许继续 TASK-016B Payment Entry Adapter 设计，不允许直接实现。
