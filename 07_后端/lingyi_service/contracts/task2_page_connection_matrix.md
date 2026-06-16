# 任务2 页面接入矩阵

范围：本文件只在后端仓库沉淀前端接入对照，不读取、不修改前端工程。输入仅来自本仓库已存在的契约资产：

- `contracts/frontend_backend_page_matrix.json`
- `contracts/frontend_backend_page_matrix.md`
- `contracts/frontend_readiness_page_handoff.md`
- `contracts/frontend_readiness_field_contract.json`
- `contracts/backend_interface_asset_catalog.json`

## 冻结口径

- 后端接口资产：A=185、B=19、C=7、D=11。
- 当前页面矩阵：共 48 页；真实后端可接 15 页；dev readiness only 0 页；apiPath 未命中后端 0 页；未声明 apiPath 33 页。
- P1 可先接只读页：13 页，均为 `real_backend_route`。
- P4 暂缓页：2 页，虽有真实接口但涉及看板口径或库存/财务边界，本轮只保留现状。
- P3 待产品契约页：33 页，当前不伪造 apiPath，不把相近接口误绑为业务接口。

## P1 先接只读页

| 模块 | 页面 | 前端路由 | 后端 URL | 字段契约 |
| --- | --- | --- | --- | --- |
| 首页 | 首页 | `/dashboard/workplace` | `/api/dashboard/overview?company=<company>` | `DashboardOverviewData` |
| 基础资料 | 客户 | `/foundation/customer` | `/api/sales-inventory/customers` | `CustomerItem, PageData` |
| 基础资料 | 仓库管理 | `/foundation/warehouse` | `/api/sales-inventory/warehouses` | `WarehouseItem` |
| 物料开发 | 面料 | `/material/materialFabric` | `/api/bom/fabrics` | `BomFabricItem` |
| 物料开发 | 辅料/包材 | `/material/materialAccessory` | `/api/bom/accessories-packaging` | `BomAccessoriesPackagingItem` |
| 物料开发 | 物料图库 | `/material/materialGalleryList` | `/api/bom/material-gallery` | `BomMaterialGalleryItem` |
| 物料开发 | 物料加工类型 | `/material/materialProcessType` | `/api/bom/processing-types` | `BomProcessingTypeItem` |
| 物料开发 | 物料类型 | `/material/materialCategory` | `/api/bom/material-types` | `BomMaterialTypeItem` |
| 物料开发 | 物料单位 | `/material/materialUnit` | `/api/bom/material-units` | `BomMaterialUnitItem` |
| 大货管理 | 订单 | `/production/productOrder` | `/api/sales-inventory/sales-orders` | `SalesOrderListItem, SalesOrderDraftCreateRequest` |
| 大货管理 | 大货跟进 | `/production/orderTrackingV2` | `/api/production/plans` | `ProductionPlanListItem` |
| 物料采购 | 物料加工 | `/materialPurchase/materialProcess` | `/api/subcontract/` | `SubcontractListItem, SubcontractCreateRequest` |
| 物料进销存 | 物料进销存报表 | `/materialStock/materialTransfer` | `/api/warehouse/stock-ledger` | `WarehouseStockLedgerItem` |

## P4 暂缓页

| 模块 | 页面 | 前端路由 | 后端 URL | 暂缓原因 |
| --- | --- | --- | --- | --- |
| 大货管理 | 大货看板 | `/production/home` | `/api/dashboard/overview?company=<company>` | 页面需要 `ProductionDashboard` 读模型；当前仅可降级看 dashboard 汇总。 |
| 物料进销存 | 物料库存 | `/materialStock/materialTypeStock` | `/api/warehouse/stock-ledger` | 库存/财务内核是否自建仍 PARKED；本轮不扩大库存语义。 |

## P3 待补契约页

这些页面当前没有可信 apiPath；前端开发时不得自动猜接口。需要先补页面字段契约，再选择已存在 URL 或进入后端补口任务。

