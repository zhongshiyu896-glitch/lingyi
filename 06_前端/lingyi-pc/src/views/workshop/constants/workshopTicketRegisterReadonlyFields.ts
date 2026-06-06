export type WorkshopTicketRegisterReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export interface WorkshopTicketRegisterReadonlyMetricField {
  key: 'draftFieldCount' | 'missingFieldCount' | 'guardedActionCount' | 'readonlyItemCount'
  label: string
}

export interface WorkshopTicketRegisterReadonlyGuardedAction {
  key:
    | 'register'
    | 'reversal'
    | 'dispatch-confirm'
    | 'export'
    | 'worker'
    | 'refresh-permission'
    | 'reload-module-actions'
  label: string
  reason: string
}

export const WORKSHOP_TICKET_REGISTER_READONLY_METRIC_FIELDS: WorkshopTicketRegisterReadonlyMetricField[] = [
  { key: 'draftFieldCount', label: '草稿字段数' },
  { key: 'missingFieldCount', label: '待补字段数' },
  { key: 'guardedActionCount', label: '阻断动作数' },
  { key: 'readonlyItemCount', label: '只读项数' },
]

export const WORKSHOP_TICKET_REGISTER_READONLY_GUARDED_ACTIONS: WorkshopTicketRegisterReadonlyGuardedAction[] = [
  {
    key: 'register',
    label: '提交登记',
    reason: '当前仅开放 order-parity 只读摘要，不开放真实工票登记写入。',
  },
  {
    key: 'reversal',
    label: '提交撤销',
    reason: '当前仅开放 dispatch-source 只读核对，不开放真实工票撤销写入。',
  },
  {
    key: 'dispatch-confirm',
    label: '派工 / 确认',
    reason: '当前仅开放工票登记 parity 只读核对，不开放真实派工或确认执行。',
  },
  {
    key: 'export',
    label: '导出工票',
    reason: '当前仅开放工票登记只读摘要，不开放真实导出执行。',
  },
  {
    key: 'worker',
    label: 'worker / ERPNext',
    reason: '当前仅开放只读边界，不开放 outbox、worker、ERPNext 或跨模块执行。',
  },
  {
    key: 'refresh-permission',
    label: '刷新权限',
    reason: '当前工票登记页面处于 order-parity 只读边界，权限刷新入口仅保留只读提示，不执行真实刷新动作。',
  },
  {
    key: 'reload-module-actions',
    label: '重载模块动作',
    reason: '当前工票登记页面仅核对只读边界，模块动作重载入口保持禁用，不执行真实重载。',
  },
]

export const WORKSHOP_TICKET_REGISTER_READONLY_ROUTE_LABELS = {
  defaultRoute: '/workshop/tickets/register',
  parityRoute: '/workshop/tickets/register?tab=order-parity&parity=production-order',
  focusRoute: '/workshop/tickets/register?tab=order-parity&parity=production-order&focus=dispatch-source',
  sourceLabel: 'order-parity 来源',
  readonlyMode: 'WORKSHOP_TICKET_REGISTER_GET_ONLY',
} as const

export const WORKSHOP_TICKET_REGISTER_READONLY_GUARD_MESSAGE =
  '当前仅开放工票登记 order-parity 与 dispatch-source 只读核对，不开放真实派工、确认、导出、outbox、worker、ERPNext 或跨模块执行。'

export const WORKSHOP_TICKET_REGISTER_READONLY_REMAINING_GAP =
  'remaining_gap=真实工票登记/撤销、派工确认、导出、outbox、worker、ERPNext 与跨模块执行链路未开放；仅保留 order-parity query state、item/status、blocked reason 与 dispatch-source 镜像。'

export const WORKSHOP_TICKET_REGISTER_READONLY_WRITE_BOUNDARY =
  'register / reversal / dispatch-confirm / export / worker / refresh-permission / reload-module-actions disabled'
