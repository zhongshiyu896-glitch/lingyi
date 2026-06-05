import {
  DASHBOARD_READONLY_SOURCE_LAYER,
  DASHBOARD_WORKBENCH_REMAINING_GAP,
} from '@/api/dashboard_readonly'

export type DashboardTodoSourceModule = 'dashboard' | 'sales_inventory' | 'warehouse'

export interface DashboardTodoFieldConfig {
  key: string
  title: string
  sourceModule: DashboardTodoSourceModule
  sourceRoute: string
  sourceDescription: string
  entrySource: string
}

export interface DashboardTodoReadonlyActionConfig {
  key: string
  label: string
  reason: string
}

export const DASHBOARD_TODO_FIELDS: DashboardTodoFieldConfig[] = [
  {
    key: 'pending_messages',
    title: '待处理动态老化',
    sourceModule: 'dashboard',
    sourceRoute: '/dashboard/workplace',
    sourceDescription: '来源：kanban messages 与 dashboard route alias，只读核对待处理动态和入口来源。',
    entrySource: 'dashboard/workplace redirect',
  },
  {
    key: 'overdue_orders',
    title: '超期订单老化',
    sourceModule: 'sales_inventory',
    sourceRoute: '/sales-inventory/sales-orders',
    sourceDescription: '来源：订单待办与库存摘要，只读核对超期订单与入口跟进来源。',
    entrySource: 'sales-inventory overdue order',
  },
  {
    key: 'warehouse_warning',
    title: '仓储预警老化',
    sourceModule: 'warehouse',
    sourceRoute: '/warehouse',
    sourceDescription: '来源：仓储预警摘要，只读核对仓储高危与入口来源。',
    entrySource: 'warehouse warning summary',
  },
]

export const DASHBOARD_TODO_READONLY_ACTIONS: DashboardTodoReadonlyActionConfig[] = [
  {
    key: 'approve',
    label: '审批',
    reason: '待办老化与入口来源子区仅支持只读钻取，审批动作保持禁用。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '导出链路不在本切片开放，避免回到首页证据导出或报表写链路。',
  },
  {
    key: 'cross_module_execute',
    label: '跨模块执行',
    reason: '跨模块执行必须留在业务模块内处理，此处只保留只读 drilldown guard。',
  },
]

export { DASHBOARD_READONLY_SOURCE_LAYER, DASHBOARD_WORKBENCH_REMAINING_GAP as DASHBOARD_TODO_REMAINING_GAP }
