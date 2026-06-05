export type StyleProfitGapMetricKey =
  | 'sourceVarianceCount'
  | 'missingSnapshotCount'
  | 'unresolvedSourceCount'
  | 'gapAmount'

export interface StyleProfitGapMetricField {
  key: StyleProfitGapMetricKey
  label: string
}

export const STYLE_PROFIT_GAP_LIST_METRIC_FIELDS = [
  { key: 'sourceVarianceCount', label: '差异快照' },
  { key: 'missingSnapshotCount', label: '缺项快照' },
  { key: 'unresolvedSourceCount', label: '未解析来源' },
  { key: 'gapAmount', label: '累计差异' },
] as const satisfies ReadonlyArray<StyleProfitGapMetricField>

export const STYLE_PROFIT_GAP_DETAIL_METRIC_FIELDS = [
  { key: 'sourceVarianceCount', label: '差异来源' },
  { key: 'missingSnapshotCount', label: '缺项明细' },
  { key: 'unresolvedSourceCount', label: '未解析来源' },
  { key: 'gapAmount', label: '基线差异' },
] as const satisfies ReadonlyArray<StyleProfitGapMetricField>
