export type OperationWageRateReadonlyState =
  | 'ready-readonly'
  | 'query-guarded'
  | 'source-warning'
  | 'permission-guarded'

export type OperationWageRateReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export const OPERATION_WAGE_RATE_READONLY_STATE_LABELS: Record<
  OperationWageRateReadonlyState,
  string
> = {
  'ready-readonly': '工价来源已回读 / 只读守卫',
  'query-guarded': '查询已守卫 / 仅保留只读摘要',
  'source-warning': '来源状态存在预警',
  'permission-guarded': '工价来源只读守卫',
}

export const OPERATION_WAGE_RATE_READONLY_STATE_TAGS: Record<
  OperationWageRateReadonlyState,
  OperationWageRateReadonlyTagType
> = {
  'ready-readonly': 'success',
  'query-guarded': 'warning',
  'source-warning': 'warning',
  'permission-guarded': 'danger',
}

export const OPERATION_WAGE_RATE_READONLY_SUMMARY_FIELDS = [
  { key: 'rateCountLabel', label: '工价条数' },
  { key: 'activeRateCountLabel', label: 'active 条数' },
  { key: 'globalRateCountLabel', label: '通用工价条数' },
  { key: 'blockedActionCountLabel', label: '阻断动作数' },
] as const

export type OperationWageRateReadonlySummaryFieldKey =
  (typeof OPERATION_WAGE_RATE_READONLY_SUMMARY_FIELDS)[number]['key']

export const OPERATION_WAGE_RATE_READONLY_PARITY_LABEL = 'wage-rate parity'
export const OPERATION_WAGE_RATE_READONLY_FOCUS_LABEL = 'rate-source focus'
export const OPERATION_WAGE_RATE_READONLY_GUARD_REASON =
  '当前切片仅开放 wage-rate parity、rate-source focus 与 source/item status 只读核对；真实工价维护、导入、导出、outbox、worker、ERPNext 与 production write 保持冻结。'
export const OPERATION_WAGE_RATE_READONLY_REMAINING_GAP =
  '未开放真实工价维护、导入、导出、outbox、worker、ERPNext 与 production write；仅保留 source query state、rate-source、item/status 与 blocked reason。'
export const OPERATION_WAGE_RATE_READONLY_WRITE_BOUNDARY =
  'GET-only | write_request_count=0 | enabled_write_action_texts=[] | forbidden_write_calls=[]'

export const OPERATION_WAGE_RATE_READONLY_DISABLED_ACTIONS = [
  {
    label: '新增工价',
    reason: 'wage write 链路冻结',
  },
  {
    label: '停用工价',
    reason: 'wage write 链路冻结',
  },
  {
    label: '导入工价',
    reason: 'import / worker 链路冻结',
  },
  {
    label: '导出工价',
    reason: 'export / download 链路冻结',
  },
  {
    label: 'outbox / worker',
    reason: 'outbox / worker 链路冻结',
  },
  {
    label: 'ERPNext 同步',
    reason: 'ERPNext / outbox / worker / production write 链路冻结',
  },
] as const
