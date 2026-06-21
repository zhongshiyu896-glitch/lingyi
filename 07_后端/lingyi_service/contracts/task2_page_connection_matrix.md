# 任务2 页面接入矩阵

范围：本文件同步自当前前端页面注册表和 FastAPI 路由表；同步日期 2026-06-19。

## 冻结口径

- 库存 / 财务 / 权限源采用 FastAPI 自建，不连接 ERPNext 9081。
- 只把当前前端页面已声明且后端路由存在的 apiPath 标为 A 期真实接入。
- readiness/stub 仅 dev 可用，不作为正式页面写接口。
- 当前页面矩阵：共 60 页；真实后端可接 60 页；apiPath 未命中后端 0 页；未声明 apiPath 0 页。

## A 期已接真实后端页面

| 模块 | 页面 | 前端路由 | 后端 URL | 优先级 | 字段契约 / 剩余缺口 |
| --- | --- | --- | --- | --- | --- |
| 首页 | 首页 | `/dashboard/workplace` | `/api/dashboard/overview?company=<company>` | P1_first_readonly_connect | DashboardOverviewData |
| 基础资料 | 客户 | `/foundation/customer` | `/api/master-data/customers` | P1_first_readonly_connect | CustomerItem, PageData |
| 基础资料 | 加工厂 | `/foundation/factory` | `/api/master-data/factories` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 供应商 | `/foundation/supplier` | `/api/master-data/suppliers` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 送货地址 | `/foundation/commonAddress` | `/api/master-data/common-addresses` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 结算方式 | `/foundation/tradeTerm` | `/api/master-data/trade-terms` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 发票类型 | `/foundation/invoiceType` | `/api/master-data/invoice-types` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 样板类型 | `/foundation/sampleType` | `/api/master-data/sample-types` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 费用类型 | `/foundation/costType` | `/api/master-data/cost-types` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 尺码排序 | `/foundation/sizeSort` | `/api/master-data/size-sorts` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 仓库管理 | `/foundation/warehouse` | `/api/master-data/warehouses` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, WarehouseItem；WarehouseLocation: 仓库主数据增改停走 FastAPI MasterDataItem；仓库树子级/库位字段仍为 owner gap |
| 基础资料 | 销售渠道 | `/foundation/distributionChannel` | `/api/master-data/distribution-channels` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 出纳账户 | `/foundation/bankAccount` | `/api/master-data/bank-accounts` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest |
| 基础资料 | 工艺要求模板 | `/foundation/workmanshipTemplate` | `/api/bom/process-requirement-templates` | P1_first_readonly_connect | FoundationTemplateItem, FoundationTemplateNodeItem, FoundationTemplateCreateRequest |
| 基础资料 | 尺寸表模板 | `/foundation/sizeSpecTemplate` | `/api/bom/size-chart-templates` | P1_first_readonly_connect | FoundationTemplateItem, FoundationTemplateNodeItem, FoundationTemplateCreateRequest |
| 款式设计 | 款式资料 | `/product/styleMaster` | `/api/style-master/styles` | P1_first_readonly_connect | StyleMasterItem, StyleDictionaryItem, StyleMasterCreateRequest, StyleDictionaryCreateRequest |
| 款式设计 | 款式图库 | `/product/styleGallery` | `/api/style-master/style-gallery` | P1_first_readonly_connect | StyleGalleryItem, StyleGalleryCreateRequest, StyleMasterItem |
| 物料开发 | 面料 | `/material/materialFabric` | `/api/master-data/materials` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomFabricItem；MaterialFabricVisualOnly: 物料主数据增改停走 FastAPI MasterDataItem payload；部位/幅宽/克重后端无字段，列位保留并显示 — |
| 物料开发 | 辅料/包材 | `/material/materialAccessory` | `/api/master-data/materials` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomAccessoriesPackagingItem；MaterialAccessoryVisualOnly: 物料主数据增改停走 FastAPI MasterDataItem payload；部位/幅宽/克重后端无字段，列位保留并显示 — |
| 物料开发 | 物料图库 | `/material/materialGalleryList` | `/api/master-data/materials` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomMaterialGalleryItem；MaterialGalleryVisualOnly: 物料图库增改停走 FastAPI MasterDataItem payload；无真实图像文件时只展示 thumbnail_url 字段和静态缩略图入口 |
| 物料开发 | 物料加工类型 | `/material/materialProcessType` | `/api/master-data/materials` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomProcessingTypeItem |
| 物料开发 | 物料类型 | `/material/materialCategory` | `/api/master-data/materials` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomMaterialTypeItem；MaterialTypeTree: 物料类型增改停走 FastAPI MasterDataItem payload；树形层级为前端按 material_group 派生，后端无 children/level/order 字段 |
| 物料开发 | 物料单位 | `/material/materialUnit` | `/api/master-data/materials` | P1_first_readonly_connect | MasterDataItem, MasterDataCreateRequest, MasterDataUpdateRequest, MasterDataDeactivateRequest, BomMaterialUnitItem |
| 设计打样 | 样板单 | `/sample/sampleListV2` | `/api/sample/orders` | P4_hold | SampleOrderItem, SampleOrderCreateRequest；SampleOrder: SampleOrder FastAPI 已接入 /api/sample/orders；mock 模式保留旧占位，API 模式封样后转大货会生成 A4 销售订单草稿。 |
| 设计打样 | 跟进模板 | `/sample/trackingTemplate` | `/api/sample/tracking-templates` | P1_first_readonly_connect | SampleTrackingTemplateItem, SampleTrackingNodeItem；SampleTrackingTemplate: SampleTrackingTemplate schema 已由 FastAPI /api/sample/tracking-templates 承接；mock 模式保留 owner gap 占位。 |
| 大货管理 | 大货看板 | `/production/home` | `/api/dashboard/overview?company=<company>` | P4_hold | DashboardOverviewData, SalesOrderListItem；ProductionDashboard: A期已用 DashboardOverviewData 接入 /api/dashboard/overview；专属 ProductionDashboard schema 与节点级业务钻取待B期补齐。 |
| 大货管理 | 报价单 | `/production/productQuote` | `/api/production/quotes` | P1_first_readonly_connect | ProductionQuoteListItem, ProductionQuoteCreateRequest；ProductQuote: api模式支持从已有生产计划新建报价真落库，面辅料成本按生产计划物料快照或款BOM计算；转订单/作废/复制待后续闭环 |
| 大货管理 | 订单 | `/production/productOrder` | `/api/sales-inventory/sales-orders` | P1_first_readonly_connect | SalesOrderListItem, SalesOrderDraftCreateRequest, ProductionMaterialCheckRequest |
| 大货管理 | 大货跟进 | `/production/orderTrackingV2` | `/api/production/plans` | P1_first_readonly_connect | ProductionPlanListItem；ProductionTracking: 跟进节点/异常/进度字段缺口；列表降级绑定 ProductionPlanListItem |
| 大货管理 | 跟进模板 | `/production/factoryPacking/pending` | `/api/production/followup-templates` | P1_first_readonly_connect | ProductionFollowupTemplateListItem, ProductionFollowupTemplateCreateRequest, ProductionFollowupTemplateUpdateRequest, ProductionFollowupTemplateCopyRequest, ProductionFollowupTemplateActionRequest；api模式已接 FastAPI 跟进模板增改复制停用真落库 |
| 大货管理 | 下单进出数量明细表 | `/production/factoryPacking/list` | `/api/production/order-io-quantities` | P1_first_readonly_connect | ProductionOrderIOQuantityListData, FactoryPackingCreateRequest, FactoryPackingData；api模式读取进出聚合，新增登记写入 `/api/production/factory-packings` 真落库并回算数量 |
| 大货管理 | 款式打板下单对账表 | `/production/productionTrackingTemplate` | `/api/production/tracking-reconciliations` | P4_hold | ProductionTrackingReconcileData, ProductionTrackingReconcileGenerateRequest |
| 大货管理 | 订单生产加工数量对照表 | `/production/report/orderQuantityReport` | `/api/production/report-suite` | P1_first_readonly_connect | ProductionReportSuiteData；OrderQuantityReportMockOnly: api模式已接 /api/production/report-suite；mock模式保留静态 owner gap 遮蔽 |
| 大货管理 | 订单款式利润预测明细表 | `/production/report/productOrderSampleCompare` | `/api/production/report-suite` | P4_hold | ProductionReportSuiteData；ProductOrderSampleCompareMockOnly: api模式已接 /api/production/report-suite；样衣成本差异待B期成本口径合并 |
| 大货管理 | 大货成本物料明细表 | `/production/report/orderTrackingReport` | `/api/production/report-suite` | P4_hold | ProductionReportSuiteData；ProductionCostMaterialDetailMockOnly: api模式已接 /api/production/report-suite；mock模式保留静态 owner gap 遮蔽 |
| 大货管理 | 大货销售预测明细表 | `/production/report/productOrderProfitReport` | `/api/production/report-suite` | P4_hold | ProductionReportSuiteData；ProductOrderProfitReportMockOnly: api模式已接 /api/production/report-suite；利润优先取 style-profit 快照，缺快照按BOM预测 |
| 大货管理 | 业务员业绩分析报表 | `/production/report/productionCostMaterialDetailReport` | `/api/production/report-suite` | P1_first_readonly_connect | ProductionReportSuiteData；SalespersonPerformanceReportMockOnly: api模式已接 /api/production/report-suite；mock模式保留静态 owner gap 遮蔽 |
| 物料采购 | 物料采购单 | `/materialPurchase/materialPurchaseProcess` | `/api/material-purchase/orders` | P1_first_readonly_connect | MaterialPurchaseOrderListItem, MaterialPurchaseOrderCreateRequest, MaterialPurchaseOrderCreateData |
| 物料采购 | 物料加工 | `/materialPurchase/materialProcess` | `/api/subcontract/` | P1_first_readonly_connect | SubcontractListItem, SubcontractCreateRequest |
| 物料进销存 | 物料库存 | `/materialStock/materialTypeStock` | `/api/warehouse/stock-ledger` | P4_hold | WarehouseStockLedgerItem |
| 物料进销存 | 物料加工入仓 | `/materialStock/materialProcessInWarehouse` | `/api/warehouse/stock-entry-drafts` | P4_hold | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest, WarehouseStockEntryDraftAuditRequest, WarehouseStockEntryDraftCancelRequest；MaterialProcessInboundSource: A期已用 WarehouseStockEntryDraftData + source_type=material_process_inbound 隔离物料加工入仓；创建/审核/取消走统一库存草稿 |
| 物料进销存 | 其他入仓 | `/materialStock/materialOtherInWarehouse` | `/api/warehouse/stock-entry-drafts` | P4_hold | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest；MaterialOtherInboundSource: A期已用 WarehouseStockEntryDraftData + source_type=material_other_inbound 隔离其他入仓；采购入库跳转以 source_type=material_purchase_order 覆盖 |
| 物料进销存 | 物料扣仓 | `/materialStock/materialHoldWarehouse` | `/api/warehouse/stock-entry-drafts` | P1_first_readonly_connect | WarehouseStockEntryDraftData, WarehouseMaterialHoldReleaseRequest；MaterialHoldWarehouseReservationDetail: A期列表/新建/释放已接 WarehouseStockEntryDraftData + source_type=material_hold；reserved_qty 已按未释放 material_hold 草稿明细汇总，专用 reservation 表仍待后续库存预留模型补齐 |
| 物料进销存 | 采购退料出仓 | `/materialStock/materialPurchaseReturn` | `/api/warehouse/stock-entry-drafts` | P4_hold | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest, WarehouseStockEntryDraftAuditRequest, WarehouseStockEntryDraftCancelRequest；PurchaseReturnStockOut: A期已用 WarehouseStockEntryDraftData + source_type=material_purchase_return 隔离采购退料出仓；创建/审核/取消走统一库存草稿 |
| 物料进销存 | 物料销售出仓 | `/materialStock/materialSaleOutWarehouse` | `/api/warehouse/stock-entry-drafts` | P4_hold | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest, WarehouseStockEntryDraftAuditRequest, WarehouseStockEntryDraftCancelRequest；MaterialSaleOutWarehouse: A期已用 WarehouseStockEntryDraftData + source_type=material_sale_outbound 隔离物料销售出仓；创建/审核/取消走统一库存草稿 |
| 物料进销存 | 物料调仓 | `/materialStock/materialTransform/pending` | `/api/warehouse/stock-entry-drafts` | P4_hold | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest |
| 物料进销存 | 物料盘点 | `/materialStock/materialTransform/list` | `/api/warehouse/inventory-counts` | P4_hold | WarehouseInventoryCountData, WarehouseInventoryCountCreateRequest |
| 物料进销存 | 物料进销存报表 | `/materialStock/materialTransfer` | `/api/warehouse/stock-ledger` | P1_first_readonly_connect | WarehouseStockLedgerItem |
| 物料进销存 | 加工厂应退料报表 | `/materialStock/materialCheck` | `/api/warehouse/factory-return-material-report` | P1_first_readonly_connect | WarehouseFactoryReturnMaterialReportData |
| 物料进销存 | 库存物料滞留报表 | `/materialStock/report/materialStock` | `/api/warehouse/material-retention-report` | P1_first_readonly_connect | WarehouseMaterialRetentionReportData |
| 车间管理 | 工票登记 | `/workshop/tickets` | `/api/workshop/tickets` | P4_hold | WorkshopTicketRow, WorkshopTicketRegisterRequest |
| 车间管理 | 工序工价 | `/workshop/wageRates` | `/api/workshop/wage-rates` | P1_first_readonly_connect | OperationWageRateRow, OperationWageRateCreateRequest |
| 车间管理 | 计件工资 | `/workshop/dailyWages` | `/api/workshop/daily-wages` | P1_first_readonly_connect | WorkshopDailyWageRow |
| 质量管理 | 质检登记 | `/quality/inspections` | `/api/quality/inspections` | P4_hold | QualityInspectionListItem, QualityInspectionCreateRequest, QualityInspectionConfirmRequest |
| 大货管理 | 成品入库 | `/production/finishedGoodsInbound` | `/api/warehouse/stock-entry-drafts` | P4_hold | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest, WarehouseStockEntryDraftCancelRequest |
| 大货管理 | 发货开票 | `/production/deliveryInvoice` | `/api/sales-inventory/delivery-invoices` | P4_hold | DeliveryInvoiceData, DeliveryInvoiceCreateRequest, DeliveryNoteItem, SalesInvoiceItem |
| 大货管理 | 应收回款 | `/production/receivablePayment` | `/api/sales-inventory/payment-entries` | P4_hold | SalesInvoiceItem, SalesPaymentEntryData, SalesPaymentEntryCreateRequest |
| 物料采购 | 加工厂对账应付 | `/materialPurchase/factoryStatementPayment` | `/api/factory-statements/payments` | P4_hold | FactoryStatementListItem, FactoryStatementPaymentData, FactoryStatementPaymentCreateRequest |
| 物料采购 | 采购发票应付 | `/materialPurchase/purchaseInvoicePayable` | `/api/material-purchase/purchase-invoices` | P4_hold | MaterialPurchaseInvoiceData, MaterialPurchaseInvoiceCreateRequest, MaterialPurchasePaymentData, MaterialPurchasePaymentCreateRequest |
| 物料采购 | 采购入库 | `/materialPurchase/purchaseInbound` | `/api/warehouse/stock-entry-drafts` | P4_hold | WarehouseStockEntryDraftData, WarehouseStockEntryDraftCreateRequest, WarehouseStockEntryDraftAuditRequest, WarehouseStockEntryDraftCancelRequest；MaterialPurchaseInboundSource: A期复用 WarehouseStockEntryDraftData + source_type=material_purchase_order 承接采购入库；创建/审核/取消走统一库存草稿并回写采购需求 |

## 待 B 期或产品契约页面

- 当前 page-registry 内 60 个现有页面均已声明并命中 FastAPI 真实后端 route；后续仍按字段 gap 与写操作验收继续推进。

## 闭环说明

- A 期按现有页面推进：页面可点、接口真落库、失败显式报错。
- B 期再补仍缺的专属页面或专属契约；当前矩阵内页面均已命中 FastAPI route，但 P4_hold / field gap 不代表完整业务闭环已完成。
- 已接页面里的 field gap 只表示字段口径部分缺失，不代表 apiPath 不可用。
