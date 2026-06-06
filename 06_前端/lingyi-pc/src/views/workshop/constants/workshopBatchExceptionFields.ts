export type WorkshopBatchExceptionTone = 'success' | 'info' | 'warning' | 'danger'

export interface WorkshopBatchExceptionSummaryCard {
  key: string
  label: string
  value: string
  hint: string
  tone: WorkshopBatchExceptionTone
}

export interface WorkshopBatchExceptionLineItem {
  key: string
  label: string
  value: string
  tone: WorkshopBatchExceptionTone
}

export interface WorkshopBatchExceptionEntry {
  key: string
  title: string
  owner: string
  source: string
  status: string
  tone: WorkshopBatchExceptionTone
  summary: string
  details: string[]
}

export interface WorkshopBatchExceptionDisabledAction {
  key: string
  label: string
  reason: string
}

export const workshopBatchExceptionRouteContracts = {
  batch: '/workshop/tickets/batch?tab=exception-guard',
  parityAlias: '/production/productOrder -> /workshop/tickets/batch?parity=production-order&tab=exception-guard',
} as const

export const workshopBatchExceptionDisabledActions: WorkshopBatchExceptionDisabledAction[] = [
  {
    key: 'batch-submit',
    label: '批量提交',
    reason: '只读模式：批量提交已禁用，不触发真实批量写入。',
  },
  {
    key: 'job-card-sync',
    label: '工票同步',
    reason: '只读模式：job-card sync 已禁用，不触发 outbox 或 worker。',
  },
  {
    key: 'batch-export',
    label: '导出异常批次',
    reason: '只读模式：导出已禁用，不触发下载或报表生成。',
  },
  {
    key: 'failed-retry',
    label: '失败重试',
    reason: '只读模式：失败重试已禁用，仅保留异常行 readback。',
  },
]

export const workshopBatchExceptionFallbackBlockedReasons = [
  'true batch submit、job-card sync、export 与 backend remediation 均保持 guarded_readonly。',
  'ERPNext、outbox、worker 与 production write path 未开放。',
]
