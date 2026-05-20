import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/home',
    name: 'HomePage',
    component: () => import('@/views/HomePage.vue'),
  },
  {
    path: '/bom/list',
    name: 'BomList',
    component: () => import('@/views/bom/BomList.vue'),
    meta: { module: 'bom' },
  },
  {
    path: '/bom/detail',
    name: 'BomDetail',
    component: () => import('@/views/bom/BomDetail.vue'),
    meta: { module: 'bom' },
  },
  {
    path: '/production/plans',
    name: 'ProductionPlanList',
    component: () => import('@/views/production/ProductionPlanList.vue'),
    meta: { module: 'production' },
  },
  {
    path: '/production/plans/detail',
    name: 'ProductionPlanDetail',
    component: () => import('@/views/production/ProductionPlanDetail.vue'),
    meta: { module: 'production' },
  },
  {
    path: '/subcontract/list',
    name: 'SubcontractOrderList',
    component: () => import('@/views/subcontract/SubcontractOrderList.vue'),
    meta: { module: 'subcontract' },
  },
  {
    path: '/subcontract/detail',
    name: 'SubcontractOrderDetail',
    component: () => import('@/views/subcontract/SubcontractOrderDetail.vue'),
    meta: { module: 'subcontract' },
  },
  {
    path: '/workshop/tickets',
    name: 'WorkshopTicketList',
    component: () => import('@/views/workshop/WorkshopTicketList.vue'),
    meta: { module: 'workshop' },
  },
  {
    path: '/workshop/tickets/register',
    name: 'WorkshopTicketRegister',
    component: () => import('@/views/workshop/WorkshopTicketRegister.vue'),
    meta: { module: 'workshop' },
  },
  {
    path: '/workshop/tickets/batch',
    name: 'WorkshopTicketBatch',
    component: () => import('@/views/workshop/WorkshopTicketBatch.vue'),
    meta: { module: 'workshop' },
  },
  {
    path: '/workshop/daily-wages',
    name: 'WorkshopDailyWage',
    component: () => import('@/views/workshop/WorkshopDailyWage.vue'),
    meta: { module: 'workshop' },
  },
  {
    path: '/workshop/wage-rates',
    name: 'WorkshopWageRate',
    component: () => import('@/views/workshop/OperationWageRate.vue'),
    meta: { module: 'workshop' },
  },
  {
    path: '/reports/catalog',
    name: 'ReportCatalog',
    component: () => import('@/views/reports/ReportCatalog.vue'),
    meta: { module: 'report' },
  },
  {
    path: '/permissions/governance',
    name: 'PermissionGovernance',
    component: () => import('@/views/system/PermissionGovernance.vue'),
    meta: { module: 'permission' },
  },
  {
    path: '/system/management',
    name: 'SystemManagement',
    component: () => import('@/views/system/SystemManagement.vue'),
    meta: { module: 'system' },
  },
  {
    path: '/reports/style-profit',
    name: 'StyleProfitSnapshotList',
    component: () => import('@/views/style_profit/StyleProfitSnapshotList.vue'),
    meta: { module: 'style_profit' },
  },
  {
    path: '/reports/style-profit/detail',
    name: 'StyleProfitSnapshotDetail',
    component: () => import('@/views/style_profit/StyleProfitSnapshotDetail.vue'),
    meta: { module: 'style_profit' },
  },
  {
    path: '/factory-statements/list',
    name: 'FactoryStatementList',
    component: () => import('@/views/factory_statement/FactoryStatementList.vue'),
    meta: { module: 'factory_statement' },
  },
  {
    path: '/factory-statements/detail',
    name: 'FactoryStatementDetail',
    component: () => import('@/views/factory_statement/FactoryStatementDetail.vue'),
    meta: { module: 'factory_statement' },
  },
  {
    path: '/factory-statements/print',
    name: 'FactoryStatementPrint',
    component: () => import('@/views/factory_statement/FactoryStatementPrint.vue'),
    meta: { module: 'factory_statement' },
  },
  {
    path: '/sales-inventory/sales-orders',
    name: 'SalesInventorySalesOrderList',
    component: () => import('@/views/sales_inventory/SalesInventorySalesOrderList.vue'),
    meta: { module: 'sales_inventory' },
  },
  {
    path: '/sales-inventory/sales-orders/detail',
    name: 'SalesInventorySalesOrderDetail',
    component: () => import('@/views/sales_inventory/SalesInventorySalesOrderDetail.vue'),
    meta: { module: 'sales_inventory' },
  },
  {
    path: '/sales-inventory/stock-ledger',
    name: 'SalesInventoryStockLedger',
    component: () => import('@/views/sales_inventory/SalesInventoryStockLedger.vue'),
    meta: { module: 'sales_inventory' },
  },
  {
    path: '/sales-inventory/references',
    name: 'SalesInventoryReferenceList',
    component: () => import('@/views/sales_inventory/SalesInventoryReferenceList.vue'),
    meta: { module: 'sales_inventory' },
  },
  {
    path: '/warehouse',
    name: 'WarehouseDashboard',
    component: () => import('@/views/warehouse/WarehouseDashboard.vue'),
    meta: { module: 'warehouse' },
  },
  {
    path: '/dashboard/overview',
    name: 'DashboardOverview',
    component: () => import('@/views/dashboard/DashboardOverview.vue'),
    meta: { module: 'dashboard' },
  },
  {
    path: '/quality/inspections',
    name: 'QualityInspectionList',
    component: () => import('@/views/quality/QualityInspectionList.vue'),
    meta: { module: 'quality' },
  },
  {
    path: '/quality/inspections/detail',
    name: 'QualityInspectionDetail',
    component: () => import('@/views/quality/QualityInspectionDetail.vue'),
    meta: { module: 'quality' },
  },
  {
    path: '/cross-module/view',
    name: 'CrossModuleView',
    component: () => import('@/views/cross_module/CrossModuleView.vue'),
    meta: { module: 'sales_inventory' },
  },
  // Yisuan module-entry parity aliases (readonly navigation only).
  {
    path: '/dashboard/workplace',
    redirect: '/dashboard/overview',
  },
  {
    path: '/foundation/customer',
    redirect: { path: '/sales-inventory/references', query: { tab: 'customers', parity: 'foundation-customer' } },
  },
  {
    path: '/foundation/supplier',
    redirect: { path: '/factory-statements/list', query: { parity: 'foundation-supplier' } },
  },
  {
    path: '/foundation/factory',
    redirect: { path: '/factory-statements/list', query: { parity: 'foundation-factory' } },
  },
  {
    path: '/foundation/warehouse',
    redirect: { path: '/warehouse', query: { parity: 'foundation-warehouse' } },
  },
  {
    path: '/material/materialFabric',
    redirect: { path: '/bom/list', query: { parity: 'material-fabric' } },
  },
  {
    path: '/goodsPlan/materialSamples',
    redirect: { path: '/bom/list', query: { parity: 'goodsplan-material-samples' } },
  },
  {
    path: '/goodsPlan/goodsPlanProcess',
    redirect: { path: '/bom/list', query: { parity: 'goodsplan-material-samples' } },
  },
  {
    path: '/product/product',
    redirect: { path: '/bom/list', query: { parity: 'product-style' } },
  },
  {
    path: '/sample/sampleListV2',
    redirect: { path: '/production/plans', query: { parity: 'sample-list' } },
  },
  {
    path: '/sample/sampleProcess',
    redirect: { path: '/production/plans', query: { parity: 'sample-list' } },
  },
  {
    path: '/production/productOrder',
    redirect: { path: '/sales-inventory/sales-orders', query: { parity: 'production-order' } },
  },
  {
    path: '/production/productionProcess',
    redirect: { path: '/production/plans', query: { parity: 'production-followup-template' } },
  },
  {
    path: '/materialPurchase/materialPurchaseProcess',
    redirect: { path: '/subcontract/list', query: { parity: 'material-purchase' } },
  },
  {
    path: '/materialStock/materialTypeStock',
    redirect: { path: '/sales-inventory/stock-ledger', query: { parity: 'material-stock' } },
  },
  {
    path: '/materialStock/materialStockProcess',
    redirect: { path: '/sales-inventory/stock-ledger', query: { parity: 'material-stock' } },
  },
  {
    path: '/productStock/productStockList',
    redirect: { path: '/warehouse', query: { parity: 'product-stock' } },
  },
  {
    path: '/productStock/productStockProcess',
    redirect: { path: '/warehouse', query: { parity: 'product-stock' } },
  },
  {
    path: '/financial/financialReport/customerReconciliationReport',
    redirect: { path: '/reports/catalog', query: { parity: 'customer-reconciliation' } },
  },
  {
    path: '/financial/financialProcess',
    redirect: { path: '/reports/catalog', query: { parity: 'customer-reconciliation' } },
  },
  {
    path: '/reportManage/collaborationReport/factoryProductStockReport',
    redirect: { path: '/reports/catalog', query: { parity: 'factory-product-stock' } },
  },
  {
    path: '/app/:pathMatch(.*)*',
    redirect: '/home',
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/home',
  },
]

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes,
})

export default router
