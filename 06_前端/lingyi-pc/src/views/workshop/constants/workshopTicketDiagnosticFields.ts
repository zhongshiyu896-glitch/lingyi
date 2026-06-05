import type { TagProps } from 'element-plus'

export type WorkshopTicketDiagnosticTagType = NonNullable<TagProps['type']>

export interface WorkshopTicketDiagnosticField {
  key: 'batch_exception' | 'sync_block' | 'reversal_delta'
  title: string
  sourceRoute: '/workshop/tickets?tab=diagnostic'
  sourceModule: 'workshop'
  sourceDescription: string
  blockedReason: string
}

export interface WorkshopTicketDiagnosticGuardedAction {
  key: 'ticket-register' | 'ticket-batch' | 'job-card-sync-retry' | 'ticket-export'
  label: string
  reason: string
}

export interface WorkshopTicketDiagnosticMetricField {
  key: 'ticketCount' | 'exceptionCount' | 'pendingCount' | 'reversalCount'
  label: string
}

export const WORKSHOP_TICKET_DIAGNOSTIC_FIELDS: WorkshopTicketDiagnosticField[] = [
  {
    key: 'batch_exception',
    title: '批次异常摘要',
    sourceRoute: '/workshop/tickets?tab=diagnostic',
    sourceModule: 'workshop',
    sourceDescription: '聚合 failed / dead / blocked_scope 工票，保留批次异常只读摘要。',
    blockedReason: 'blocked_reason=批次异常修复仅在授权流程执行，当前列表只保留只读诊断。',
  },
  {
    key: 'sync_block',
    title: '同步阻断原因',
    sourceRoute: '/workshop/tickets?tab=diagnostic',
    sourceModule: 'workshop',
    sourceDescription: '聚合 pending / processing / blocked_scope 工票，核对同步阻断来源。',
    blockedReason: 'blocked_reason=同步重试与写入链路保持关闭，当前仅开放只读核对。',
  },
  {
    key: 'reversal_delta',
    title: '撤销差异摘要',
    sourceRoute: '/workshop/tickets?tab=diagnostic',
    sourceModule: 'workshop',
    sourceDescription: '聚合 reversal 工票，核对撤销差异和净数量差异来源。',
    blockedReason: 'blocked_reason=撤销修复不在本切片开放范围内，仅允许只读追踪。',
  },
]

export const WORKSHOP_TICKET_DIAGNOSTIC_METRICS: WorkshopTicketDiagnosticMetricField[] = [
  { key: 'ticketCount', label: '工票数' },
  { key: 'exceptionCount', label: '异常条数' },
  { key: 'pendingCount', label: '待同步条数' },
  { key: 'reversalCount', label: '撤销差异条数' },
]

export const WORKSHOP_TICKET_DIAGNOSTIC_READONLY_ACTIONS: WorkshopTicketDiagnosticGuardedAction[] = [
  {
    key: 'ticket-register',
    label: '工票登记',
    reason: '当前仅开放工票异常诊断只读核对，不开放工票登记。',
  },
  {
    key: 'ticket-batch',
    label: '批量导入',
    reason: '当前仅开放批次异常来源核对，不开放批量导入。',
  },
  {
    key: 'job-card-sync-retry',
    label: '重试同步',
    reason: '当前仅开放同步阻断诊断，不开放同步重试。',
  },
  {
    key: 'ticket-export',
    label: '导出',
    reason: '当前仅开放只读诊断视图，不开放导出执行。',
  },
]

export const WORKSHOP_TICKET_DIAGNOSTIC_ROUTE_LABELS = {
  current: '/workshop/tickets',
  diagnostic: '/workshop/tickets?tab=diagnostic',
  sourceLabel: '工票诊断来源',
  readonlyMode: 'WORKSHOP_TICKET_GET_ONLY',
} as const

export const WORKSHOP_TICKET_DIAGNOSTIC_GUARD_MESSAGE =
  '当前仅开放工票列表诊断、批次异常摘要和阻断原因回读，不开放登记、导入、同步、导出或跨模块执行。'

export const WORKSHOP_TICKET_DIAGNOSTIC_REMAINING_GAP =
  'remaining_gap=真实工票登记、批量导入、同步写入、导出和跨模块执行未开放；批次异常仍需人工核对。'
