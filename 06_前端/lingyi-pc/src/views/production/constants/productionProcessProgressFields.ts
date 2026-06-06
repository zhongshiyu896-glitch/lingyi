export type ProductionProcessProgressTagType = 'success' | 'warning' | 'danger' | 'info'

export type ProductionProcessProgressMetricKey =
  | 'mirroredJobCardCount'
  | 'syncPendingCount'
  | 'blockedCount'
  | 'statusSnapshot'

export const PRODUCTION_PROCESS_PROGRESS_METRIC_FIELDS = [
  { key: 'mirroredJobCardCount', label: '工序已镜像' },
  { key: 'syncPendingCount', label: '同步待完成' },
  { key: 'blockedCount', label: '阻断提示' },
  { key: 'statusSnapshot', label: '状态摘要' },
] as const satisfies ReadonlyArray<{ key: ProductionProcessProgressMetricKey; label: string }>

export const PRODUCTION_PROCESS_PROGRESS_REMAINING_GAPS = [
  '真实生产下发未开放',
  'job-card sync / export / worker 未开放',
  'ERPNext production 与 outbox 写链路未开放',
  '库存与采购写回未开放',
] as const

export const PRODUCTION_PROCESS_PROGRESS_BLOCKED_ACTIONS = [
  { label: '同步工序卡', reason: 'job-card sync 冻结' },
  { label: '导出工序进度', reason: 'export 冻结' },
  { label: 'worker 补偿', reason: 'outbox / worker 冻结' },
] as const
