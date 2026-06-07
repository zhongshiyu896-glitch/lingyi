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

export const PRODUCTION_FOLLOWUP_READONLY_FIELDS = [
  { key: 'templateCountLabel', label: '模板条目' },
  { key: 'sampleProcessCountLabel', label: '样衣 parity' },
  { key: 'exceptionCountLabel', label: '异常待核对' },
  { key: 'sourceScopeLabel', label: '来源范围' },
  { key: 'coverageLabel', label: '覆盖状态' },
  { key: 'refreshLabel', label: '最后刷新' },
] as const

export type ProductionFollowupReadonlyFieldKey =
  (typeof PRODUCTION_FOLLOWUP_READONLY_FIELDS)[number]['key']

export const PRODUCTION_FOLLOWUP_PARITY_LABEL = 'production-followup-template parity'
export const PRODUCTION_FOLLOWUP_FOCUS_LABEL = 'followup-source'

export const PRODUCTION_FOLLOWUP_READONLY_GUARD_REASON =
  '生产跟进模板只开放本地只读核对，真实工单下发、释放、同步、导出、ERPNext、outbox、worker 与 production write 链路均保持禁用。'

export const PRODUCTION_FOLLOWUP_WRITE_BOUNDARY =
  'issue / release / sync / export / outbox / worker / ERPNext / production-write / cross-module disabled'

export const PRODUCTION_FOLLOWUP_DISABLED_ACTIONS = [
  { label: '工单下发', reason: '本地只读试用模式：工单下发已停用' },
  { label: '工单释放', reason: '本地只读试用模式：工单释放已停用' },
  { label: '工序卡同步', reason: '本地只读试用模式：工序卡同步已停用' },
  { label: '导出跟进模板', reason: '本地只读试用模式：跟进模板导出已停用' },
  { label: 'Outbox 推送', reason: '本地只读试用模式：Outbox 推送已停用' },
  { label: 'Worker 执行', reason: '本地只读试用模式：Worker 执行已停用' },
  { label: 'ERPNext 同步', reason: '本地只读试用模式：ERPNext 同步已停用' },
  { label: '跨模块执行', reason: '本地只读试用模式：跨模块执行已停用' },
  { label: '生产写入', reason: '本地只读试用模式：生产写入已停用' },
] as const
