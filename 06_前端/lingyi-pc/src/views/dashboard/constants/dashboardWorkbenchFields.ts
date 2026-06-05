import {
  DASHBOARD_READONLY_SOURCE_LAYER,
  DASHBOARD_WORKBENCH_REMAINING_GAP,
} from '@/api/dashboard_readonly'

export interface DashboardWorkbenchReadonlyField {
  key: string
  label: string
  routeLabel: string
  sourceTag: string
}

export const DASHBOARD_WORKBENCH_READONLY_FIELDS: DashboardWorkbenchReadonlyField[] = [
  {
    key: 'quality_review',
    label: '质检异常摘要',
    routeLabel: '/quality/inspections',
    sourceTag: `${DASHBOARD_READONLY_SOURCE_LAYER}.quality`,
  },
  {
    key: 'overdue_orders',
    label: '订单超期摘要',
    routeLabel: '/sales-inventory/sales-orders',
    sourceTag: `${DASHBOARD_READONLY_SOURCE_LAYER}.sales_inventory`,
  },
  {
    key: 'warehouse_warning',
    label: '仓储预警摘要',
    routeLabel: '/warehouse',
    sourceTag: `${DASHBOARD_READONLY_SOURCE_LAYER}.warehouse`,
  },
  {
    key: 'inventory_warning',
    label: '低库存摘要',
    routeLabel: '/sales-inventory/stock-ledger',
    sourceTag: `${DASHBOARD_READONLY_SOURCE_LAYER}.sales_inventory`,
  },
]

export { DASHBOARD_READONLY_SOURCE_LAYER, DASHBOARD_WORKBENCH_REMAINING_GAP }
