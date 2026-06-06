import {
  DASHBOARD_READONLY_SOURCE_LAYER,
  DASHBOARD_WORKBENCH_REMAINING_GAP,
} from '@/api/dashboard_readonly'

export type DashboardAlertSourceModule = 'quality' | 'sales_inventory' | 'warehouse'

export interface DashboardAlertFieldConfig {
  key: string
  title: string
  sourceModule: DashboardAlertSourceModule
  sourceRoute: string
  sourceDescription: string
  summaryIndex?: number
  warningIndex?: number
  todoKey?: string
}

export interface DashboardAlertReadonlyActionConfig {
  key: string
  label: string
  reason: string
}

export interface DashboardAlertReadonlyGuardReasonMap {
  refreshPermission: string
  reloadModuleActions: string
}

export const DASHBOARD_ALERT_READONLY_TAB = 'alert-readonly'
export const DASHBOARD_ALERT_READONLY_PARITY = 'six-module'
export const DASHBOARD_ALERT_READONLY_FOCUS = 'alert-source'
export const DASHBOARD_ALERT_BLOCKED_REASON =
  'dashboard alert readonly 仅允许来源审计与只读复核，真实首页跳转、模块执行与导出修复链路保持阻断。'
export const DASHBOARD_ALERT_READONLY_GUARD =
  '当前页面为 dashboard alert readonly 守卫模式，所有写动作与跨模块执行入口仅保留禁用态说明。'

export const DASHBOARD_ALERT_FIELDS: DashboardAlertFieldConfig[] = [
  {
    key: 'quality_alert',
    title: '质检缺陷告警',
    sourceModule: 'quality',
    sourceRoute: '/quality/inspections',
    sourceDescription: '来源：质检缺陷统计与通过率摘要，只读复核缺陷波动。',
    summaryIndex: 0,
    warningIndex: 0,
  },
  {
    key: 'sales_inventory_alert',
    title: '订单超期与库存告警',
    sourceModule: 'sales_inventory',
    sourceRoute: '/sales-inventory/sales-orders',
    sourceDescription: '来源：订单待办与库存安全线，只读核对超期与补货风险。',
    summaryIndex: 1,
    warningIndex: 1,
    todoKey: 'overdue_orders',
  },
  {
    key: 'warehouse_alert',
    title: '仓储高危告警',
    sourceModule: 'warehouse',
    sourceRoute: '/warehouse',
    sourceDescription: '来源：仓储预警与库存阈值，只读定位高危仓储风险。',
    summaryIndex: 3,
    warningIndex: 2,
    todoKey: 'warehouse_warning',
  },
]

export const DASHBOARD_ALERT_READONLY_ACTIONS: DashboardAlertReadonlyActionConfig[] = [
  {
    key: 'approve',
    label: '审批',
    reason: '经营告警仅支持来源审计与只读复核，审批动作保持禁用。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '导出链路不在本切片开放，避免退回证据导出任务。',
  },
  {
    key: 'cross_module_execute',
    label: '跨模块执行',
    reason: '跨模块执行必须在业务模块内处理，此处只保留只读守卫。',
  },
]

export const DASHBOARD_ALERT_GLOBAL_GUARD_REASON_MAP: DashboardAlertReadonlyGuardReasonMap = {
  refreshPermission: 'dashboard alert readonly 不开放权限刷新，避免影响共享首页守卫状态。',
  reloadModuleActions: 'dashboard alert readonly 不开放模块动作重载，避免触发首页动作链路。',
}

export { DASHBOARD_READONLY_SOURCE_LAYER, DASHBOARD_WORKBENCH_REMAINING_GAP as DASHBOARD_ALERT_REMAINING_GAP }
