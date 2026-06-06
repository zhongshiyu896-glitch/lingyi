export type WorkshopTicketJobCardReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export interface WorkshopTicketJobCardReadonlyMetricField {
  key: 'ticketCount' | 'jobCardCount' | 'blockedSyncCount' | 'guardedActionCount'
  label: string
}

export interface WorkshopTicketJobCardReadonlyGuardedAction {
  key:
    | 'dispatch-confirm'
    | 'job-card-sync'
    | 'export'
    | 'worker'
    | 'refresh-permission'
    | 'reload-module-actions'
  label: string
  reason: string
}

export const WORKSHOP_TICKET_JOB_CARD_READONLY_METRIC_FIELDS: WorkshopTicketJobCardReadonlyMetricField[] = [
  { key: 'ticketCount', label: '工票条数' },
  { key: 'jobCardCount', label: '工序卡条数' },
  { key: 'blockedSyncCount', label: '同步阻断条数' },
  { key: 'guardedActionCount', label: '阻断动作数' },
]

export const WORKSHOP_TICKET_JOB_CARD_READONLY_GUARDED_ACTIONS: WorkshopTicketJobCardReadonlyGuardedAction[] = [
  {
    key: 'dispatch-confirm',
    label: '派工 / 确认',
    reason: '当前仅开放 job-card-readonly 只读核对，不开放真实派工或确认执行。',
  },
  {
    key: 'job-card-sync',
    label: 'Job Card 同步',
    reason: '当前仅开放工序卡来源核对，不开放真实 job-card sync、outbox、worker 或 ERPNext 执行。',
  },
  {
    key: 'export',
    label: '导出工票',
    reason: '当前仅开放工票查询只读摘要，不开放真实导出执行。',
  },
  {
    key: 'worker',
    label: 'worker / ERPNext',
    reason: '当前仅开放只读边界，不开放 outbox、worker、ERPNext 或跨模块执行。',
  },
  {
    key: 'refresh-permission',
    label: '刷新权限',
    reason: '当前工票列表页面处于 job-card-readonly 边界，权限刷新入口仅保留只读提示，不执行真实刷新动作。',
  },
  {
    key: 'reload-module-actions',
    label: '重载模块动作',
    reason: '当前工票列表页面仅核对只读边界，模块动作重载入口保持禁用，不执行真实重载。',
  },
]

export const WORKSHOP_TICKET_JOB_CARD_READONLY_ROUTE_LABELS = {
  defaultRoute: '/workshop/tickets',
  parityRoute: '/workshop/tickets?tab=job-card-readonly&parity=production-order',
  focusRoute: '/workshop/tickets?tab=job-card-readonly&parity=production-order&focus=job-card-source',
  sourceLabel: 'job-card-readonly 来源',
  readonlyMode: 'WORKSHOP_TICKET_JOB_CARD_GET_ONLY',
} as const

export const WORKSHOP_TICKET_JOB_CARD_READONLY_GUARD_MESSAGE =
  '当前仅开放工票列表 job-card-readonly、production-order parity 与 job-card-source focus 核对，不开放真实派工、确认、job-card sync、导出、outbox、worker、ERPNext 或跨模块执行。'

export const WORKSHOP_TICKET_JOB_CARD_READONLY_REMAINING_GAP =
  'remaining_gap=真实派工/确认、job-card sync、导出、outbox、worker、ERPNext 与跨模块执行链路未开放；仅保留 job-card-readonly query state、item/status、blocked reason 与 production-order parity 镜像。'

export const WORKSHOP_TICKET_JOB_CARD_READONLY_WRITE_BOUNDARY =
  'dispatch-confirm / job-card-sync / export / worker / refresh-permission / reload-module-actions disabled'
