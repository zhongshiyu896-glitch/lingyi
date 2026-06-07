import type { TagProps } from 'element-plus'

export type WorkshopDailyWageTagType = NonNullable<TagProps['type']>

export interface WorkshopDailyWageReadonlyTag {
  key: string
  label: string
  type: WorkshopDailyWageTagType
}

export interface WorkshopDailyWageReadonlyMetricField {
  key: string
  label: string
}

export interface WorkshopDailyWageGuardedAction {
  key:
    | 'daily-wage-confirm'
    | 'daily-wage-import'
    | 'daily-wage-export'
    | 'erpnext'
    | 'outbox'
    | 'worker'
    | 'cross-module'
  label: string
  route: '/workshop/daily-wages'
  reason: string
}

export const WORKSHOP_DAILY_WAGE_READONLY_METRICS: WorkshopDailyWageReadonlyMetricField[] = [
  { key: 'employeeCount', label: '员工数' },
  { key: 'reversalCount', label: '回流工票' },
  { key: 'netQty', label: '净数量' },
  { key: 'totalAmount', label: '工资合计' },
]

export const WORKSHOP_DAILY_WAGE_ROUTE_LABELS = {
  defaultRoute: '/workshop/daily-wages',
  sourceLabel: 'daily-wage-source',
  readonlyMode: 'WORKSHOP_DAILY_WAGE_GET_ONLY',
} as const

export const WORKSHOP_DAILY_WAGE_GUARD_MESSAGE =
  'blocked_reason=当前仅开放日工资统计回读、来源核对和异常摘要；确认、导入、导出、ERPNext、outbox、worker 与跨模块执行保持关闭。'

export const WORKSHOP_DAILY_WAGE_READONLY_GUARD =
  'readonly_guard=当前页面处于 daily-wage-readonly，本地仅核对工资统计和来源状态，不开放真实工资确认或跨模块执行。'

export const WORKSHOP_DAILY_WAGE_REMAINING_GAP =
  'remaining_gap=真实日工资确认、批量导入、导出、ERPNext、outbox、worker、production-write 与跨模块执行未开放；当前仅保留 daily-wage-source 与 wage item/status 摘要。'

export const WORKSHOP_DAILY_WAGE_GUARDED_ACTIONS: WorkshopDailyWageGuardedAction[] = [
  {
    key: 'daily-wage-confirm',
    label: '日工资确认',
    route: '/workshop/daily-wages',
    reason: '当前仅开放日工资只读核对，不开放真实确认或回写。',
  },
  {
    key: 'daily-wage-import',
    label: '批量导入',
    route: '/workshop/daily-wages',
    reason: '当前仅开放来源与统计核对，不开放导入执行。',
  },
  {
    key: 'daily-wage-export',
    label: '导出',
    route: '/workshop/daily-wages',
    reason: '当前仅开放日工资只读核对，不开放导出执行。',
  },
  {
    key: 'erpnext',
    label: 'ERPNext',
    route: '/workshop/daily-wages',
    reason: '当前仅开放 daily-wage-source 核对，不开放 ERPNext 适配器链路。',
  },
  {
    key: 'outbox',
    label: 'Outbox',
    route: '/workshop/daily-wages',
    reason: '当前仅开放只读联动验收，不开放 outbox 投递或补偿。',
  },
  {
    key: 'worker',
    label: 'Worker',
    route: '/workshop/daily-wages',
    reason: '当前仅开放只读联动验收，不开放 worker 执行或后台修复。',
  },
  {
    key: 'cross-module',
    label: '跨模块执行',
    route: '/workshop/daily-wages',
    reason: '当前仅开放只读核对，不开放派工、production-write 或跨模块执行链路。',
  },
]
