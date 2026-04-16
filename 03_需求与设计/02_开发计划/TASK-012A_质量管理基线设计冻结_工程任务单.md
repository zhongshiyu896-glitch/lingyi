# TASK-012A 质量管理基线设计冻结工程任务单

- 任务编号：TASK-012A
- 角色：工程师
- 优先级：P1
- 前置依赖：TASK-011G 审计通过（HEAD `ab5ea7bb12b7f05904eccbdda4a6cecfd7bd0614`）
- 任务类型：设计冻结（仅文档）

## 一、任务目标

冻结质量管理第一阶段基线设计，统一检验对象、质检单据、缺陷记录、权限审计、ERPNext 边界与前端门禁要求，为 TASK-012B 后端模型/接口实现提供唯一前置。

## 二、任务边界

### 2.1 允许输出
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md`
- `/Users/hh/Desktop/领意服装管理系统/03_需求与设计/02_开发计划/TASK-012A_质量管理基线设计冻结_工程任务单.md`

### 2.2 禁止修改
- `/Users/hh/Desktop/领意服装管理系统/06_前端/**`
- `/Users/hh/Desktop/领意服装管理系统/07_后端/**`
- `/Users/hh/Desktop/领意服装管理系统/.github/**`
- `/Users/hh/Desktop/领意服装管理系统/02_源码/**`

### 2.3 第一阶段允许覆盖
1. 来料检验。
2. 外发回料检验。
3. 成品检验。
4. 缺陷记录。
5. 质检结果确认。
6. 质检只读/导出。
7. 与外发验货、库存、款式、供应商只读关联。

### 2.4 第一阶段禁止覆盖
1. ERPNext Stock Entry/Purchase Receipt/Delivery Note 写入。
2. ERPNext GL/Payment/Purchase Invoice。
3. 自动扣款、自动返工、自动报废入账。
4. AQL 抽样算法深度实现。
5. 供应商绩效评分。
6. outbox。
7. 前端页面实现。
8. TASK-012B 之前写代码。

## 三、必须冻结内容

### 3.1 系统边界
文档必须明确：
1. ERPNext 负责 Item/Supplier/Warehouse/Stock Ledger 只读权威数据。
2. FastAPI 自建负责质量检验单、缺陷记录、质检统计。
3. Vue3 前端只展示质量管理页面，不直连 ERPNext。
4. 本任务仅设计冻结。

### 3.2 质检对象
必须定义并解释：
1. `incoming_material`
2. `subcontract_receipt`
3. `finished_goods`
4. `manual`

并要求 `manual` 至少带 `company/item_code`。

### 3.3 数据模型草案
必须覆盖表：
1. `ly_schema.ly_quality_inspection`
2. `ly_schema.ly_quality_inspection_item`
3. `ly_schema.ly_quality_defect`
4. `ly_schema.ly_quality_operation_log`

关键字段至少覆盖：
`company/inspection_no/source_type/source_id/item_code/supplier/warehouse/work_order/sales_order/inspection_date/inspected_qty/accepted_qty/rejected_qty/defect_qty/result/status/created_by/confirmed_by/confirmed_at`

### 3.4 状态机
冻结为：
`draft -> confirmed -> cancelled`

并明确：
1. draft 可编辑。
2. confirmed 不可改数量与缺陷明细。
3. cancelled 不参与统计。
4. confirmed 调整需取消后重建或后续 adjustment 立项。
5. 禁止直接删除 confirmed。

### 3.5 关键业务规则
必须冻结：
1. `inspected_qty = accepted_qty + rejected_qty`
2. `defect_rate = defect_qty / inspected_qty`
3. `rejected_rate = rejected_qty / inspected_qty`
4. `inspected_qty = 0` 时两率为 0
5. 数量字段不得为负
6. `accepted_qty + rejected_qty <= inspected_qty`
7. confirmed 必须校验来源 still valid
8. 来源不可用 fail closed

### 3.6 权限动作（TASK-007）
必须完整列出：
1. `quality:read`
2. `quality:create`
3. `quality:update`
4. `quality:confirm`
5. `quality:cancel`
6. `quality:export`
7. `quality:diagnostic`

### 3.7 资源权限字段
必须覆盖：
`company/item_code/supplier/warehouse/work_order/sales_order/source_type/source_id`

并明确：
1. 列表资源过滤。
2. 详情动作权限优先再资源校验。
3. 写接口校验 `company/item_code/supplier/warehouse`。
4. 来源对象校验资源归属。
5. 权限源不可用 fail closed。

### 3.8 ERPNext Fail-Closed（TASK-008）
必须冻结：
1. Item/Supplier/Warehouse 不可用 fail closed。
2. malformed response fail closed。
3. 401/403/timeout/5xx fail closed。
4. 禁止空数据伪成功。
5. 禁止信任前端传入主数据展示字段。
6. 主数据名称以 ERPNext 校验结果为准。

### 3.9 Outbox 边界（TASK-009）
必须明确：
1. TASK-012A/B/C 不实现 outbox。
2. 质量确认不直接写 ERPNext 库存。
3. 若后续要库存/财务影响，必须单独立项并遵循 TASK-009。

### 3.10 前端门禁（TASK-010）
必须冻结：
1. 模块名 `quality`。
2. 接入公共 frontend-contract-engine。
3. `fixture.positive` 与 `fixture.negative` 必填。
4. 禁止 `/api/resource`。
5. 禁止 internal/run-once/diagnostic 普通入口。
6. confirm/cancel/create/update 按钮必须绑定权限动作。

### 3.11 API 草案（TASK-012B 可实现）
1. `POST /api/quality/inspections`
2. `GET /api/quality/inspections`
3. `GET /api/quality/inspections/{id}`
4. `PATCH /api/quality/inspections/{id}`
5. `POST /api/quality/inspections/{id}/confirm`
6. `POST /api/quality/inspections/{id}/cancel`
7. `GET /api/quality/statistics`
8. `GET /api/quality/export`

### 3.12 TASK-012B 实现边界
允许：
1. 后端模型/schema/router/service。
2. 数据库迁移。
3. 权限与安全审计、操作审计、错误信封。
4. 单元测试。

禁止：
1. 前端页面。
2. ERPNext 写操作。
3. outbox。
4. 自动扣款/返工/报废。
5. 供应商评分。
6. 生产发布 / push / remote / PR。

## 四、审计前置要求

审计官必须确认：
1. 文档仅冻结设计，不含实现要求漂移。
2. 质检对象、状态机、关键公式完整。
3. 权限动作与资源字段与 TASK-007 一致。
4. ERPNext fail-closed 与 TASK-008 一致。
5. outbox 边界与 TASK-009 一致。
6. 前端门禁与 TASK-010 一致。
7. TASK-012B 允许/禁止边界清晰。

## 五、验证命令

```bash
cd /Users/hh/Desktop/领意服装管理系统
test -f "03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md"
test -f "03_需求与设计/02_开发计划/TASK-012A_质量管理基线设计冻结_工程任务单.md"
git diff --name-only -- "06_前端" "07_后端" ".github" "02_源码"
git diff --cached --name-only
```

## 六、验收标准

- [ ] TASK-012 设计文档已输出
- [ ] TASK-012A 工程任务单已输出
- [ ] 质检对象定义完整
- [ ] 数据模型草案完整
- [ ] 状态机冻结
- [ ] 关键业务公式冻结
- [ ] 权限动作完整
- [ ] 资源权限字段完整
- [ ] ERPNext fail-closed 口径完整
- [ ] Outbox 边界明确
- [ ] 前端门禁要求明确
- [ ] TASK-012B 实现边界明确
- [ ] 未修改前端代码
- [ ] 未修改后端代码
- [ ] 未修改 `.github`
- [ ] 未修改 `02_源码`
- [ ] 未暂存、未提交、未 push

## 七、执行约束

1. 本任务只输出文档，不写业务代码。
2. 不进入 TASK-012B 实现。
3. 不暂存、不提交、不 push。

## 八、交付回报格式

```text
TASK-012A 执行完成。
结论：待审计

已输出：
- /03_需求与设计/01_架构设计/TASK-012_质量管理基线设计.md
- /03_需求与设计/02_开发计划/TASK-012A_质量管理基线设计冻结_工程任务单.md

本次只输出文档。
未修改前端/后端/.github/02_源码。
未暂存、未提交、未 push。
```
