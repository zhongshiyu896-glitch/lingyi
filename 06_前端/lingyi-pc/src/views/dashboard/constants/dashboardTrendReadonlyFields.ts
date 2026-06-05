import {
  DASHBOARD_READONLY_SOURCE_LAYER,
  DASHBOARD_WORKBENCH_REMAINING_GAP,
} from '@/api/dashboard_readonly'

export type DashboardTrendSourceModule = 'quality' | 'sales_inventory' | 'warehouse' | 'system'

export interface DashboardTrendFieldConfig {
  key: string
  label: string
  sourceModule: DashboardTrendSourceModule
  sourceDescription: string
  healthCheckName?: string
}

export interface DashboardTrendReadonlyActionConfig {
  key: string
  label: string
  reason: string
}

export const DASHBOARD_TREND_FIELDS: DashboardTrendFieldConfig[] = [
  {
    key: 'quality_freshness',
    label: '质检来源新鲜度',
    sourceModule: 'quality',
    sourceDescription: '来源：质检统计摘要，只读核对缺陷与通过率更新时间。',
  },
  {
    key: 'sales_inventory_freshness',
    label: '订单与库存来源新鲜度',
    sourceModule: 'sales_inventory',
    sourceDescription: '来源：订单待办与库存安全线，只读核对库存风险刷新状态。',
  },
  {
    key: 'warehouse_freshness',
    label: '仓储来源新鲜度',
    sourceModule: 'warehouse',
    sourceDescription: '来源：仓储预警与阈值摘要，只读核对高危仓储刷新状态。',
  },
  {
    key: 'system_freshness',
    label: '系统健康时间戳',
    sourceModule: 'system',
    sourceDescription: '来源：system health summary，只读核对 dashboard 读侧健康时间。',
    healthCheckName: 'readonly_contract',
  },
]

export const DASHBOARD_TREND_READONLY_ACTIONS: DashboardTrendReadonlyActionConfig[] = [
  {
    key: 'approve',
    label: '审批',
    reason: '趋势时窗与来源新鲜度子区仅支持只读核对，审批动作保持禁用。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '导出链路不在本切片开放，避免退回证据导出或报表写链路。',
  },
  {
    key: 'cross_module_execute',
    label: '跨模块执行',
    reason: '跨模块执行必须留在业务模块内处理，此处只保留只读守卫。',
  },
]

export { DASHBOARD_READONLY_SOURCE_LAYER, DASHBOARD_WORKBENCH_REMAINING_GAP as DASHBOARD_TREND_REMAINING_GAP }
