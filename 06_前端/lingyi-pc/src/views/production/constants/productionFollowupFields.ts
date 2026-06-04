export type ProductionFollowupTagType = 'success' | 'warning' | 'danger' | 'info'

export type ProductionFollowupMetricKey =
  | 'templateCount'
  | 'sampleProcessCount'
  | 'exceptionCount'
  | 'progressSnapshot'

export const PRODUCTION_FOLLOWUP_METRIC_FIELDS = [
  { key: 'templateCount', label: '模板快照' },
  { key: 'sampleProcessCount', label: '样衣 parity' },
  { key: 'exceptionCount', label: '异常待核对' },
  { key: 'progressSnapshot', label: '进度摘要' },
] as const satisfies ReadonlyArray<{ key: ProductionFollowupMetricKey; label: string }>

export const PRODUCTION_FOLLOWUP_PARITY_SCOPE_LABELS: Record<string, string> = {
  '': '主入口只读',
  'sample-list': '样衣流程 parity',
  'production-order': '订单计划镜像',
  'production-followup-template': '生产跟进模板 parity',
}

export const PRODUCTION_FOLLOWUP_REMAINING_GAPS = [
  '真实生产派工未开放',
  '生产状态变更未开放',
  'job-card sync / outbox / worker 未开放',
  'ERPNext production 与库存影响未开放',
] as const
