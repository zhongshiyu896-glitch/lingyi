# 任务2 页面接入矩阵

范围：本文件同步自当前前端页面注册表和 FastAPI 路由表；同步日期 2026-06-17。

## 冻结口径

- 库存 / 财务 / 权限源采用 FastAPI 自建，不连接 ERPNext 9081。
- 只把当前前端页面已声明且后端路由存在的 apiPath 标为 A 期真实接入。
- readiness/stub 仅 dev 可用，不作为正式页面写接口。
- 当前页面矩阵：共 57 页；真实后端可接 48 页；apiPath 未命中后端 0 页；待 B 期或产品契约 9 页。

## A 期已接真实后端页面

| 模块 | 页面 | 前端路由 | 后端 URL | 字段契约 / 剩余缺口 |
| --- | --- | --- | --- | --- |
| 首页 | 首页 | `/dashboard/workplace` | `/api/dashboard/overview?company=<company>` | DashboardOverviewData |
| 基础资料 | 客户 | `/foundation/customer` | `/api/sales-inventory/customers` | CustomerItem, PageData |
| 基础资料 | 加工厂 | `/foundation/factory` | `/api/master-data/factories` | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 供应商 | `/foundation/supplier` | `/api/master-data/suppliers` | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 仓库管理 | `/foundation/warehouse` | `/api/master-data/warehouses` | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, WarehouseItem；WarehouseLocation: 仓库主数据增改停走 FastAPI MasterDataItem；仓库树子级/库位字段仍为 owner gap |
| 基础资料 | 工艺要求模板 | `/foundation/workmanshipTemplate` | `/api/bom/process-requirement-templates` | BomProcessingTypeItem；WorkmanshipTemplate: 契约无 WorkmanshipTemplate schema；api模式只读绑定 /api/bom/process-requirement-templates，模板增改停待B期 |
| 物料开发 | 面料 | `/material/materialFabric` | `/api/master-data/materials` | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomFabricItem；MaterialFabricVisualOnly: 物料主数据增改停走 FastAPI MasterDataItem payload；部位/幅宽/克重后端无字段，列位保留并显示 — |
| 物料开发 | 辅料/包材 | `/material/materialAccessory` | `/api/master-data/materials` | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomAccessoriesPackagingItem；MaterialAccessoryVisualOnly: 物料主数据增改停走 FastAPI MasterDataItem payload；部位/幅宽/克重后端无字段，列位保留并显示 — |
| 物料开发 | 物料图库 | `/material/materialGalleryList` | `/api/master-data/materials` | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomMaterialGalleryItem；MaterialGalleryVisualOnly: 物料图库增改停走 FastAPI MasterDataItem payload；无真实图像文件时只展示 thumbnail_url 字段和静态缩略图入口 |
| 物料开发 | 物料加工类型 | `/material/materialProcessType` | `/api/master-data/materials` | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomProcessingTypeItem |
| 物料开发 | 物料类型 | `/material/materialCategory` | `/api/master-data/materials` | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomMaterialTypeItem；MaterialTypeTree: 物料类型增改停走 FastAPI MasterDataItem payload；树形层级为前端按 material_group 派生，后端无 children/level/order 字段 |
| 物料开发 | 物料单位 | `/material/materialUnit` | `/api/master-data/materials` | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomMaterialUnitItem |
| 大货管理 | 大货看板 | `/production/home` | `/api/dashboard/overview?company=<company>` | DashboardOverviewData, SalesOrderListItem；ProductionDashboard: A期已用 DashboardOverviewData 接入 /api/dashboard/overview；专属 ProductionDashboard schema 与节点级业务钻取待B期补齐。 |
| 大货管理 | 报价单 | `/production/productQuote` | `/api/production/quotes` | ProductQuote: 契约无 ProductQuote schema；api模式只读绑定 ProductionQuoteListData，写操作待B期 |
| 大货管理 | 订单 | `/production/productOrder` | `/api/sales-inventory/sales-orders` | SalesOrderListItem, SalesOrderDraftCreateRequest |
| 大货管理 | 大货跟进 | `/production/orderTrackingV2` | `/api/production/plans` | ProductionPlanListItem；ProductionTracking: 跟进节点/异常/进度字段缺口；列表降级绑定 ProductionPlanListItem |
| 大货管理 | 跟进模板 | `/production/factoryPacking/pending` | `/api/production/followup-templates` | ProductionTrackingTemplate: 契约无 ProductionTrackingTemplate schema；api模式只读绑定 ProductionFollowupTemplateListData，写操作待B期 |
| 大货管理 | 下单进出数量明细表 | `/production/factoryPacking/list` | `/api/production/order-io-quantities` | FactoryPacking: 契约无 FactoryPacking schema；api模式只读绑定 ProductionOrderIOQuantityListData，箱数/装箱流水待B期 |
| 大货管理 | 款式打板下单对账表 | `/production/productionTrackingTemplate` | `/api/production/tracking-reconciliations` | ProductionTrackingReconcileData, ProductionTrackingReconcileGenerateRequest |
| 大货管理 | 订单生产加工数量对照表 | `/production/report/orderQuantityReport` | `/api/production/report-suite` | ProductionReportSuiteData；OrderQuantityReportMockOnly: api模式已接 /api/production/report-suite；mock模式保留静态 owner gap 遮蔽 |
| 大货管理 | 订单款式利润预测明细表 | `/production/report/productOrderSampleCompare` | `/api/production/report-suite` | ProductionReportSuiteData；ProductOrderSampleCompareMockOnly: api模式已接 /api/production/report-suite；样衣成本差异待B期成本口径合并 |
| 大货管理 | 大货成本物料明细表 | `/production/report/orderTrackingReport` | `/api/production/report-suite` | ProductionReportSuiteData；ProductionCostMaterialDetailMockOnly: api模式已接 /api/production/report-suite；mock模式保留静态 owner gap 遮蔽 |
| 大货管理 | 大货销售预测明细表 | `/production/report/productOrderProfitReport` | `/api/production/report-suite` | ProductionReportSuiteData；ProductOrderProfitReportMockOnly: api模式已接 /api/production/report-suite；利润优先取 style-profit 快照，缺快照按BOM预测 |
| 大货管理 | 业务员业绩分析报表 | `/production/report/productionCostMaterialDetailReport` | `/api/production/report-suite` | ProductionReportSuiteData；SalespersonPerformanceReportMockOnly: api模式已接 /api/production/report-suite；mock模式保留静态 owner gap 遮蔽 |
| 大货管理 | 成品入库 | `/production/finishedGoodsInbound` | `/api/warehouse/stock-entry-drafts` | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest, WarehouseStockEntryDraftCancelRequest |
| 大货管理 | 发货开票 | `/production/deliveryInvoice` | `/api/sales-inventory/delivery-invoices` | DeliveryInvoiceData, DeliveryInvoiceCreateRequest, DeliveryNoteItem, SalesInvoiceItem |
| 大货管理 | 应收回款 | `/production/receivablePayment` | `/api/sales-inventory/payment-entries` | SalesInvoiceItem, SalesPaymentEntryData, SalesPaymentEntryCreateRequest |
| 车间管理 | 工票登记 | `/workshop/tickets` | `/api/workshop/tickets` | WorkshopTicketRow, WorkshopTicketRegisterRequest |
| 车间管理 | 工序工价 | `/workshop/wageRates` | `/api/workshop/wage-rates` | OperationWageRateRow, OperationWageRateCreateRequest |
| 车间管理 | 计件工资 | `/workshop/dailyWages` | `/api/workshop/daily-wages` | WorkshopDailyWageRow |
| 质量管理 | 质检登记 | `/quality/inspections` | `/api/quality/inspections` | QualityInspectionListItem, QualityInspectionCreateRequest, QualityInspectionConfirmRequest |
| 物料采购 | 物料采购单 | `/materialPurchase/materialPurchaseProcess` | `/api/material-purchase/orders` | MaterialPurchaseOrderListItem, MaterialPurchaseOrderCreateRequest, MaterialPurchaseOrderCreateData |
| 物料采购 | 物料加工 | `/materialPurchase/materialProcess` | `/api/subcontract/` | SubcontractListItem, SubcontractCreateRequest |
| 物料采购 | 加工厂对账应付 | `/materialPurchase/factoryStatementPayment` | `/api/factory-statements/payments` | FactoryStatementListItem, FactoryStatementPaymentData, FactoryStatementPaymentCreateRequest |
| 物料采购 | 采购发票应付 | `/materialPurchase/purchaseInvoicePayable` | `/api/material-purchase/purchase-invoices` | MaterialPurchaseInvoiceData, MaterialPurchaseInvoiceCreateRequest, MaterialPurchasePaymentData, MaterialPurchasePaymentCreateRequest |
| 物料进销存 | 物料库存 | `/materialStock/materialTypeStock` | `/api/warehouse/stock-ledger` | WarehouseStockLedgerItem |
| 物料进销存 | 物料加工入仓 | `/materialStock/materialProcessInWarehouse` | `/api/warehouse/stock-entry-drafts` | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest |
| 物料进销存 | 其他入仓 | `/materialStock/materialOtherInWarehouse` | `/api/warehouse/stock-entry-drafts` | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest |
| 物料进销存 | 物料扣仓 | `/materialStock/materialHoldWarehouse` | `/api/warehouse/stock-entry-drafts` | WarehouseStockEntryDraftData；MaterialHoldWarehouseRelease: A期列表已接 WarehouseStockEntryDraftData；释放扣仓写接口待 B 期补齐，当前不做假写入 |
| 物料进销存 | 采购退料出仓 | `/materialStock/materialPurchaseReturn` | `/api/warehouse/stock-entry-drafts` | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest；PurchaseReturnStockOut: 未提供采购退料出仓专属列表读模型；暂复用 WarehouseStockEntryDraftData 的 Material Issue 草稿列表 |
| 物料进销存 | 物料销售出仓 | `/materialStock/materialSaleOutWarehouse` | `/api/warehouse/stock-entry-drafts` | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest；MaterialSaleOutWarehouse: 未提供物料销售出仓专属列表读模型；暂复用 WarehouseStockEntryDraftData 的 Material Issue 草稿列表 |
| 物料进销存 | 物料调仓 | `/materialStock/materialTransform/pending` | `/api/warehouse/stock-entry-drafts` | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest |
| 物料进销存 | 物料盘点 | `/materialStock/materialTransform/list` | `/api/warehouse/inventory-counts` | WarehouseInventoryCountData, WarehouseInventoryCountCreateRequest |
| 物料进销存 | 物料进销存报表 | `/materialStock/materialTransfer` | `/api/warehouse/stock-ledger` | WarehouseStockLedgerItem |
| 物料进销存 | 加工厂应退料报表 | `/materialStock/materialCheck` | `/api/warehouse/factory-return-material-report` | WarehouseFactoryReturnMaterialReportData |
| 物料进销存 | 库存物料滞留报表 | `/materialStock/report/materialStock` | `/api/warehouse/material-retention-report` | WarehouseMaterialRetentionReportData |
| 设计打样 | 样板单 | `/sample/sampleListV2` | `/api/sample/orders` | SampleOrderItem, SampleOrderCreateRequest；SampleOrder: SampleOrder FastAPI 已接入 /api/sample/orders；mock 模式保留旧占位，API 模式转大货会生成 A4 销售订单草稿。 |
| 设计打样 | 跟进模板 | `/sample/trackingTemplate` | `/api/sample/tracking-templates` | SampleTrackingTemplateItem, SampleTrackingNodeItem；SampleTrackingTemplate: SampleTrackingTemplate schema 已由 FastAPI /api/sample/tracking-templates 承接；mock 模式保留 owner gap 占位。 |

