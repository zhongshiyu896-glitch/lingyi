import { createRouter, createWebHistory, type RouteRecordRaw } from 'vue-router'

import { usePermissionStore } from '@/stores/permission'

const z042ReportParityQuery = {
  parity: 'z042-report-parity-source-guard',
  readonly_probe: '1',
  source_trace: 'z042-report-parity-source-trace',
  export_guard: 'z042-report-export-guard-matrix',
  fallback: 'z042-report-fallback-explanation',
  z043_export_eligibility: 'readonly-export-disabled',
  z043_source_grouping: 'finance-and-collaboration-parity',
  z043_disabled_download_reason: 'write-success-not-allowed',
  z043_final_route: '/reports/catalog',
  z044_source_readback: 'finance-collaboration-source-group',
  z044_export_lock_reason: 'readonly-export-lock',
  z044_disabled_download_readback: 'download-disabled-readback',
  z044_final_route_readback: '/reports/catalog',
  z045_source_lock_readback: 'finance-collaboration-source-lock',
  z045_download_denial_reason: 'download-disabled-by-readonly-contract',
  z045_export_lock_notice: 'report-export-locked-by-local-boundary',
  z045_final_route_readback: '/reports/catalog',
  z046_source_grouping: 'report-catalog-source-tabbed-readback',
  z046_download_disabled_hint: 'download-disabled-by-readonly-boundary',
  z046_export_lock_tooltip: 'export-guarded-local-only',
  z046_final_route_readback: '/reports/catalog',
  z046_guarded_matrix_scope: 'report-export-finance-collaboration-detail',
}

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    redirect: '/home',
  },
  {
    path: '/login',
    name: 'LoginPage',
    component: () => import('@/views/auth/LoginPage.vue'),
    meta: { public: true },
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
    beforeEnter: (to) => {
      if (to.query.parity === 'permission-audit' && to.query.tab === 'governance') {
        return {
          path: '/permissions/governance',
          query: { tab: 'audit-readiness' },
        }
      }
      return true
    },
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
    beforeEnter: (to) => {
      if (to.query.entry === 'module-availability') {
        return {
          path: '/cross-module/view',
          query: { tab: 'module-availability' },
        }
      }
      return true
    },
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
    redirect: '/home?tab=module-shortcuts',
  },
  {
    path: '/foundation/customer',
    redirect: { path: '/sales-inventory/references', query: { tab: 'customers', parity: 'foundation-customer' } },
  },
  {
    path: '/foundation/supplier',
    redirect: '/sales-inventory/references?tab=suppliers&parity=foundation-supplier',
  },
  {
    path: '/foundation/factory',
    redirect: { path: '/factory-statements/list', query: { parity: 'foundation-factory', tab: 'source-parity' } },
  },
  {
    path: '/foundation/warehouse',
    redirect: { path: '/warehouse', query: { parity: 'foundation-warehouse' } },
  },
  {
    path: '/material/materialFabric',
    redirect: '/warehouse?tab=permission-mode&parity=foundation-material',
  },
  {
    path: '/goodsPlan/materialSamples',
    redirect: { path: '/bom/list', query: { parity: 'goodsplan-material-samples', tab: 'exception-baseline' } },
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
    redirect: { path: '/workshop/tickets/batch', query: { parity: 'production-order', tab: 'exception-guard' } },
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
    redirect: { path: '/warehouse', query: { parity: 'product-stock', tab: 'traceability' } },
  },
  {
    path: '/productStock/productStockProcess',
    redirect: { path: '/warehouse', query: { parity: 'product-stock', tab: 'traceability' } },
  },
  {
    path: '/financial/financialReport/customerReconciliationReport',
    redirect: {
      path: '/reports/catalog',
      query: {
        ...z042ReportParityQuery,
        parity: 'financial-customer-reconciliation-report',
        source_entry: 'customer-reconciliation-report',
      },
    },
  },
  {
    path: '/financial/financialProcess',
    redirect: {
      path: '/reports/catalog',
      query: {
        ...z042ReportParityQuery,
        parity: 'financial-process-report',
        source_entry: 'financial-process',
      },
    },
  },
  {
    path: '/finance/bank-flow',
    redirect: {
      path: '/reports/catalog',
      query: {
        ...z042ReportParityQuery,
        parity: 'finance-bank-flow-report',
        source_entry: 'bank-flow',
      },
    },
  },
  {
    path: '/finance/receipts-payments',
    redirect: {
      path: '/reports/catalog',
      query: { parity: 'finance-receipts-payments-report', readonly_probe: '1' },
    },
  },
  {
    path: '/finance/reconciliation',
    redirect: {
      path: '/reports/catalog',
      query: { parity: 'finance-reconciliation-report', readonly_probe: '1' },
    },
  },
  {
    path: '/reportManage/collaborationReport/factoryProductStockReport',
    redirect: {
      path: '/reports/catalog',
      query: {
        ...z042ReportParityQuery,
        parity: 'collaboration-factory-product-stock-report',
        source_entry: 'factory-product-stock-report',
      },
    },
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

router.beforeEach(async (to) => {
  const permissionStore = usePermissionStore()
  const redirectPath =
    typeof to.query.redirect === 'string' && to.query.redirect.startsWith('/') ? to.query.redirect : '/home'

  if (to.meta.public) {
    if (to.name === 'LoginPage') {
      try {
        await permissionStore.loadCurrentUser({ force: true })
      } catch {
        // Keep the login page reachable when the session probe fails closed.
      }
      if (permissionStore.state.username && permissionStore.state.status !== 'guest') {
        return redirectPath
      }
    }
    return true
  }

  try {
    await permissionStore.loadCurrentUser({ force: true })
  } catch {
    // Route auth is fail-closed below when no authenticated session is available.
  }

  if (permissionStore.state.username && permissionStore.state.status !== 'guest') {
    return true
  }

  return {
    path: '/login',
    query: { redirect: to.fullPath },
  }
})

export default router