| 模块 | 页面 | 前端路由 | 缺口 |
| --- | --- | --- | --- |
| 基础资料 | 加工厂 | `/foundation/factory` | `Factory` schema 缺失；可参考已存在 `/api/subcontract/factories`，但需先确认字段契约。 |
| 基础资料 | 供应商 | `/foundation/supplier` | `SupplierItem` 已确认 `name/supplier_name/disabled`；连接时使用已存在 `/api/sales-inventory/suppliers`。 |
| 基础资料 | 送货地址 | `/foundation/commonAddress` | `CommonAddress` schema 缺失；候选 `/api/sales-inventory/delivery-addresses` 为 dev readiness。 |
| 基础资料 | 结算方式 | `/foundation/tradeTerm` | `TradeTerm` schema 缺失；候选 `/api/factory-statements/settlement-methods` 为 dev readiness。 |
| 基础资料 | 发票类型 | `/foundation/invoiceType` | `InvoiceType` schema 缺失；候选 `/api/factory-statements/invoice-types` 为 dev readiness。 |
| 基础资料 | 样板类型 | `/foundation/sampleType` | `SampleType` schema 缺失；候选 `/api/bom/sample-types` 为 dev readiness。 |
| 基础资料 | 费用类型 | `/foundation/costType` | `CostType` schema 缺失；候选 `/api/factory-statements/expense-types` 为 dev readiness。 |
| 基础资料 | 尺码排序 | `/foundation/sizeSort` | `SizeSort` schema 缺失；候选 `/api/bom/size-sortings` 为 dev readiness。 |
| 基础资料 | 销售渠道 | `/foundation/distributionChannel` | `DistributionChannel` schema 缺失；候选 `/api/sales-inventory/sales-channels` 为 dev readiness。 |
| 基础资料 | 出纳账户 | `/foundation/bankAccount` | `BankAccount` schema 缺失；候选 `/api/factory-statements/cashier-accounts` 为 dev readiness。 |
| 基础资料 | 工艺要求模板 | `/foundation/workmanshipTemplate` | `WorkmanshipTemplate` schema 缺失；可参考 `/api/bom/process-requirement-templates`。 |
| 基础资料 | 尺寸表模板 | `/foundation/sizeSpecTemplate` | `SizeSpecTemplate` schema 缺失；候选 `/api/bom/size-chart-templates` 为 dev readiness。 |
| 设计打样 | 样板单 | `/sample/sampleListV2` | `SampleOrder` schema 缺失；候选 `/api/bom/sample-orders` 为 dev readiness。 |
| 设计打样 | 跟进模板 | `/sample/trackingTemplate` | `SampleTrackingTemplate` schema 缺失；后端已有 `/api/production/followup-templates`，需确认是否复用。 |
| 大货管理 | 报价单 | `/production/productQuote` | `ProductQuote` schema 缺失，不伪装为 sales-orders。 |
| 大货管理 | 跟进模板 | `/production/factoryPacking/pending` | `ProductionTrackingTemplate` schema 缺失。 |
| 大货管理 | 下单进出数量明细表 | `/production/factoryPacking/list` | `FactoryPacking` schema 缺失。 |
| 大货管理 | 款式打板下单对账表 | `/production/productionTrackingTemplate` | `ProductionTrackingReconcile` schema 缺失。 |
| 大货管理 | 订单生产加工数量对照表 | `/production/report/orderQuantityReport` | 报表读模型缺失，仅 `sales_order/customer/status` 可派生。 |
| 大货管理 | 订单款式利润预测明细表 | `/production/report/productOrderSampleCompare` | 报表读模型缺失。 |
| 大货管理 | 大货成本物料明细表 | `/production/report/orderTrackingReport` | 报表读模型缺失。 |
| 大货管理 | 大货销售预测明细表 | `/production/report/productOrderProfitReport` | 报表读模型缺失。 |
| 大货管理 | 业务员业绩分析报表 | `/production/report/productionCostMaterialDetailReport` | 报表读模型缺失。 |
| 物料采购 | 物料采购单 | `/materialPurchase/materialPurchaseProcess` | 采购单列表 schema 缺失；可参考 `/api/bom/purchase-orders`。 |
| 物料进销存 | 物料加工入仓 | `/materialStock/materialProcessInWarehouse` | 只有单条草稿详情 `/api/warehouse/stock-entry-drafts/{id}`；不写列表 apiPath。 |
| 物料进销存 | 其他入仓 | `/materialStock/materialOtherInWarehouse` | 只有单条草稿详情；不写列表 apiPath。 |
| 物料进销存 | 物料扣仓 | `/materialStock/materialHoldWarehouse` | 只有单条草稿详情；不写列表 apiPath。 |
| 物料进销存 | 采购退料出仓 | `/materialStock/materialPurchaseReturn` | 采购退料出仓列表读模型缺失。 |
| 物料进销存 | 物料销售出仓 | `/materialStock/materialSaleOutWarehouse` | 物料销售出仓列表读模型缺失。 |
| 物料进销存 | 物料调仓 | `/materialStock/materialTransform/pending` | 只有单条草稿详情；不写列表 apiPath。 |
| 物料进销存 | 物料盘点 | `/materialStock/materialTransform/list` | 物料盘点列表读模型缺失。 |
| 物料进销存 | 加工厂应退料报表 | `/materialStock/materialCheck` | 加工厂应退料报表读模型缺失，不误绑 stock-ledger。 |
| 物料进销存 | 库存物料滞留报表 | `/materialStock/report/materialStock` | 库存物料滞留报表读模型缺失，不误绑 stock-ledger。 |

## 闭环必需但当前页面矩阵未覆盖

`contracts/frontend_readiness_page_handoff.md` 已列出六大模块可接端点；若前端新增页面，优先从该清单取 URL 和字段。当前页面矩阵未覆盖但六大闭环会用到的节点包括：生产工单、工单领料、请购、采购入库、采购发票、外发发料、外发收货、应退料、完工入库、发货单、销售发票、应收、账实平、质检列表、工票、计件工资、款式成本、订单毛利。

## 不实施项

- 生产权限源是否脱 ERPNext：PARKED；任务2/3不改 `LINGYI_PERMISSION_SOURCE` 生产约束。
- 库存/财务是否自建：PARKED；任务2/3不补写闭环、不改库存/财务内核语义。
- `*/readiness/*-flow` POST 仅为 dev 回执桩，不能作为生产写接口或前端正式写接口。