## 待 B 期或产品契约页面

这些页面当前没有可信 apiPath；不得自动猜接口，不把 readiness/stub 当正式页面接口。

| 模块 | 页面 | 前端路由 | 缺口 |
| --- | --- | --- | --- |
| 基础资料 | 送货地址 | `/foundation/commonAddress` | CommonAddress: 候选 /api/sales-inventory/delivery-addresses 为 temporary_dev_only；A期不接桩，待B期补 CommonAddress 真实表与接口 |
| 基础资料 | 结算方式 | `/foundation/tradeTerm` | TradeTerm: 候选 settlement-methods 为 temporary_dev_only；A期不接桩，待B期补 TradeTerm 真实字典表与接口 |
| 基础资料 | 发票类型 | `/foundation/invoiceType` | InvoiceType: 候选 /api/factory-statements/invoice-types 为 temporary_dev_only；A期不接桩，待B期补 InvoiceType 真实字典表与接口 |
| 基础资料 | 样板类型 | `/foundation/sampleType` | SampleType: 候选 /api/bom/sample-types 为 temporary_dev_only；A期不接桩，待B期补 SampleType 真实字典表与接口 |
| 基础资料 | 费用类型 | `/foundation/costType` | CostType: 费用类型暂无生产可用真实接口；A期保留缺口，待B期补 CostType 真实字典表与接口 |
| 基础资料 | 尺码排序 | `/foundation/sizeSort` | SizeSort: 候选 /api/bom/size-sortings 为 temporary_dev_only；A期不接桩，待B期补 SizeSort 真实字典表与接口 |
| 基础资料 | 销售渠道 | `/foundation/distributionChannel` | DistributionChannel: 候选 /api/sales-inventory/sales-channels 为 temporary_dev_only；A期不接桩，待B期补 DistributionChannel 真实字典表与接口 |
| 基础资料 | 出纳账户 | `/foundation/bankAccount` | BankAccount: 候选 /api/factory-statements/cashier-accounts 为 temporary_dev_only；A期不接桩，待B期补 BankAccount 真实财务账户表与接口 |
| 基础资料 | 尺寸表模板 | `/foundation/sizeSpecTemplate` | SizeSpecTemplate: 候选 /api/bom/size-chart-templates 为 temporary_dev_only；A期不接桩，待B期补 SizeSpecTemplate 真实模板表与接口 |

## 闭环说明

- A 期按现有页面推进：页面可点、接口真落库、失败显式报错。
- B 期再补仍缺的专属页面或专属契约，例如部分字典、送货地址、结算方式、发票类型、销售渠道、出纳账户、尺寸表模板等。
- 已接页面里的 field gap 只表示字段口径部分缺失，不代表 apiPath 不可用。
