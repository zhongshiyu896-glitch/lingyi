# TASK-012 质量管理基线设计

- 模块：质量管理基线
- 版本：V1.0（设计冻结）
- 更新时间：2026-04-16
- 前置：TASK-011G 审计通过（HEAD `ab5ea7bb12b7f05904eccbdda4a6cecfd7bd0614`）
- 适用范围：TASK-012B 实现阶段与后续 TASK-012 系列任务

## 一、目标与边界

### 1.1 目标
冻结质量管理第一阶段基线设计，统一检验对象、质检单据、缺陷记录、权限审计、ERPNext 边界和前端门禁要求，作为 TASK-012B 工程实现唯一前置。

### 1.2 第一阶段允许范围
1. 来料检验。
2. 外发回料检验。
3. 成品检验。
4. 缺陷记录。
5. 质检结果确认。
6. 质检只读/导出。
7. 与外发验货、库存、款式、供应商只读关联。

### 1.3 第一阶段禁止范围
1. ERPNext Stock Entry 写入。
2. ERPNext Purchase Receipt 写入。
3. ERPNext Delivery Note 写入。
4. ERPNext GL / Payment / Purchase Invoice。
5. 自动扣款结算。
6. 自动返工工单。
7. 自动报废入账。
8. AQL 抽样算法深度实现。
9. 供应商绩效评分。
10. outbox。
11. 前端页面实现。
12. TASK-012B 之前写代码。

## 二、系统边界与职责

### 2.1 系统边界
1. ERPNext：负责 Item、Supplier、Warehouse、Stock Ledger 等只读权威主数据与事实数据。
2. FastAPI：负责质检主数据、检验单、缺陷记录、统计查询与权限过滤。
3. Vue3：负责质量管理页面展示（后续任务实现），不直连 ERPNext。
4. TASK-012A：仅设计冻结，不实现业务代码。

### 2.2 权威数据原则
1. 前端提交的 `supplier/warehouse/item_name` 等展示信息不得作为可信业务事实。
2. 所有主数据名称、有效性与归属关系以 ERPNext 只读校验结果为准。

## 三、质检对象定义（冻结）

| 来源类型 | source_type | 说明 |
|---|---|---|
| 来料检验 | `incoming_material` | 采购/来料场景，第一阶段只关联 ERPNext 只读数据 |
| 外发回料检验 | `subcontract_receipt` | 关联 TASK-002 外发回料/验货数据 |
| 成品检验 | `finished_goods` | 关联款式、生产或库存只读数据 |
| 手工检验 | `manual` | 无强来源时手工登记，但必须有 `company/item_code` |

## 四、数据模型草案（冻结）

| 表名 | 用途 |
|---|---|
| `ly_schema.ly_quality_inspection` | 质量检验主表 |
| `ly_schema.ly_quality_inspection_item` | 抽检/明细行 |
| `ly_schema.ly_quality_defect` | 缺陷记录 |
| `ly_schema.ly_quality_operation_log` | 操作审计/业务日志 |

### 4.1 关键字段（最小集合）
必须覆盖：
1. `company`
2. `inspection_no`
3. `source_type`
4. `source_id`
5. `item_code`
6. `supplier`
7. `warehouse`
8. `work_order`
9. `sales_order`
10. `inspection_date`
11. `inspected_qty`
12. `accepted_qty`
13. `rejected_qty`
14. `defect_qty`
15. `result`
16. `status`
17. `created_by`
18. `confirmed_by`
19. `confirmed_at`

## 五、状态机（冻结）

```text
draft -> confirmed -> cancelled
```

规则：
1. `draft` 可编辑。
2. `confirmed` 后不可修改检验数量和缺陷明细。
3. `cancelled` 不参与统计。
4. confirmed 后若需调整，必须取消后重建；adjustment 另行立项。
5. 禁止直接删除 confirmed 记录。

## 六、关键业务规则（冻结）

1. `inspected_qty = accepted_qty + rejected_qty`
2. `defect_rate = defect_qty / inspected_qty`
3. `rejected_rate = rejected_qty / inspected_qty`
4. `inspected_qty = 0` 时，`defect_rate = 0` 且 `rejected_rate = 0`
5. `accepted_qty/rejected_qty/defect_qty` 不得为负
6. `accepted_qty + rejected_qty` 不得超过 `inspected_qty`
7. `confirmed` 时必须校验来源对象 still valid
8. 来源不可用必须 fail closed，不得确认

