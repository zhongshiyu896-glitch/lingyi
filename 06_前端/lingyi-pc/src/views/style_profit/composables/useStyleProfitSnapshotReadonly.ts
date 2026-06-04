import type {
  StyleProfitDetailItem,
  StyleProfitSnapshotListItem,
  StyleProfitSnapshotResult,
  StyleProfitSourceMapItem,
} from '@/api/style_profit'
import {
  STYLE_PROFIT_ALLOCATION_STATUS_LABELS,
  STYLE_PROFIT_PARITY_SCOPE_LABELS,
  STYLE_PROFIT_REMAINING_GAP_LABEL,
  STYLE_PROFIT_REVENUE_STATUS_LABELS,
  STYLE_PROFIT_SNAPSHOT_STATUS_LABELS,
  STYLE_PROFIT_SOURCE_STATUS_LABELS,
  STYLE_PROFIT_SOURCE_TYPE_LABELS,
  STYLE_PROFIT_WRITE_BOUNDARY_LABEL,
  type StyleProfitDetailMetricKey,
  type StyleProfitListMetricKey,
  type StyleProfitReadonlyTagType,
} from '@/views/style_profit/constants/styleProfitReadonlyFields'

interface StyleProfitReadonlyMetricValues<T extends string> {
  [key: string]: string
}

export interface StyleProfitListReadonlySummary {
  parityScopeLabel: string
  readonlySourceLabel: string
  revenueModeLabel: string
  snapshotStatusLabel: string
  allocationStatusLabel: string
  sourceTypeLabel: string
  sourceStatusLabel: string
  sourceTypeTone: StyleProfitReadonlyTagType
  sourceStatusTone: StyleProfitReadonlyTagType
  snapshotStatusTone: StyleProfitReadonlyTagType
  metricValues: StyleProfitReadonlyMetricValues<StyleProfitListMetricKey>
  readonlyGuardReason: string
  writeBoundary: string
  remainingGap: string
}

export interface StyleProfitDetailReadonlySummary {
  parityScopeLabel: string
  readonlySourceLabel: string
  revenueModeLabel: string
  snapshotStatusLabel: string
  allocationStatusLabel: string
  sourceTypeLabel: string
  sourceStatusLabel: string
  sourceTypeTone: StyleProfitReadonlyTagType
  sourceStatusTone: StyleProfitReadonlyTagType
  snapshotStatusTone: StyleProfitReadonlyTagType
  metricValues: StyleProfitReadonlyMetricValues<StyleProfitDetailMetricKey>
  readonlyGuardReason: string
  writeBoundary: string
  remainingGap: string
}

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const asNumber = (value: string | number | null | undefined): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const resolveLabel = (value: string | null | undefined, labels: Record<string, string>, fallback: string): string => {
  if (!value) return fallback
  return labels[value] || value
}

const resolveToneByStatus = (value: string | null | undefined): StyleProfitReadonlyTagType => {
  if (value === 'complete' || value === 'mapped') return 'success'
  if (value === 'incomplete' || value === 'partial') return 'warning'
  if (value === 'unresolved') return 'danger'
  return 'info'
}

const joinUniqueLabels = (values: Array<string | null | undefined>, labels: Record<string, string>, fallback: string): string => {
  const normalized = values
    .map((value) => resolveLabel(value || '', labels, ''))
    .filter((value) => value && value !== '-')
  if (!normalized.length) return fallback
  return [...new Set(normalized)].join(' / ')
}

const resolveParityScopeLabel = (parity: string): string =>
  STYLE_PROFIT_PARITY_SCOPE_LABELS[parity] || STYLE_PROFIT_PARITY_SCOPE_LABELS.default

