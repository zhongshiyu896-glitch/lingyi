export type StyleProfitReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export type StyleProfitListMetricKey =
  | 'snapshotCount'
  | 'mappedCount'
  | 'unresolvedCount'
  | 'profitRange'

export type StyleProfitDetailMetricKey =
  | 'detailCount'
  | 'sourceMapCount'
  | 'unresolvedCount'
  | 'coverage'

export const STYLE_PROFIT_LIST_METRIC_FIELDS = [
  { key: 'snapshotCount', label: '快照数量' },
  { key: 'mappedCount', label: '已映射来源' },
  { key: 'unresolvedCount', label: '待复核来源' },
  { key: 'profitRange', label: '利润区间' },
] as const satisfies ReadonlyArray<{ key: StyleProfitListMetricKey; label: string }>

export const STYLE_PROFIT_DETAIL_METRIC_FIELDS = [
  { key: 'detailCount', label: '明细行数' },
  { key: 'sourceMapCount', label: '来源映射' },
  { key: 'unresolvedCount', label: '未解析来源' },
  { key: 'coverage', label: '纳入利润' },
] as const satisfies ReadonlyArray<{ key: StyleProfitDetailMetricKey; label: string }>

export const STYLE_PROFIT_PARITY_SCOPE_LABELS: Record<string, string> = {
  '': '款式利润主入口',
  'style-profit': '款式利润主入口',
  default: '款式利润主入口',
}

export const STYLE_PROFIT_REVENUE_STATUS_LABELS: Record<string, string> = {
  actual_first: '实际优先',
  actual_only: '仅实际',
  estimated_only: '仅预估',
}

export const STYLE_PROFIT_SNAPSHOT_STATUS_LABELS: Record<string, string> = {
  complete: '已完成',
  incomplete: '待复核',
}

export const STYLE_PROFIT_ALLOCATION_STATUS_LABELS: Record<string, string> = {
  mapped: '来源已映射',
  partial: '部分映射',
  unresolved: '存在未解析',
  pending: '待补齐来源',
}

export const STYLE_PROFIT_SOURCE_TYPE_LABELS: Record<string, string> = {
  BOM: 'BOM 成本',
  WORK_ORDER: '工单成本',
  STOCK_LEDGER: '库存成本',
  SUBCONTRACT: '外协成本',
  MaterialSnapshot: '物料快照',
  JobCard: '工序工单',
}

export const STYLE_PROFIT_SOURCE_STATUS_LABELS: Record<string, string> = {
  mapped: '已映射',
  partial: '部分映射',
  unresolved: '待复核',
  submitted: '已提交',
  draft: '草稿',
  cancelled: '已取消',
}

export const STYLE_PROFIT_WRITE_BOUNDARY_LABEL = 'ERPNext / 导出 / 真实利润写入 disabled'

export const STYLE_PROFIT_REMAINING_GAP_LABEL =
  '未开放导出、ERPNext、真实利润写入、outbox、worker、生产/库存联动写链路。'
