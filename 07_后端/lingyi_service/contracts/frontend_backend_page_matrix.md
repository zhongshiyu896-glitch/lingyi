# 前端页面到后端接口接入矩阵

来源：只读解析 `/Users/hh/Desktop/lingyi-frontend-1to1/src/page-registry.ts`；不修改前端文件。

- 真实后端可接：60
- dev readiness only：0
- apiPath 未命中后端：0
- 未声明 apiPath：0

| 优先级 | 模块 | 页面 | 前端路由 | apiPath | 后端状态 | 契约/缺口 |
| --- | --- | --- | --- | --- | --- | --- |
| P1_first_readonly_connect | 首页 | 首页 | `/dashboard/workplace` | `/api/dashboard/overview?company=<company>` | real_backend_route | DashboardOverviewData |
| P1_first_readonly_connect | 基础资料 | 客户 | `/foundation/customer` | `/api/master-data/customers` | real_backend_route | CustomerItem, PageData |
| P1_first_readonly_connect | 基础资料 | 加工厂 | `/foundation/factory` | `/api/master-data/factories` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 供应商 | `/foundation/supplier` | `/api/master-data/suppliers` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 送货地址 | `/foundation/commonAddress` | `/api/master-data/common-addresses` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 结算方式 | `/foundation/tradeTerm` | `/api/master-data/trade-terms` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 发票类型 | `/foundation/invoiceType` | `/api/master-data/invoice-types` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 样板类型 | `/foundation/sampleType` | `/api/master-data/sample-types` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 费用类型 | `/foundation/costType` | `/api/master-data/cost-types` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 尺码排序 | `/foundation/sizeSort` | `/api/master-data/size-sorts` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 仓库管理 | `/foundation/warehouse` | `/api/master-data/warehouses` | real_backend_route | WarehouseLocation: 仓库主数据增改停走 FastAPI MasterDataItem；仓库树子级/库位字段仍为 owner gap |
| P1_first_readonly_connect | 基础资料 | 销售渠道 | `/foundation/distributionChannel` | `/api/master-data/distribution-channels` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 出纳账户 | `/foundation/bankAccount` | `/api/master-data/bank-accounts` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| P1_first_readonly_connect | 基础资料 | 工艺要求模板 | `/foundation/workmanshipTemplate` | `/api/bom/process-requirement-templates` | real_backend_route | FoundationTemplateItem, FoundationTemplateNodeItem, FoundationTemplateCreateRequest |
| P1_first_readonly_connect | 基础资料 | 尺寸表模板 | `/foundation/sizeSpecTemplate` | `/api/bom/size-chart-templates` | real_backend_route | FoundationTemplateItem, FoundationTemplateNodeItem, FoundationTemplateCreateRequest |
| P1_first_readonly_connect | 款式设计 | 款式资料 | `/product/styleMaster` | `/api/style-master/styles` | real_backend_route | StyleMasterItem, StyleDictionaryItem, StyleMasterCreateRequest, StyleDictionaryCreateRequest |
| P1_first_readonly_connect | 款式设计 | 款式图库 | `/product/styleGallery` | `/api/style-master/style-gallery` | real_backend_route | StyleGalleryItem, StyleGalleryCreateRequest, StyleMasterItem |
| P1_first_readonly_connect | 物料开发 | 面料 | `/material/materialFabric` | `/api/master-data/materials` | real_backend_route | MaterialFabricVisualOnly: 物料主数据增改停走 FastAPI MasterDataItem payload；部位/幅宽/克重后端无字段，列位保留并显示 — |
| P1_first_readonly_connect | 物料开发 | 辅料/包材 | `/material/materialAccessory` | `/api/master-data/materials` | real_backend_route | MaterialAccessoryVisualOnly: 物料主数据增改停走 FastAPI MasterDataItem payload；部位/幅宽/克重后端无字段，列位保留并显示 — |
| P1_first_readonly_connect | 物料开发 | 物料图库 | `/material/materialGalleryList` | `/api/master-data/materials` | real_backend_route | MaterialGalleryVisualOnly: 物料图库增改停走 FastAPI MasterDataItem payload；无真实图像文件时只展示 thumbnail_url 字段和静态缩略图入口 |
| P1_first_readonly_connect | 物料开发 | 物料加工类型 | `/material/materialProcessType` | `/api/master-data/materials` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomProcessingTypeItem |
| P1_first_readonly_connect | 物料开发 | 物料类型 | `/material/materialCategory` | `/api/master-data/materials` | real_backend_route | MaterialTypeTree: 物料类型增改停走 FastAPI MasterDataItem payload；树形层级为前端按 material_group 派生，后端无 children/level/order 字段 |
| P1_first_readonly_connect | 物料开发 | 物料单位 | `/material/materialUnit` | `/api/master-data/materials` | real_backend_route | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomMaterialUnitItem |
| P4_hold | 设计打样 | 样板单 | `/sample/sampleListV2` | `/api/sample/orders` | real_backend_route | SampleOrder: SampleOrder FastAPI 已接入 /api/sample/orders；mock 模式保留旧占位，API 模式封样后转大货会生成 A4 销售订单草稿。 |
| P1_first_readonly_connect | 设计打样 | 跟进模板 | `/sample/trackingTemplate` | `/api/sample/tracking-templates` | real_backend_route | SampleTrackingTemplate: SampleTrackingTemplate schema 已由 FastAPI /api/sample/tracking-templates 承接；mock 模式保留 owner gap 占位。 |
| P4_hold | 大货管理 | 大货看板 | `/production/home` | `/api/dashboard/overview?company=<company>` | real_backend_route | ProductionDashboard: A期已用 DashboardOverviewData 接入 /api/dashboard/overview；专属 ProductionDashboard schema 与节点级业务钻取待B期补齐。 |
| P1_first_readonly_connect | 大货管理 | 报价单 | `/production/productQuote` | `/api/production/quotes` | real_backend_route | ProductQuote: api模式支持从已有生产计划新建报价真落库，面辅料成本按生产计划物料快照或款BOM计算；转订单/作废/复制待后续闭环 |
| P1_first_readonly_connect | 大货管理 | 订单 | `/production/productOrder` | `/api/sales-inventory/sales-orders` | real_backend_route | SalesOrderListItem, SalesOrderDraftCreateRequest, ProductionMaterialCheckRequest |
| P1_first_readonly_connect | 大货管理 | 大货跟进 | `/production/orderTrackingV2` | `/api/production/plans` | real_backend_route | ProductionTracking: 跟进节点/异常/进度字段缺口；列表降级绑定 ProductionPlanListItem |
| P1_first_readonly_connect | 大货管理 | 跟进模板 | `/production/factoryPacking/pending` | `/api/production/followup-templates` | real_backend_route | ProductionFollowupTemplateListItem/Create/Update/Copy/Action；api模式已接 FastAPI 跟进模板增改复制停用真落库 |
| P4_hold | 大货管理 | 下单进出数量明细表 | `/production/factoryPacking/list` | `/api/production/order-io-quantities` | real_backend_route | FactoryPacking: 契约无 FactoryPacking schema；api模式只读绑定 ProductionOrderIOQuantityListData，箱数/装箱流水待B期 |
| P4_hold | 大货管理 | 款式打板下单对账表 | `/production/productionTrackingTemplate` | `/api/production/tracking-reconciliations` | real_backend_route | ProductionTrackingReconcileData, ProductionTrackingReconcileGenerateRequest |
| P1_first_readonly_connect | 大货管理 | 订单生产加工数量对照表 | `/production/report/orderQuantityReport` | `/api/production/report-suite` | real_backend_route | OrderQuantityReportMockOnly: api模式已接 /api/production/report-suite；mock模式保留静态 owner gap 遮蔽 |
| P4_hold | 大货管理 | 订单款式利润预测明细表 | `/production/report/productOrderSampleCompare` | `/api/production/report-suite` | real_backend_route | ProductOrderSampleCompareMockOnly: api模式已接 /api/production/report-suite；样衣成本差异待B期成本口径合并 |
| P4_hold | 大货管理 | 大货成本物料明细表 | `/production/report/orderTrackingReport` | `/api/production/report-suite` | real_backend_route | ProductionCostMaterialDetailMockOnly: api模式已接 /api/production/report-suite；mock模式保留静态 owner gap 遮蔽 |
| P4_hold | 大货管理 | 大货销售预测明细表 | `/production/report/productOrderProfitReport` | `/api/production/report-suite` | real_backend_route | ProductOrderProfitReportMockOnly: api模式已接 /api/production/report-suite；利润优先取 style-profit 快照，缺快照按BOM预测 |
| P1_first_readonly_connect | 大货管理 | 业务员业绩分析报表 | `/production/report/productionCostMaterialDetailReport` | `/api/production/report-suite` | real_backend_route | SalespersonPerformanceReportMockOnly: api模式已接 /api/production/report-suite；mock模式保留静态 owner gap 遮蔽 |
| P1_first_readonly_connect | 物料采购 | 物料采购单 | `/materialPurchase/materialPurchaseProcess` | `/api/material-purchase/orders` | real_backend_route | MaterialPurchaseOrderListItem, MaterialPurchaseOrderCreateRequest, MaterialPurchaseOrderCreateData |
| P1_first_readonly_connect | 物料采购 | 物料加工 | `/materialPurchase/materialProcess` | `/api/subcontract/` | real_backend_route | SubcontractListItem, SubcontractCreateRequest |
| P4_hold | 物料进销存 | 物料库存 | `/materialStock/materialTypeStock` | `/api/warehouse/stock-ledger` | real_backend_route | WarehouseStockLedgerItem |
| P4_hold | 物料进销存 | 物料加工入仓 | `/materialStock/materialProcessInWarehouse` | `/api/warehouse/stock-entry-drafts` | real_backend_route | MaterialProcessInboundSource: A期已用 WarehouseStockEntryDraftData + source_type=material_process_inbound 隔离物料加工入仓；创建/审核/取消走统一库存草稿 |
| P4_hold | 物料进销存 | 其他入仓 | `/materialStock/materialOtherInWarehouse` | `/api/warehouse/stock-entry-drafts` | real_backend_route | MaterialOtherInboundSource: A期已用 WarehouseStockEntryDraftData + source_type=material_other_inbound 隔离其他入仓；采购入库跳转以 source_type=material_purchase_order 覆盖 |
| P1_first_readonly_connect | 物料进销存 | 物料扣仓 | `/materialStock/materialHoldWarehouse` | `/api/warehouse/stock-entry-drafts` | real_backend_route | MaterialHoldWarehouseReservationDetail: A期列表/新建/释放已接 WarehouseStockEntryDraftData + source_type=material_hold；锁定量/占用明细仍待后续专用表 |
| P4_hold | 物料进销存 | 采购退料出仓 | `/materialStock/materialPurchaseReturn` | `/api/warehouse/stock-entry-drafts` | real_backend_route | PurchaseReturnStockOut: A期已用 WarehouseStockEntryDraftData + source_type=material_purchase_return 隔离采购退料出仓；创建/审核/取消走统一库存草稿 |
| P4_hold | 物料进销存 | 物料销售出仓 | `/materialStock/materialSaleOutWarehouse` | `/api/warehouse/stock-entry-drafts` | real_backend_route | MaterialSaleOutWarehouse: A期已用 WarehouseStockEntryDraftData + source_type=material_sale_outbound 隔离物料销售出仓；创建/审核/取消走统一库存草稿 |
| P4_hold | 物料进销存 | 物料调仓 | `/materialStock/materialTransform/pending` | `/api/warehouse/stock-entry-drafts` | real_backend_route | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest |
| P4_hold | 物料进销存 | 物料盘点 | `/materialStock/materialTransform/list` | `/api/warehouse/inventory-counts` | real_backend_route | WarehouseInventoryCountData, WarehouseInventoryCountCreateRequest |
| P1_first_readonly_connect | 物料进销存 | 物料进销存报表 | `/materialStock/materialTransfer` | `/api/warehouse/stock-ledger` | real_backend_route | WarehouseStockLedgerItem |
| P1_first_readonly_connect | 物料进销存 | 加工厂应退料报表 | `/materialStock/materialCheck` | `/api/warehouse/factory-return-material-report` | real_backend_route | WarehouseFactoryReturnMaterialReportData |
| P1_first_readonly_connect | 物料进销存 | 库存物料滞留报表 | `/materialStock/report/materialStock` | `/api/warehouse/material-retention-report` | real_backend_route | WarehouseMaterialRetentionReportData |
| P4_hold | 车间管理 | 工票登记 | `/workshop/tickets` | `/api/workshop/tickets` | real_backend_route | WorkshopTicketRow, WorkshopTicketRegisterRequest |
| P1_first_readonly_connect | 车间管理 | 工序工价 | `/workshop/wageRates` | `/api/workshop/wage-rates` | real_backend_route | OperationWageRateRow, OperationWageRateCreateRequest |
| P1_first_readonly_connect | 车间管理 | 计件工资 | `/workshop/dailyWages` | `/api/workshop/daily-wages` | real_backend_route | WorkshopDailyWageRow |
| P4_hold | 质量管理 | 质检登记 | `/quality/inspections` | `/api/quality/inspections` | real_backend_route | QualityInspectionListItem, QualityInspectionCreateRequest, QualityInspectionConfirmRequest |
| P4_hold | 大货管理 | 成品入库 | `/production/finishedGoodsInbound` | `/api/warehouse/stock-entry-drafts` | real_backend_route | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest, WarehouseStockEntryDraftCancelRequest |
| P4_hold | 大货管理 | 发货开票 | `/production/deliveryInvoice` | `/api/sales-inventory/delivery-invoices` | real_backend_route | DeliveryInvoiceData, DeliveryInvoiceCreateRequest, DeliveryNoteItem, SalesInvoiceItem |
| P4_hold | 大货管理 | 应收回款 | `/production/receivablePayment` | `/api/sales-inventory/payment-entries` | real_backend_route | SalesInvoiceItem, SalesPaymentEntryData, SalesPaymentEntryCreateRequest |
| P4_hold | 物料采购 | 加工厂对账应付 | `/materialPurchase/factoryStatementPayment` | `/api/factory-statements/payments` | real_backend_route | FactoryStatementListItem, FactoryStatementPaymentData, FactoryStatementPaymentCreateRequest |
| P4_hold | 物料采购 | 采购发票应付 | `/materialPurchase/purchaseInvoicePayable` | `/api/material-purchase/purchase-invoices` | real_backend_route | MaterialPurchaseInvoiceData, MaterialPurchaseInvoiceCreateRequest, MaterialPurchasePaymentData, MaterialPurchasePaymentCreateRequest |
| P4_hold | 物料采购 | 采购入库 | `/materialPurchase/purchaseInbound` | `/api/warehouse/stock-entry-drafts` | real_backend_route | MaterialPurchaseInboundSource: A期复用 WarehouseStockEntryDraftData + source_type=material_purchase_order 承接采购入库；创建/审核/取消走统一库存草稿并回写采购需求 |