## 七、权限动作与资源权限（引用 TASK-007）

### 7.1 动作权限
| 动作 | 说明 |
|---|---|
| `quality:read` | 读取质检单与统计 |
| `quality:create` | 创建质检单 |
| `quality:update` | 修改 draft 质检单 |
| `quality:confirm` | 确认质检单 |
| `quality:cancel` | 取消质检单 |
| `quality:export` | 导出质量报表 |
| `quality:diagnostic` | 质量模块诊断，普通用户禁用 |

### 7.2 资源权限字段
必须覆盖：
1. `company`
2. `item_code`
3. `supplier`
4. `warehouse`
5. `work_order`
6. `sales_order`
7. `source_type`
8. `source_id`

### 7.3 资源权限规则
1. 列表接口必须资源过滤。
2. 详情接口必须动作权限优先，再资源权限校验。
3. 写接口必须校验 `company/item_code/supplier/warehouse` 资源权限。
4. 来源对象必须校验资源归属关系。
5. 权限源不可用必须 fail closed。

## 八、ERPNext Fail-Closed（引用 TASK-008）

1. Item/Supplier/Warehouse 任一主数据不可用时 fail closed。
2. ERPNext response malformed 必须 fail closed。
3. ERPNext 401/403/timeout/5xx 必须 fail closed。
4. 禁止通过空数据伪成功。
5. 禁止直接信任前端传入主数据展示字段。
6. 主数据名称与标识以 ERPNext 校验结果为准。

## 九、Outbox 边界（引用 TASK-009）

1. TASK-012A/B/C 不实现 outbox。
2. 质量确认不直接写 ERPNext 库存。
3. 如后续需要库存/财务影响，必须单独立项并遵循 TASK-009 状态机规范。

## 十、前端门禁要求（引用 TASK-010）

1. 模块配置名固定为 `quality`。
2. 必须接入公共 `frontend-contract-engine`。
3. 必须声明 `fixture.positive` 与 `fixture.negative`。
4. 禁止 ERPNext `/api/resource` 直连。
5. 禁止 internal/run-once/diagnostic 普通入口。
6. 写入口必须只调用 FastAPI 自建接口。
7. confirm/cancel/create/update 按钮必须绑定权限动作。

## 十一、TASK-012B 接口草案（冻结）

| 接口 | 方法 | 路径 |
|---|---|---|
| 创建质检单 | POST | `/api/quality/inspections` |
| 质检单列表 | GET | `/api/quality/inspections` |
| 质检单详情 | GET | `/api/quality/inspections/{id}` |
| 修改 draft | PATCH | `/api/quality/inspections/{id}` |
| 确认质检单 | POST | `/api/quality/inspections/{id}/confirm` |
| 取消质检单 | POST | `/api/quality/inspections/{id}/cancel` |
| 质量统计 | GET | `/api/quality/statistics` |
| 质量导出 | GET | `/api/quality/export` |

## 十二、错误信封与审计要求

### 12.1 错误信封
```json
{
  "code": "ERROR_CODE",
  "message": "可读错误信息",
  "data": null
}
```

### 12.2 安全审计
必须覆盖：
1. 未认证。
2. 动作权限拒绝。
3. 资源越权。
4. 权限源不可用。
5. 外部依赖不可用。
6. internal diagnostic 越权访问。

### 12.3 操作审计
第一阶段重点覆盖：
1. `create`
2. `update`
3. `confirm`
4. `cancel`
5. `export`
6. `diagnostic`

## 十三、TASK-012B 实现边界（冻结）

### 13.1 允许
1. 后端模型/schema/router/service。
2. 数据库迁移。
3. 权限与安全审计。
4. 操作审计。
5. 错误信封。
6. 单元测试。

### 13.2 禁止
1. 前端页面。
2. ERPNext 写操作。
3. outbox。
4. 自动扣款/返工/报废。
5. 供应商评分。
6. 生产发布 / push / remote / PR。

## 十四、实现前检查清单（给 TASK-012B）

- [ ] 检验来源类型与字段冻结一致
- [ ] 状态机仅 `draft/confirmed/cancelled`
- [ ] 核心数量公式与非负约束已落地
- [ ] 权限动作与资源字段与 TASK-007 一致
- [ ] ERPNext fail-closed 与 TASK-008 一致
- [ ] 无 outbox（遵循 TASK-009 边界）
- [ ] 前端门禁要求与 TASK-010 对齐
