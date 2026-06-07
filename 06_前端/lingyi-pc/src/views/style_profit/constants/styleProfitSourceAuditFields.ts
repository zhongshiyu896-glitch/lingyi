export type StyleProfitSourceAuditTagTone = 'success' | 'warning' | 'danger' | 'info'

export type StyleProfitSourceAuditMetricKey =
  | 'snapshotCount'
  | 'sourceCount'
  | 'unresolvedCount'
  | 'guardedActionCount'

export interface StyleProfitSourceAuditMetricField {
  key: StyleProfitSourceAuditMetricKey
  label: string
}

export interface StyleProfitSourceAuditGuardedAction {
  key:
    | 'recalculate'
    | 'export'
    | 'submit'
    | 'source-collector-write'
    | 'erpnext-outbox-worker'
  label: string
  reason: string
}

export const STYLE_PROFIT_SOURCE_AUDIT_METRIC_FIELDS: ReadonlyArray<StyleProfitSourceAuditMetricField> = [
  { key: 'snapshotCount', label: '快照条数' },
  { key: 'sourceCount', label: '来源样本' },
  { key: 'unresolvedCount', label: '待复核来源' },
  { key: 'guardedActionCount', label: '阻断动作数' },
]

export const STYLE_PROFIT_SOURCE_AUDIT_GUARDED_ACTIONS: ReadonlyArray<StyleProfitSourceAuditGuardedAction> = [
  {
    key: 'recalculate',
    label: '利润重算',
    reason: '当前仅开放 source-audit 只读核对，不开放真实利润重算。',
  },
  {
    key: 'export',
    label: '导出 / 打印',
    reason: '当前仅开放 source-audit 只读核对，不开放真实导出或打印执行。',
  },
  {
    key: 'submit',
    label: '提交 / 留档 / 保存',
    reason: '当前仅开放 source-audit 只读核对，不开放真实提交、留档或保存。',
  },
  {
    key: 'source-collector-write',
    label: 'Source Collector 写入',
    reason: '当前仅开放 source-audit 只读核对，不开放 source collector 写入或回填。',
  },
  {
    key: 'erpnext-outbox-worker',
    label: 'ERPNext / outbox / worker',
    reason: '当前仅开放 source-audit 只读核对，不开放 ERPNext、outbox、worker 或生产写入执行。',
  },
]

export const STYLE_PROFIT_SOURCE_AUDIT_BLOCKED_REASON =
  'blocked_reason=当前仅开放 source-audit / provenance 只读核对，不允许真实利润重算、导出、提交、source collector 写入、ERPNext、outbox、worker 或生产写入。'

export const STYLE_PROFIT_SOURCE_AUDIT_READONLY_GUARD_MESSAGE =
  '当前仅开放 source-audit、style-profit parity 与只读来源核对，不开放真实利润重算、导出、提交、source collector 写入、ERPNext、outbox、worker 或生产写入执行。'

export const STYLE_PROFIT_SOURCE_AUDIT_REMAINING_GAP =
  'remaining_gap=真实利润重算、导出、提交、source collector 写入、ERPNext、outbox、worker 与生产写链路未开放；仅保留 source-audit query state、blocked reason、style-profit parity 与 source/item status 镜像。'

export const STYLE_PROFIT_SOURCE_AUDIT_WRITE_BOUNDARY =
  'recalculate / export / submit / source-collector-write / ERPNext / outbox / worker disabled'
