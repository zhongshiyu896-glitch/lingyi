import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/bom/list',
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
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
