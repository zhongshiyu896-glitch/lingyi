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
    | 'daily-wage-export'
    | 'daily-wage-generate'
    | 'daily-wage-sync'
    | 'ticket-register'
    | 'ticket-batch'
    | 'job-card-sync-retry'
  label: string
  route: '/workshop/daily-wages' | '/workshop/tickets'
  reason: string
}

export const WORKSHOP_DAILY_WAGE_READONLY_METRICS: WorkshopDailyWageReadonlyMetricField[] = [
  { key: 'employeeCount', label: '员工数' },
  { key: 'reversalCount', label: '回流工票' },
  { key: 'netQty', label: '净数量' },
  { key: 'totalAmount', label: '工资合计' },
]

export const WORKSHOP_DAILY_WAGE_ROUTE_LABELS = {
  current: '/workshop/daily-wages',
  linked: '/workshop/tickets',
  sourceLabel: '工票回流来源',
  readonlyMode: 'READONLY_GET_ONLY',
} as const

export const WORKSHOP_DAILY_WAGE_GUARD_MESSAGE =
  '当前仅开放日薪统计回读、工票来源核对和异常摘要；生成、同步、回写、登记、批量导入保持只读禁用。'

export const WORKSHOP_DAILY_WAGE_REMAINING_GAP =
  '真实日薪回写、工票登记、批量导入、ERPNext/outbox/worker 未开放。'

export const WORKSHOP_DAILY_WAGE_GUARDED_ACTIONS: WorkshopDailyWageGuardedAction[] = [
  {
    key: 'daily-wage-export',
    label: '导出',
    route: '/workshop/daily-wages',
    reason: '当前仅开放日薪统计只读核对，不开放导出执行。',
  },
  {
    key: 'daily-wage-generate',
    label: '生成',
    route: '/workshop/daily-wages',
    reason: '当前仅开放异常摘要和来源诊断，不开放日薪生成。',
  },
  {
    key: 'daily-wage-sync',
    label: '同步',
    route: '/workshop/daily-wages',
    reason: '当前仅开放只读联动验收，不开放日薪同步。',
  },
  {
    key: 'ticket-register',
    label: '工票登记',
    route: '/workshop/tickets',
    reason: '当前仅开放工票回流只读核对，不开放工票登记。',
  },
  {
    key: 'ticket-batch',
    label: '批量导入',
    route: '/workshop/tickets',
    reason: '当前仅开放回流来源核对，不开放批量导入。',
  },
  {
    key: 'job-card-sync-retry',
    label: '重试同步',
    route: '/workshop/tickets',
    reason: '当前仅开放同步状态只读诊断，不开放同步重试。',
  },
]
