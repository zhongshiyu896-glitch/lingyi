# 后端接口资产分类清单

来源：FastAPI `app.routes` 自动导出；readiness/stub 以 `app/routers/frontend_readiness.py` 为准。

- A 类真实业务接口：178
- B 类 dev/test readiness 只读接口：27
- C 类 readiness flow 回执桩：7
- D 类内部/诊断/不建议前端直连接口：11

| 类别 | Method | Path | 分页 | 登录 | 真实写库 | 前端接入状态 | 响应字段摘要 | 风险说明 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A | GET | `/api/auth/actions` | 否 | 是 | 否 | candidate | - | 认证/会话真实接口 |
| A | GET | `/api/auth/actions/bom/{bom_id}` | 否 | 是 | 否 | candidate | - | 认证/会话真实接口 |
| A | POST | `/api/auth/login` | 否 | 否 | 否 | needs_dedicated_write_task | - | 认证/会话真实接口 |
| A | POST | `/api/auth/logout` | 否 | 否 | 否 | needs_dedicated_write_task | - | 认证/会话真实接口 |
| A | GET | `/api/auth/me` | 否 | 是 | 否 | candidate | - | 认证/会话真实接口 |
| A | GET | `/api/bom/` | 是 | 是 | 否 | candidate | id, bom_no, item_code, version_no, is_default, status, effective_date | 真实业务只读接口候选 |
| A | POST | `/api/bom/` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/bom/accessories-packaging` | 是 | 是 | 否 | candidate | id, bom_id, bom_no, item_code, material_item_code, material_name, category, color, specification, supplier_name, uom, qty_per_piece, ... | 真实业务只读接口候选 |
| B | GET | `/api/bom/colors` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/bom/fabrics` | 是 | 是 | 否 | candidate | id, bom_id, bom_no, item_code, material_item_code, fabric_name, color, specification, supplier_name, uom, qty_per_piece, loss_rate, ... | 真实业务只读接口候选 |
| A | GET | `/api/bom/material-categories` | 是 | 是 | 否 | candidate | dict_type, dict_code, dict_name, status, source, updated_at | 真实业务只读接口候选 |
| A | GET | `/api/bom/material-deduction` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/bom/material-gallery` | 是 | 是 | 否 | candidate | id, bom_id, bom_no, item_code, material_item_code, category, color, size, uom, qty_per_piece, loss_rate, status, ... | 真实业务只读接口候选 |
| A | GET | `/api/bom/material-processing` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/bom/material-processing-inbound` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| B | GET | `/api/bom/material-requests` | 是 | 是 | 否 | temporary_dev_only | request_no, company, item_code, material_item_code, supplier_name, qty, uom, expected_delivery_date, status, bom_no | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/bom/material-sales-outbound` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/bom/material-types` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/bom/material-units` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/bom/materials` | 是 | 是 | 否 | candidate | id, bom_id, bom_no, item_code, material_item_code, material_type_code, material_type_name, material_group, applicable_scene, supplier_name, status, is_default | 真实业务只读接口候选 |
| A | GET | `/api/bom/process-requirement-templates` | 是 | 是 | 否 | candidate | process_type_code, process_type_name, process_name, sequence_no, subcontract_mode, pricing_mode, unit_rate, status, is_default | 真实业务只读接口候选 |
| A | GET | `/api/bom/processing-types` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/bom/purchase-orders` | 是 | 是 | 否 | candidate | id, bom_id, purchase_no, supplier_name, item_code, material_item_code, material_name, qty, uom, unit_price, total_amount, expected_delivery_date, ... | 真实业务只读接口候选 |
| C | POST | `/api/bom/readiness/procurement-flow` | 否 | 是 | 否 | do_not_connect_as_write | request_no, purchase_no, receipt_no, purchase_invoice_name, supplier, supplier_name, item_code, material_item_code, received_qty, grand_total, outstanding_amount, status | readiness flow 回执桩; 不得当作真实写接口 |
| B | GET | `/api/bom/sample-orders` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/bom/sample-progress` | 是 | 是 | 否 | temporary_dev_only | id, sample_order_no, sample_type, item_code, status, owner, updated_at | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/bom/sample-types` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/bom/size-chart-templates` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/bom/size-sortings` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/bom/sizes` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/bom/style-bom-process` | 是 | 是 | 否 | candidate | id, bom_id, bom_no, item_code, version_no, process_type_code, process_type_name, process_name, sequence_no, subcontract_mode, pricing_mode, unit_rate, ... | 真实业务只读接口候选 |
| A | GET | `/api/bom/styles` | 是 | 是 | 否 | candidate | id, bom_no, item_code, version_no, is_default, status, effective_date | 真实业务只读接口候选 |
| A | GET | `/api/bom/units` | 是 | 是 | 否 | candidate | dict_type, dict_code, dict_name, status, source, updated_at | 真实业务只读接口候选 |
| A | GET | `/api/bom/{bom_id}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | PUT | `/api/bom/{bom_id}` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/bom/{bom_id}/activate` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/bom/{bom_id}/deactivate` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/bom/{bom_id}/explode` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/bom/{bom_id}/set-default` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/cross-module/sales-order-trail/{sales_order_id}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/cross-module/work-order-trail/{work_order_id}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/dashboard/overview` | 否 | 是 | 否 | candidate | company, from_date, to_date, generated_at, quality, sales_inventory, warehouse, source_status, kanban, home_overview | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/factory-statements/` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/factory-statements/bank-deposits` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/bank-ledgers` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/bank-withdrawals` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| B | GET | `/api/factory-statements/cashier-accounts` | 是 | 是 | 否 | temporary_dev_only | bank_name, account_name, account_no, currency, owner, remark | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/factory-statements/customer-evaluations` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/customer-receivable-summaries` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/customer-receivables` | 是 | 是 | 否 | candidate | summary_no, statement_no, company, customer_name, customer_code, currency, opening_receivable, current_receivable, received_amount, ending_receivable, aging_30, aging_60, ... | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/customer-reconciliations` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/customer-unpaid-reports` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/expense-reimbursement-payments` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| B | GET | `/api/factory-statements/expense-types` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/factory-statements/factory-evaluations` | 是 | 是 | 否 | candidate | evaluation_no, statement_no, company, supplier, factory_name, factory_code, assessor, score, score_level, review_status, follow_up_status, evaluation_date, ... | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/factory-payable-summaries` | 是 | 是 | 否 | candidate | summary_no, statement_no, company, supplier, factory_name, factory_code, currency, opening_payable, current_payable, paid_amount, ending_payable, aging_30, ... | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/factory-reconciliations` | 是 | 是 | 否 | candidate | reconciliation_no, statement_no, company, supplier, factory_name, factory_code, currency, reconciliation_amount, settled_amount, pending_amount, settlement_status, review_status, ... | 真实业务只读接口候选 |
| D | POST | `/api/factory-statements/internal/payable-draft-sync/run-once` | 否 | 是 | 否 | not_for_page_direct_use | - | 内部 worker/运维接口; 不给前端页面直接接入 |
| B | GET | `/api/factory-statements/invoice-types` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/factory-statements/purchase-invoices` | 是 | 是 | 否 | temporary_dev_only | purchase_invoice_name, company, supplier, supplier_name, currency, grand_total, paid_amount, outstanding_amount, status, posting_date | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/factory-statements/settlement-methods` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/factory-statements/supplier-evaluations` | 是 | 是 | 否 | candidate | evaluation_no, statement_no, company, supplier, supplier_code, assessor, score, score_level, review_status, follow_up_status, evaluation_date, expiry_date, ... | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/supplier-payable-summaries` | 是 | 是 | 否 | candidate | summary_no, statement_no, company, supplier, supplier_code, currency, opening_payable, current_payable, paid_amount, ending_payable, aging_30, aging_60, ... | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/supplier-reconciliations` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/factory-statements/{statement_id}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/factory-statements/{statement_id}/cancel` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/factory-statements/{statement_id}/confirm` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/factory-statements/{statement_id}/payable-draft` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/permissions/actions/catalog` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/permissions/audit/operations` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/permissions/audit/operations/export` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/permissions/audit/security` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/permissions/audit/security/export` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| D | GET | `/api/permissions/diagnostic` | 否 | 是 | 否 | not_for_page_direct_use | - | 诊断接口; 运维排障用途 |
| A | GET | `/api/permissions/menu-management` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/permissions/roles/matrix` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/production/followup-templates` | 是 | 是 | 否 | candidate | template_id, template_no, template_name, template_type, trigger_node, followup_role, followup_frequency, sla_hours, item_code, company, status, updated_at | 真实业务只读接口候选 |
| B | GET | `/api/production/followup-templates` | 是 | 是 | 否 | temporary_dev_only | template_id, template_no, template_name, template_type, trigger_node, followup_role, followup_frequency, sla_hours, item_code, company, status, updated_at | dev/test only; 生产环境必须关闭 |
| D | POST | `/api/production/internal/work-order-sync/run-once` | 否 | 是 | 否 | not_for_page_direct_use | code, message, data, data.dry_run, data.processed_count, data.succeeded_count, data.failed_count, data.dead_count | 内部 worker/运维接口; 不给前端页面直接接入 |
| A | GET | `/api/production/material-cost-details` | 是 | 是 | 否 | candidate | code, message, data, data.items, data.items.plan_id, data.items.plan_no, data.items.company, data.items.sales_order, data.items.sales_order_item, data.items.item_code, data.items.material_item_code, data.items.supplier, ... | 真实业务只读接口候选 |
| B | GET | `/api/production/material-issues` | 是 | 是 | 否 | temporary_dev_only | plan_id, plan_no, work_order, company, item_code, material_item_code, warehouse, required_qty, available_qty, issued_qty, shortage_qty, status | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/production/order-io-quantities` | 是 | 是 | 否 | candidate | plan_id, plan_no, company, sales_order, sales_order_item, customer, item_code, ordered_qty, inbound_qty, outbound_qty, pending_inbound_qty, pending_outbound_qty, ... | 真实业务只读接口候选 |
| A | GET | `/api/production/plans` | 是 | 是 | 否 | candidate | id, plan_no, company, sales_order, sales_order_item, customer, item_code, bom_id, bom_version, planned_qty, planned_start_date, status, ... | 真实业务只读接口候选 |
| A | POST | `/api/production/plans` | 否 | 是 | 是 | needs_dedicated_write_task | code, message, data, data.plan_id, data.plan_no, data.status, data.company | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/production/plans/{plan_id}` | 否 | 是 | 否 | candidate | code, message, data, data.id, data.plan_no, data.company, data.sales_order, data.sales_order_item, data.customer, data.item_code, data.bom_id, data.bom_version, ... | 真实业务只读接口候选 |
| A | POST | `/api/production/plans/{plan_id}/create-work-order` | 否 | 是 | 是 | needs_dedicated_write_task | code, message, data, data.plan_id, data.outbox_id, data.event_key, data.sync_status, data.work_order | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/production/plans/{plan_id}/material-check` | 否 | 是 | 是 | needs_dedicated_write_task | code, message, data, data.plan_id, data.snapshot_count, data.items, data.items.bom_item_id, data.items.material_item_code, data.items.warehouse, data.items.qty_per_piece, data.items.loss_rate, data.items.required_qty, ... | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/production/quotes` | 是 | 是 | 否 | candidate | code, message, data, data.items, data.items.plan_id, data.items.quote_no, data.items.plan_no, data.items.company, data.items.sales_order, data.items.sales_order_item, data.items.customer, data.items.item_code, ... | 真实业务只读接口候选 |
| C | POST | `/api/production/readiness/inventory-finance-flow` | 否 | 是 | 否 | do_not_connect_as_write | reservation_no, delivery_note, sales_invoice, summary_no, warehouse, item_code, inbound_qty, delivered_qty, book_qty, actual_qty, diff_qty, outstanding_amount, ... | readiness flow 回执桩; 不得当作真实写接口 |
| C | POST | `/api/production/readiness/work-order-flow` | 否 | 是 | 否 | do_not_connect_as_write | plan_id, plan_no, outbox_id, event_key, sync_status, work_order, sales_order, sales_order_item, item_code, planned_qty, status | readiness flow 回执桩; 不得当作真实写接口 |
| A | GET | `/api/production/sales-forecast-details` | 是 | 是 | 否 | candidate | code, message, data, data.items, data.items.plan_id, data.items.plan_no, data.items.company, data.items.sales_order, data.items.sales_order_item, data.items.customer, data.items.item_code, data.items.forecast_qty, ... | 真实业务只读接口候选 |
| A | GET | `/api/production/salesperson-performance` | 是 | 是 | 否 | candidate | code, message, data, data.items, data.items.plan_id, data.items.plan_no, data.items.company, data.items.salesperson, data.items.sales_order, data.items.sales_order_item, data.items.customer, data.items.item_code, ... | 真实业务只读接口候选 |
| A | GET | `/api/production/work-orders` | 是 | 是 | 否 | candidate | plan_id, plan_no, company, sales_order, sales_order_item, customer, item_code, bom_id, bom_version, work_order, planned_qty, produced_qty, ... | 真实业务只读接口候选 |
| A | POST | `/api/production/work-orders/{work_order}/sync-job-cards` | 否 | 是 | 是 | needs_dedicated_write_task | code, message, data, data.work_order, data.plan_id, data.synced_count, data.items, data.items.job_card, data.items.operation, data.items.operation_sequence, data.items.company, data.items.item_code, ... | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| D | GET | `/api/quality/diagnostic` | 否 | 是 | 否 | not_for_page_direct_use | - | 诊断接口; 运维排障用途 |
| A | GET | `/api/quality/export` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/quality/inspections` | 是 | 是 | 否 | candidate | id, inspection_no, company, source_type, source_id, item_code, supplier, warehouse, inspection_date, inspected_qty, accepted_qty, rejected_qty, ... | 真实业务只读接口候选 |
| A | POST | `/api/quality/inspections` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/quality/inspections/{inspection_id}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | PATCH | `/api/quality/inspections/{inspection_id}` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/quality/inspections/{inspection_id}/cancel` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/quality/inspections/{inspection_id}/confirm` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/quality/inspections/{inspection_id}/defects` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/quality/inspections/{inspection_id}/outbox-status` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| D | POST | `/api/quality/internal/outbox-sync/run-once` | 否 | 是 | 否 | not_for_page_direct_use | - | 内部 worker/运维接口; 不给前端页面直接接入 |
| C | POST | `/api/quality/readiness/quality-flow` | 否 | 是 | 否 | do_not_connect_as_write | inspection_no, work_order, subcontract_no, item_code, inspected_qty, accepted_qty, rejected_qty, status | readiness flow 回执桩; 不得当作真实写接口 |
| A | GET | `/api/quality/statistics` | 否 | 是 | 否 | candidate | total_count, total_inspected_qty, total_accepted_qty, total_rejected_qty, total_defect_qty, overall_defect_rate, inspected_qty, accepted_qty, rejected_qty, defect_qty, defect_rate, rejected_rate, ... | 真实业务只读接口候选 |
| A | GET | `/api/quality/statistics/trend` | 否 | 是 | 否 | candidate | period, points.period_key, points.inspection_count, points.defect_rate, points.rejected_rate, points.total_inspected_qty | 真实业务只读接口候选 |
| A | GET | `/api/reports/approval-reports` | 否 | 是 | 否 | candidate | approval_no, approval_type, related_doc_no, applicant, approver, department, amount, priority, submitted_at, completed_at, status, remark | 真实业务只读接口候选 |
| A | GET | `/api/reports/catalog` | 否 | 是 | 否 | candidate | report_key, name, source_modules, report_type, required_filters, optional_filters, metric_summary, permission_action, status, ui_placeholders, ui_buttons, ui_table_headers, ... | 真实业务只读接口候选 |
| A | GET | `/api/reports/catalog/export` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/reports/catalog/{report_key}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| D | GET | `/api/reports/diagnostic` | 否 | 是 | 否 | not_for_page_direct_use | - | 诊断接口; 运维排障用途 |
| A | GET | `/api/reports/employee-task-statistics` | 否 | 是 | 否 | candidate | employee_id, employee_name, department, pending_tasks, in_progress_tasks, completed_tasks, overdue_tasks, completion_rate, latest_task_no, latest_task_title, latest_due_date, updated_at, ... | 真实业务只读接口候选 |
| A | GET | `/api/reports/style-profit/snapshots` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/reports/style-profit/snapshots` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/reports/style-profit/snapshots/{snapshot_id}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/aggregation` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/customer-return-applications` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/customer-return-inbound` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/customers` | 是 | 是 | 否 | candidate | name, customer_name, disabled | 真实业务只读接口候选 |
| B | GET | `/api/sales-inventory/delivery-addresses` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/sales-inventory/delivery-notes` | 是 | 是 | 否 | temporary_dev_only | delivery_note, company, sales_order, customer, item_code, warehouse, delivered_qty, posting_date, status | dev/test only; 生产环境必须关闭 |
| D | GET | `/api/sales-inventory/diagnostic` | 否 | 是 | 否 | not_for_page_direct_use | - | 诊断接口; 运维排障用途 |
| A | GET | `/api/sales-inventory/finished-goods-adjustment` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/finished-goods-count` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/finished-goods-other-inbound` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/finished-goods-other-outbound` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/finished-goods-report` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/finished-goods-reserved-inbound` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/finished-goods-shipping-notices` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/finished-goods-transfer` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/inventory-material-retention-report` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/items/{item_code}/stock-ledger` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/items/{item_code}/stock-summary` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/material-counts` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/material-inventory-report` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/material-transfers` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| B | GET | `/api/sales-inventory/sales-channels` | 是 | 是 | 否 | temporary_dev_only | dict_type, dict_code, dict_name, status, source, updated_at | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/sales-inventory/sales-invoices` | 是 | 是 | 否 | temporary_dev_only | sales_invoice, company, sales_order, customer, grand_total, paid_amount, outstanding_amount, posting_date, status | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/sales-inventory/sales-order-fulfillment` | 否 | 是 | 否 | candidate | company, items.sales_order, items.item_code, items.warehouse, items.ordered_qty, items.actual_qty, items.fulfillment_rate | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/sales-orders` | 是 | 是 | 否 | candidate | name, company, customer, transaction_date, delivery_date, status, docstatus, grand_total, currency | 真实业务只读接口候选 |
| A | POST | `/api/sales-inventory/sales-orders/drafts` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/sales-inventory/sales-orders/drafts/{draft_id}/cancel` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/sales-inventory/sales-orders/{name}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/semi-finished-inventory` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/stock-ledger` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/suppliers` | 是 | 是 | 否 | candidate | name, supplier_name, disabled | 真实业务只读接口候选 |
| A | GET | `/api/sales-inventory/warehouses` | 是 | 是 | 否 | candidate | name, company, warehouse_name, disabled | 真实业务只读接口候选 |
| C | POST | `/api/style-profit/readiness/profit-flow` | 否 | 是 | 否 | do_not_connect_as_write | snapshot_no, company, sales_order, item_code, revenue_amount, actual_total_cost, standard_total_cost, profit_amount, profit_rate, snapshot_status, allocation_status, formula_version | readiness flow 回执桩; 不得当作真实写接口 |
| B | GET | `/api/style-profit/style-costs` | 是 | 是 | 否 | temporary_dev_only | snapshot_no, company, item_code, sales_order, from_date, to_date, revenue_amount, actual_total_cost, standard_total_cost, profit_amount, profit_rate, snapshot_status, ... | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/subcontract/` | 是 | 是 | 否 | candidate | id, subcontract_no, supplier, item_code, company, bom_id, process_name, planned_qty, status, created_at | 真实业务只读接口候选 |
| A | POST | `/api/subcontract/` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| B | GET | `/api/subcontract/factories` | 是 | 是 | 否 | temporary_dev_only | company, supplier, factory_name, factory_code, review_status, follow_up_status | dev/test only; 生产环境必须关闭 |
| D | POST | `/api/subcontract/internal/stock-sync/run-once` | 否 | 是 | 否 | not_for_page_direct_use | - | 内部 worker/运维接口; 不给前端页面直接接入 |
| B | GET | `/api/subcontract/material-issues` | 是 | 是 | 否 | temporary_dev_only | subcontract_no, company, supplier, item_code, material_item_code, warehouse, required_qty, issued_qty, pending_qty, status | dev/test only; 生产环境必须关闭 |
| C | POST | `/api/subcontract/readiness/subcontract-flow` | 否 | 是 | 否 | do_not_connect_as_write | subcontract_no, supplier, item_code, material_item_code, issued_qty, received_qty, accepted_qty, planned_return_qty, returned_qty, statement_no, ending_payable, status | readiness flow 回执桩; 不得当作真实写接口 |
| B | GET | `/api/subcontract/receipts` | 是 | 是 | 否 | temporary_dev_only | subcontract_no, company, supplier, item_code, receipt_batch_no, received_qty, accepted_qty, rejected_qty, receipt_warehouse, status | dev/test only; 生产环境必须关闭 |
| B | GET | `/api/subcontract/return-materials` | 是 | 是 | 否 | temporary_dev_only | subcontract_no, company, supplier, item_code, material_item_code, planned_return_qty, returned_qty, pending_qty, status | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/subcontract/settlement-candidates` | 是 | 是 | 否 | candidate | inspection_id, settlement_line_key, subcontract_id, subcontract_no, company, supplier, item_code, process_name, receipt_batch_no, inspected_at, inspected_by, inspected_qty, ... | 真实业务只读接口候选 |
| A | POST | `/api/subcontract/settlement-locks` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/subcontract/settlement-locks/release` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/subcontract/settlement-preview` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/subcontract/{order_id}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/subcontract/{order_id}/inspect` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/subcontract/{order_id}/issue-material` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/subcontract/{order_id}/receive` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/subcontract/{order_id}/stock-sync/retry` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/system/approval-flows` | 否 | 是 | 否 | candidate | flow_key, title, audit_type, status, sender, created_by, created_at, sent_at, last_modified_by, last_modified_at, nodes, actions | 真实业务只读接口候选 |
| A | GET | `/api/system/configs/catalog` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/dictionaries/catalog` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/document-codes` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/health/summary` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/integration-platforms` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/message-notification-settings` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/operation-logs` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/organization-frameworks` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/preference-settings` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/system-announcements` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/system/users/catalog` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/alerts` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/batches` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/batches/{batch_no}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| D | GET | `/api/warehouse/diagnostic` | 否 | 是 | 否 | not_for_page_direct_use | - | 诊断接口; 运维排障用途 |
| A | GET | `/api/warehouse/export` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/factory-return-material-report` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| B | GET | `/api/warehouse/finished-goods-inbound` | 是 | 是 | 否 | temporary_dev_only | reservation_no, item_code, item_name, warehouse, reserve_qty, inbound_qty, pending_inbound_qty, reserve_status, inbound_status, reserved_date, expected_inbound_date, owner, ... | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/warehouse/finished-goods-inbound-candidates` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| D | POST | `/api/warehouse/internal/stock-entry-sync/run-once` | 否 | 是 | 否 | not_for_page_direct_use | - | 内部 worker/运维接口; 不给前端页面直接接入 |
| B | GET | `/api/warehouse/inventory-balance-reconciliation` | 是 | 是 | 否 | temporary_dev_only | company, warehouse, item_code, book_qty, actual_qty, diff_qty, status, biz_date, owner, ref_no | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/warehouse/inventory-counts` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/warehouse/inventory-counts` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/warehouse/inventory-counts/{count_id}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/warehouse/inventory-counts/{count_id}/cancel` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/warehouse/inventory-counts/{count_id}/confirm` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/warehouse/inventory-counts/{count_id}/submit` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/warehouse/inventory-counts/{count_id}/variance-review` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/warehouse/other-inbound` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| B | GET | `/api/warehouse/purchase-receipts` | 是 | 是 | 否 | temporary_dev_only | receipt_no, purchase_no, company, supplier_name, item_code, material_item_code, warehouse, received_qty, accepted_qty, posting_date, status | dev/test only; 生产环境必须关闭 |
| A | GET | `/api/warehouse/purchase-return-outbound` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/semi-finished-outbound` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/serial-numbers` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/serial-numbers/{serial_no}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/warehouse/stock-entry-drafts` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/warehouse/stock-entry-drafts/{draft_id}` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/warehouse/stock-entry-drafts/{draft_id}/cancel` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/warehouse/stock-entry-drafts/{draft_id}/outbox-status` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/stock-ledger` | 是 | 是 | 否 | candidate | company, warehouse, item_code, posting_date, voucher_type, voucher_no, actual_qty, qty_after_transaction, valuation_rate | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/stock-summary` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/warehouse/traceability` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | GET | `/api/workshop/daily-wages` | 是 | 是 | 否 | candidate | employee, work_date, process_name, item_code, register_qty, reversal_qty, net_qty, wage_amount | 真实业务只读接口候选 |
| D | POST | `/api/workshop/internal/job-card-sync/run-once` | 否 | 是 | 否 | not_for_page_direct_use | code, message, data, data.dry_run, data.forbidden_diagnostics_enabled, data.would_process_count, data.processed_count, data.succeeded_count, data.failed_count, data.forbidden_diagnostic_count, data.skipped_forbidden_count, data.blocked_scope_count, ... | 内部 worker/运维接口; 不给前端页面直接接入 |
| A | GET | `/api/workshop/job-cards/{job_card}/summary` | 否 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/workshop/job-cards/{job_card}/sync` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| C | POST | `/api/workshop/readiness/wage-flow` | 否 | 是 | 否 | do_not_connect_as_write | work_order, job_card, process_name, item_code, completed_qty, unit_rate, wage_amount, status | readiness flow 回执桩; 不得当作真实写接口 |
| A | GET | `/api/workshop/tickets` | 是 | 是 | 否 | candidate | id, ticket_no, ticket_key, job_card, work_order, bom_id, item_code, employee, process_name, color, size, operation_type, ... | 真实业务只读接口候选 |
| A | POST | `/api/workshop/tickets/batch` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/workshop/tickets/register` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/workshop/tickets/reversal` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | GET | `/api/workshop/wage-rates` | 是 | 是 | 否 | candidate | - | 真实业务只读接口候选 |
| A | POST | `/api/workshop/wage-rates` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
| A | POST | `/api/workshop/wage-rates/{rate_id}/deactivate` | 否 | 是 | 是 | needs_dedicated_write_task | - | 真实业务写接口候选; 接前端前必须逐项确认落库、审计、幂等 |