export const buildStyleProfitListReadonlySummary = (
  rows: StyleProfitSnapshotListItem[],
  parity: string,
): StyleProfitListReadonlySummary => {
  const snapshotCount = rows.length
  const mappedCount = rows.filter((row) => row.allocation_status === 'mapped').length
  const unresolvedCount = rows.reduce((sum, row) => sum + Number(row.unresolved_count || 0), 0)
  const profits = rows.map((row) => asNumber(row.profit_amount))
  const minProfit = profits.length ? Math.min(...profits) : null
  const maxProfit = profits.length ? Math.max(...profits) : null
  const revenueModeLabel = joinUniqueLabels(
    rows.map((row) => row.revenue_status),
    STYLE_PROFIT_REVENUE_STATUS_LABELS,
    '本地只读回退',
  )
  const snapshotStatusLabel = joinUniqueLabels(
    rows.map((row) => row.snapshot_status),
    STYLE_PROFIT_SNAPSHOT_STATUS_LABELS,
    '待复核',
  )
  const allocationStatusLabel = unresolvedCount > 0
    ? '存在未解析 / 待复核'
    : joinUniqueLabels(
        rows.map((row) => row.allocation_status),
        STYLE_PROFIT_ALLOCATION_STATUS_LABELS,
        '待补齐来源',
      )
  const sourceStatusLabel = unresolvedCount > 0 ? '待复核' : snapshotCount > 0 ? '已映射' : '本地只读回退'
  const sourceTypeLabel = snapshotCount > 0 ? '利润快照汇总' : '本地只读回退'

  return {
    parityScopeLabel: resolveParityScopeLabel(parity),
    readonlySourceLabel: snapshotCount > 0 ? '成本来源来自利润快照只读回读' : '当前展示本地只读回退样例',
    revenueModeLabel,
    snapshotStatusLabel,
    allocationStatusLabel,
    sourceTypeLabel,
    sourceStatusLabel,
    sourceTypeTone: snapshotCount > 0 ? 'success' : 'info',
    sourceStatusTone: unresolvedCount > 0 ? 'danger' : snapshotCount > 0 ? 'success' : 'info',
    snapshotStatusTone: rows.some((row) => row.snapshot_status === 'incomplete') ? 'warning' : 'success',
    metricValues: {
      snapshotCount: String(snapshotCount),
      mappedCount: String(mappedCount),
      unresolvedCount: String(unresolvedCount),
      profitRange:
        minProfit === null || maxProfit === null
          ? '-'
          : `${formatAmount(minProfit)} ~ ${formatAmount(maxProfit)}`,
    },
    readonlyGuardReason: 'ERPNext、导出和真实利润写入入口仅保留 guarded 状态，当前页面只做只读回读。',
    writeBoundary: STYLE_PROFIT_WRITE_BOUNDARY_LABEL,
    remainingGap: STYLE_PROFIT_REMAINING_GAP_LABEL,
  }
}

export const buildStyleProfitDetailReadonlySummary = (
  snapshot: StyleProfitSnapshotResult | null,
  details: StyleProfitDetailItem[],
  sourceMaps: StyleProfitSourceMapItem[],
  parity: string,
): StyleProfitDetailReadonlySummary => {
  const unresolvedFromDetails = details.filter((detail) => detail.is_unresolved).length
  const unresolvedFromSourceMaps = sourceMaps.filter((item) => Boolean(item.unresolved_reason)).length
  const unresolvedCount = snapshot?.unresolved_count ?? Math.max(unresolvedFromDetails, unresolvedFromSourceMaps)
  const sourceMapCount = sourceMaps.length
  const includedCount = sourceMaps.filter((item) => item.include_in_profit).length
  const revenueModeLabel = resolveLabel(snapshot?.revenue_status, STYLE_PROFIT_REVENUE_STATUS_LABELS, '本地只读回退')
  const snapshotStatusLabel = resolveLabel(snapshot?.snapshot_status, STYLE_PROFIT_SNAPSHOT_STATUS_LABELS, '待复核')
  const allocationStatusLabel = resolveLabel(snapshot?.allocation_status, STYLE_PROFIT_ALLOCATION_STATUS_LABELS, '待补齐来源')
  const sourceTypeLabel =
    joinUniqueLabels(
      sourceMaps.map((item) => item.source_system || item.source_doctype),
      STYLE_PROFIT_SOURCE_TYPE_LABELS,
      '',
    ) ||
    joinUniqueLabels(details.map((item) => item.source_type), STYLE_PROFIT_SOURCE_TYPE_LABELS, '本地只读回退')
  const sourceStatusLabel =
    unresolvedCount > 0
      ? '待复核'
      : joinUniqueLabels(
          sourceMaps.map((item) => item.source_status || item.mapping_status),
          STYLE_PROFIT_SOURCE_STATUS_LABELS,
          '已映射',
        )

  return {
    parityScopeLabel: resolveParityScopeLabel(parity),
    readonlySourceLabel: snapshot ? '当前详情来自利润快照只读回读' : '当前详情为本地只读回退样例',
    revenueModeLabel,
    snapshotStatusLabel,
    allocationStatusLabel,
    sourceTypeLabel: sourceTypeLabel || '本地只读回退',
    sourceStatusLabel,
    sourceTypeTone: sourceMapCount > 0 ? 'success' : 'warning',
    sourceStatusTone: unresolvedCount > 0 ? 'danger' : 'success',
    snapshotStatusTone: resolveToneByStatus(snapshot?.snapshot_status),
    metricValues: {
      detailCount: String(details.length),
      sourceMapCount: String(sourceMapCount),
      unresolvedCount: String(unresolvedCount),
      coverage: sourceMapCount > 0 ? `${includedCount}/${sourceMapCount} 纳入利润` : '-',
    },
    readonlyGuardReason: '详情页只开放来源追溯与利润明细读回，ERPNext、导出和真实利润写入动作均禁用。',
    writeBoundary: STYLE_PROFIT_WRITE_BOUNDARY_LABEL,
    remainingGap: STYLE_PROFIT_REMAINING_GAP_LABEL,
  }
}
