# 前端页面到后端接口接入矩阵

来源：只读解析 `/Users/hh/Desktop/lingyi-frontend-1to1/src/page-registry.ts`；不修改前端文件。

- 真实后端可接：15
- dev readiness only：1
- apiPath 未命中后端：0
- 未声明 apiPath：32

| 优先级 | 模块 | 页面 | 前端路由 | apiPath | 后端状态 | 契约/缺口 |
| --- | --- | --- | --- | --- | --- | --- |
| P1_first_readonly_connect | 首页 | 首页 | `/dashboard/workplace` | `/api/dashboard/overview?company=<company>` | real_backend_route | DashboardOverviewData |
| P1_first_readonly_connect | 基础资料 | 客户 | `/foundation/customer` | `/api/sales-inventory/customers` | real_backend_route | CustomerItem, PageData |
| P3_needs_product_contract | 基础资料 | 加工厂 | `/foundation/factory` | `` | missing_api_path | Factory: contract 缺少 Factory schema |
| P3_needs_product_contract | 基础资料 | 供应商 | `/foundation/supplier` | `` | missing_api_path | Supplier: contract 缺少 Supplier schema |
| P3_needs_product_contract | 基础资料 | 送货地址 | `/foundation/commonAddress` | `` | missing_api_path | CommonAddress: contract 缺少 CommonAddress schema |
| P3_needs_product_contract | 基础资料 | 结算方式 | `/foundation/tradeTerm` | `` | missing_api_path | TradeTerm: contract 缺少 TradeTerm schema |
| P3_needs_product_contract | 基础资料 | 发票类型 | `/foundation/invoiceType` | `` | missing_api_path | InvoiceType: contract 缺少 InvoiceType schema |
| P3_needs_product_contract | 基础资料 | 样板类型 | `/foundation/sampleType` | `` | missing_api_path | SampleType: contract 缺少 SampleType schema |
| P3_needs_product_contract | 基础资料 | 费用类型 | `/foundation/costType` | `` | missing_api_path | CostType: contract 缺少 CostType schema |
| P3_needs_product_contract | 基础资料 | 尺码排序 | `/foundation/sizeSort` | `` | missing_api_path | SizeSort: contract 缺少 SizeSort schema |
| P2_backend_alignment_needed | 基础资料 | 仓库管理 | `/foundation/warehouse` | `/api/sales-inventory/warehouses` | dev_readiness_only | WarehouseLocation: WarehouseItem 仅含 name/company/warehouse_name/disabled，库位字段缺口回报 owner |
| P3_needs_product_contract | 基础资料 | 销售渠道 | `/foundation/distributionChannel` | `` | missing_api_path | DistributionChannel: contract 缺少 DistributionChannel schema |
| P3_needs_product_contract | 基础资料 | 出纳账户 | `/foundation/bankAccount` | `` | missing_api_path | BankAccount: contract 缺少 BankAccount schema |
| P3_needs_product_contract | 基础资料 | 工艺要求模板 | `/foundation/workmanshipTemplate` | `` | missing_api_path | WorkmanshipTemplate: contract 缺少 WorkmanshipTemplate schema |
| P3_needs_product_contract | 基础资料 | 尺寸表模板 | `/foundation/sizeSpecTemplate` | `` | missing_api_path | SizeSpecTemplate: contract 缺少 SizeSpecTemplate schema |
| P1_first_readonly_connect | 物料开发 | 面料 | `/material/materialFabric` | `/api/bom/fabrics` | real_backend_route | MaterialFabricVisualOnly: 部位/幅宽/克重后端无字段，已隐藏 |
| P1_first_readonly_connect | 物料开发 | 辅料/包材 | `/material/materialAccessory` | `/api/bom/accessories-packaging` | real_backend_route | MaterialAccessoryVisualOnly: 部位/幅宽/克重后端无字段，已隐藏 |
| P1_first_readonly_connect | 物料开发 | 物料图库 | `/material/materialGalleryList` | `/api/bom/material-gallery` | real_backend_route | BomMaterialGalleryItem |
| P1_first_readonly_connect | 物料开发 | 物料加工类型 | `/material/materialProcessType` | `/api/bom/processing-types` | real_backend_route | BomProcessingTypeItem |
| P1_first_readonly_connect | 物料开发 | 物料类型 | `/material/materialCategory` | `/api/bom/material-types` | real_backend_route | MaterialTypeTree: 树形层级为前端派生，后端无 children/level/order 字段 |
| P1_first_readonly_connect | 物料开发 | 物料单位 | `/material/materialUnit` | `/api/bom/material-units` | real_backend_route | BomMaterialUnitItem |
| P3_needs_product_contract | 设计打样 | 样板单 | `/sample/sampleListV2` | `` | missing_api_path | SampleOrder: contract 缺少 SampleOrder schema |
| P3_needs_product_contract | 设计打样 | 跟进模板 | `/sample/trackingTemplate` | `` | missing_api_path | SampleTrackingTemplate: contract 缺少 SampleTrackingTemplate schema |
| P4_hold | 大货管理 | 大货看板 | `/production/home` | `/api/dashboard/overview?company=<company>` | real_backend_route | ProductionDashboard: contract 缺少 ProductionDashboard schema |
| P3_needs_product_contract | 大货管理 | 报价单 | `/production/productQuote` | `` | missing_api_path | ProductQuote: 契约无 ProductQuote schema，不伪装为 sales-orders |
| P1_first_readonly_connect | 大货管理 | 订单 | `/production/productOrder` | `/api/sales-inventory/sales-orders` | real_backend_route | SalesOrderListItem, SalesOrderDraftCreateRequest |
| P1_first_readonly_connect | 大货管理 | 大货跟进 | `/production/orderTrackingV2` | `/api/production/plans` | real_backend_route | ProductionTracking: 跟进节点/异常/进度字段缺口；列表降级绑定 ProductionPlanListItem |
| P3_needs_product_contract | 大货管理 | 跟进模板 | `/production/factoryPacking/pending` | `` | missing_api_path | ProductionTrackingTemplate: contract 缺少 ProductionTrackingTemplate schema |
| P3_needs_product_contract | 大货管理 | 下单进出数量明细表 | `/production/factoryPacking/list` | `` | missing_api_path | FactoryPacking: contract 缺少 FactoryPacking schema |
| P3_needs_product_contract | 大货管理 | 款式打板下单对账表 | `/production/productionTrackingTemplate` | `` | missing_api_path | ProductionTrackingReconcile: contract 缺少 ProductionTrackingReconcile schema |
| P3_needs_product_contract | 大货管理 | 订单生产加工数量对照表 | `/production/report/orderQuantityReport` | `` | missing_api_path | OrderQuantityReport: 报表读模型缺失，仅 sales_order/customer/status 可视为 SalesOrderListItem 派生，其余显示 — |
| P3_needs_product_contract | 大货管理 | 订单款式利润预测明细表 | `/production/report/productOrderSampleCompare` | `` | missing_api_path | ProductOrderSampleCompare: 报表读模型缺失，仅 sales_order/customer/status 可视为 SalesOrderListItem 派生，其余显示 — |
| P3_needs_product_contract | 大货管理 | 大货成本物料明细表 | `/production/report/orderTrackingReport` | `` | missing_api_path | ProductionCostMaterialDetail: 报表读模型缺失，仅 sales_order/customer/status 可视为 SalesOrderListItem 派生，其余显示 — |
| P3_needs_product_contract | 大货管理 | 大货销售预测明细表 | `/production/report/productOrderProfitReport` | `` | missing_api_path | ProductOrderProfitReport: 报表读模型缺失，仅 sales_order/customer/status 可视为 SalesOrderListItem 派生，其余显示 — |
| P3_needs_product_contract | 大货管理 | 业务员业绩分析报表 | `/production/report/productionCostMaterialDetailReport` | `` | missing_api_path | SalespersonPerformanceReport: 报表读模型缺失，仅 sales_order/customer/status 可视为 SalesOrderListItem 派生，其余显示 — |
| P1_first_readonly_connect | 物料采购 | 物料采购单 | `/materialPurchase/materialPurchaseProcess` | `/api/subcontract/` | real_backend_route | MaterialPurchaseOrder: contract 缺少采购单列表 schema，当前只用 SubcontractListItem 类型占位 |
| P1_first_readonly_connect | 物料采购 | 物料加工 | `/materialPurchase/materialProcess` | `/api/subcontract/` | real_backend_route | MaterialProcessOrder: contract 缺少 MaterialProcessOrder schema |
| P4_hold | 物料进销存 | 物料库存 | `/materialStock/materialTypeStock` | `/api/warehouse/stock-ledger` | real_backend_route | WarehouseStockLedgerItem |
| P3_needs_product_contract | 物料进销存 | 物料加工入仓 | `/materialStock/materialProcessInWarehouse` | `` | missing_api_path | StockEntryDraftList: 草稿仅有 /api/warehouse/stock-entry-drafts/{id} 单条详情读端点；列表展示用内置 mock，不写列表 apiPath |
| P3_needs_product_contract | 物料进销存 | 其他入仓 | `/materialStock/materialOtherInWarehouse` | `` | missing_api_path | StockEntryDraftList: 草稿仅有 /api/warehouse/stock-entry-drafts/{id} 单条详情读端点；列表展示用内置 mock，不写列表 apiPath |
| P3_needs_product_contract | 物料进销存 | 物料扣仓 | `/materialStock/materialHoldWarehouse` | `` | missing_api_path | StockEntryDraftList: 草稿仅有 /api/warehouse/stock-entry-drafts/{id} 单条详情读端点；列表展示用内置 mock，不写列表 apiPath |
| P3_needs_product_contract | 物料进销存 | 采购退料出仓 | `/materialStock/materialPurchaseReturn` | `` | missing_api_path | PurchaseReturnStockOut: 未提供采购退料出仓列表读模型；草稿仅有单条详情读端点，不写列表 apiPath |
| P3_needs_product_contract | 物料进销存 | 物料销售出仓 | `/materialStock/materialSaleOutWarehouse` | `` | missing_api_path | MaterialSaleOutWarehouse: 未提供物料销售出仓列表读模型；草稿仅有单条详情读端点，不写列表 apiPath |
| P3_needs_product_contract | 物料进销存 | 物料调仓 | `/materialStock/materialTransform/pending` | `` | missing_api_path | StockEntryDraftList: 草稿仅有 /api/warehouse/stock-entry-drafts/{id} 单条详情读端点；列表展示用内置 mock，不写列表 apiPath |
| P3_needs_product_contract | 物料进销存 | 物料盘点 | `/materialStock/materialTransform/list` | `` | missing_api_path | MaterialInventoryCount: 未提供物料盘点列表读模型；草稿仅有单条详情读端点，不写列表 apiPath |
| P1_first_readonly_connect | 物料进销存 | 物料进销存报表 | `/materialStock/materialTransfer` | `/api/warehouse/stock-ledger` | real_backend_route | WarehouseStockLedgerItem |
| P3_needs_product_contract | 物料进销存 | 加工厂应退料报表 | `/materialStock/materialCheck` | `` | missing_api_path | FactoryReturnMaterialReport: 加工厂应退料报表读模型缺失，不写 stock-ledger apiPath，避免误绑 |
| P3_needs_product_contract | 物料进销存 | 库存物料滞留报表 | `/materialStock/report/materialStock` | `` | missing_api_path | MaterialRetentionReport: 库存物料滞留报表读模型缺失，不写 stock-ledger apiPath，避免误绑 |
