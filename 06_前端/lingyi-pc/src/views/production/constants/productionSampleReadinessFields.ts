export type ProductionSampleReadinessTagType = 'success' | 'warning' | 'danger' | 'info'

export const PRODUCTION_SAMPLE_READINESS_FIELDS = [
  { key: 'recordCountLabel', label: '计划/条目' },
  { key: 'pendingCountLabel', label: '待同步样衣' },
  { key: 'blockedCountLabel', label: '范围阻断' },
  { key: 'sourceScopeLabel', label: '来源范围' },
  { key: 'coverageLabel', label: '覆盖状态' },
  { key: 'refreshLabel', label: '最后刷新' },
] as const

export type ProductionSampleReadinessFieldKey =
  (typeof PRODUCTION_SAMPLE_READINESS_FIELDS)[number]['key']

export const PRODUCTION_SAMPLE_READINESS_PARITY_LABEL = 'sample-list parity'
export const PRODUCTION_SAMPLE_READINESS_FOCUS_LABEL = 'sample-source'

export const PRODUCTION_SAMPLE_READINESS_READONLY_GUARD_REASON =
  '样衣 readiness 只开放本地只读核对，真实工单下发、释放、同步、导出与 ERPNext 生产写链路均保持禁用。'

export const PRODUCTION_SAMPLE_READINESS_REMAINING_GAP =
  '未开放真实 work-order issue/release/sync/export、ERPNext、outbox、worker 与 production write 执行。'

export const PRODUCTION_SAMPLE_READINESS_WRITE_BOUNDARY =
  'issue / release / sync / export / ERPNext / outbox / worker / production-write disabled'

export const PRODUCTION_SAMPLE_READINESS_DISABLED_ACTIONS = [
  { label: '工单下发', reason: '本地只读试用模式：工单下发已停用' },
  { label: '工单释放', reason: '本地只读试用模式：工单释放已停用' },
  { label: '工序卡同步', reason: '本地只读试用模式：工序卡同步已停用' },
  { label: '导出样衣 readiness', reason: '本地只读试用模式：样衣 readiness 导出已停用' },
  { label: 'ERPNext 同步', reason: '本地只读试用模式：ERPNext 同步已停用' },
  { label: 'Outbox 推送', reason: '本地只读试用模式：Outbox 推送已停用' },
  { label: 'Worker 执行', reason: '本地只读试用模式：Worker 执行已停用' },
  { label: '生产写入', reason: '本地只读试用模式：生产写入已停用' },
] as const
