# 前端页面接口交接清单

范围：仅用于后端预备与前端接入对表。所有业务请求使用既有 dev 鉴权头 `X-LY-Dev-User`、`X-LY-Dev-Roles: System Manager`；不需要新增鉴权头。

| 模块 | 页面节点 | 方法 | URL | 关键字段 | dev seed |
| --- | --- | --- | --- | --- | --- |
| 基础资料 | 客户 | GET | `/api/sales-inventory/customers` | `name, customer_name, disabled` | 是 |
| 基础资料 | 供应商 | GET | `/api/sales-inventory/suppliers` | `name, supplier_name, disabled` | 真实 |
| 基础资料 | 加工厂 | GET | `/api/subcontract/factories` | `factory_name, factory_code, review_status` | 是 |
| 基础资料 | 仓库 | GET | `/api/sales-inventory/warehouses` | `name, company, warehouse_name, disabled` | 真实 |
| 基础资料 | 供应商评估 | GET | `/api/factory-statements/supplier-evaluations` | `evaluation_no, supplier, score, review_status` | 是 |
| 基础资料 | 加工厂评估 | GET | `/api/factory-statements/factory-evaluations` | `evaluation_no, factory_name, score, review_status` | 是 |
| 物料开发 | BOM | GET | `/api/bom/` | `bom_no, item_code, version_no, status` | 既有 |
| 物料开发 | 物料档案 | GET | `/api/bom/materials` | `item_code, material_item_code, material_type_name` | 真实 |
| 物料开发 | 物料分类 | GET | `/api/bom/material-categories` | `material_type_code, material_type_name, material_group` | 真实 |
| 物料开发 | 物料单位 | GET | `/api/bom/units` | `unit_code, unit_name, base_unit, precision` | 真实 |
| 物料开发 | 颜色 | GET | `/api/bom/colors` | `dict_type, dict_code, dict_name, status` | 是 |
| 物料开发 | 尺码 | GET | `/api/bom/sizes` | `dict_type, dict_code, dict_name, status` | 是 |
| 物料开发 | 款式档案 | GET | `/api/bom/styles` | `bom_no, item_code, version_no` | 真实 |
| 物料开发 | 物料图库 | GET | `/api/bom/material-gallery` | `bom_no, material_item_code, qty_per_piece` | 是 |
| 物料开发 | 面料 | GET | `/api/bom/fabrics` | `fabric_name, material_item_code, supplier_name` | 是 |
| 物料开发 | 辅料包材 | GET | `/api/bom/accessories-packaging` | `material_name, category, supplier_name` | 是 |
| 物料开发 | 采购单 | GET | `/api/bom/purchase-orders` | `purchase_no, supplier_name, total_amount` | 是 |
| 物料开发 | 款式-BOM-工艺 | GET | `/api/bom/style-bom-process` | `bom_no, item_code, process_name, unit_rate` | 真实 |
| 基础资料 | 工艺要求模板 | GET | `/api/bom/process-requirement-templates` | `id, template_code, name, status, nodes` | 真实 |
| 基础资料 | 尺寸表模板 | GET | `/api/bom/size-chart-templates` | `id, template_code, name, status, nodes` | 真实 |
| 物料开发 | 打样进度 | GET | `/api/bom/sample-progress` | `sample_order_no, sample_type, item_code, status` | 是 |
| 销售生产 | 销售订单 | GET | `/api/sales-inventory/sales-orders` | `name, customer, transaction_date, grand_total` | 是 |
| 销售生产 | 生产计划 | GET | `/api/production/plans` | `plan_no, sales_order, item_code, planned_qty` | 是 |
| 销售生产 | 工单 | GET | `/api/production/work-orders` | `work_order, sales_order, planned_qty, produced_qty` | 真实 |
| 销售生产 | 工单领料 | GET | `/api/production/material-issues` | `work_order, material_item_code, required_qty, issued_qty` | 是 |
| 销售生产 | 收发数量 | GET | `/api/production/order-io-quantities` | `inbound_qty, outbound_qty, io_status` | 是 |
| 销售生产 | 工单轨迹 | GET | `/api/cross-module/work-order-trail/WO-FR-001?company=LY-FRONTEND-DEV` | `work_order, stock_entries, quality_inspections, summary` | 是 |
| 采购闭环 | 请购 | GET | `/api/bom/material-requests` | `request_no, material_item_code, qty, status` | 是 |
| 采购闭环 | 采购入库 | GET | `/api/warehouse/purchase-receipts` | `receipt_no, purchase_no, received_qty` | 真实 |
| 采购闭环 | 采购发票 | GET | `/api/factory-statements/purchase-invoices` | `purchase_invoice_name, grand_total, outstanding_amount` | 真实 |
| 采购闭环 | 供应商应付 | GET | `/api/factory-statements/supplier-payable-summaries` | `summary_no, supplier, ending_payable` | 是 |
| 外发加工 | 外发单 | GET | `/api/subcontract/` | `subcontract_no, supplier, item_code, status` | 既有 |
| 外发加工 | 外发发料 | GET | `/api/subcontract/material-issues` | `subcontract_no, material_item_code, issued_qty` | 是 |
| 外发加工 | 外发收货 | GET | `/api/subcontract/receipts` | `subcontract_no, receipt_batch_no, accepted_qty` | 是 |
| 外发加工 | 应退料 | GET | `/api/subcontract/return-materials` | `subcontract_no, planned_return_qty, returned_qty` | 真实 |
| 外发加工 | 结算候选 | GET | `/api/subcontract/settlement-candidates` | `subcontract_no, receipt_batch_no, net_amount` | 是 |
| 外发加工 | 加工厂对账 | GET | `/api/factory-statements/factory-reconciliations` | `reconciliation_no, factory_name, pending_amount` | 是 |
| 外发加工 | 加工厂应付 | GET | `/api/factory-statements/factory-payable-summaries` | `summary_no, factory_name, ending_payable` | 是 |
| 库存财务 | 库存台账 | GET | `/api/warehouse/stock-ledger` | `item_code, warehouse, actual_qty, qty_after_transaction` | 既有 |
| 库存财务 | 库存快照 | GET | `/api/warehouse/stock-summary?company=LY-FRONTEND-DEV` | `warehouse, item_code, actual_qty, projected_qty` | 是 |
| 库存财务 | 完工入库 | GET | `/api/warehouse/finished-goods-inbound` | `reservation_no, inbound_qty, pending_inbound_qty` | 真实 |
| 库存财务 | 发货单 | GET | `/api/sales-inventory/delivery-notes` | `delivery_note, sales_order, delivered_qty` | 真实 |
| 库存财务 | 销售发票 | GET | `/api/sales-inventory/sales-invoices` | `sales_invoice, grand_total, outstanding_amount` | 真实 |
| 库存财务 | 应收 | GET | `/api/factory-statements/customer-receivables` | `summary_no, customer_code, ending_receivable` | 真实 |
| 库存财务 | 账实平 | GET | `/api/warehouse/inventory-balance-reconciliation` | `warehouse, item_code, book_qty, actual_qty, diff_qty` | 真实 |
| 质检工票 | 质检列表 | GET | `/api/quality/inspections` | `inspection_no, inspected_qty, accepted_qty, rejected_qty` | 是 |
| 质检工票 | 质检统计 | GET | `/api/quality/statistics` | `total_count, total_inspected_qty, overall_defect_rate` | 是 |
| 质检工票 | 质检趋势 | GET | `/api/quality/statistics/trend` | `period, points` | 是 |
| 质检工票 | 工票 | GET | `/api/workshop/tickets` | `ticket_no, job_card, employee, wage_amount` | 是 |
| 质检工票 | 计件工资 | GET | `/api/workshop/daily-wages` | `employee, net_qty, wage_amount` | 是 |
| 报表看板 | 首页总览 | GET | `/api/dashboard/overview` | `company, quality, sales_inventory, warehouse, home_overview` | 是 |
| 报表看板 | 报表目录 | GET | `/api/reports/catalog` | `report_key, name, report_type, status` | 是 |
| 报表看板 | 员工任务统计 | GET | `/api/reports/employee-task-statistics` | `employee_id, pending_tasks, completion_rate` | 是 |
| 报表看板 | 审批报表 | GET | `/api/reports/approval-reports` | `approval_no, approval_type, approver, status` | 是 |
| 报表看板 | 审批流程 | GET | `/api/system/approval-flows` | `flow_key, title, audit_type, nodes, actions` | 是 |
| 报表看板 | 款式成本 | GET | `/api/style-profit/style-costs` | `snapshot_no, item_code, actual_total_cost, profit_amount` | 真实 |
| 报表看板 | 订单毛利 | GET | `/api/reports/style-profit/snapshots?company=LY-FRONTEND-DEV&item_code=ITEM-FR-001` | `snapshot_no, sales_order, profit_amount, profit_rate` | 是 |

说明：`*/readiness/*-flow` 的 POST 端点只用于 dev 闭环联调回执，不代表生产写闭环已上线。
