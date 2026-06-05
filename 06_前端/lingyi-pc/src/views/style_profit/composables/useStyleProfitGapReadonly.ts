import type {
  StyleProfitDetailItem,
  StyleProfitSnapshotListItem,
  StyleProfitSnapshotResult,
  StyleProfitSourceMapItem,
} from '@/api/style_profit'
import { STYLE_PROFIT_WRITE_BOUNDARY_LABEL } from '@/views/style_profit/constants/styleProfitReadonlyFields'

interface StyleProfitGapMetricValues {
  [key: string]: string
}

export interface StyleProfitGapReadonlySummary {
  parityScopeLabel: string
  subtitle: string
  metricValues: StyleProfitGapMetricValues
  differenceSummary: string
  missingSummary: string
  reasonSummary: string
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

const resolveParityScopeLabel = (parity: string): string => {
  if (parity === 'style-profit' || !parity) {
    return '款式利润主入口'
  }
  return `款式利润上下文：${parity}`
}

const buildReasonSummary = (tokens: string[], fallback: string): string => {
  const normalized = [...new Set(tokens.filter(Boolean))]
  if (!normalized.length) {
    return fallback
  }
  return normalized.join('；')
}

export const buildStyleProfitListGapReadonlySummary = (
  rows: StyleProfitSnapshotListItem[],
  parity: string,
): StyleProfitGapReadonlySummary => {
  const sourceVarianceRows = rows.filter((row) => Math.abs(asNumber(row.actual_total_cost) - asNumber(row.standard_total_cost)) > 0.01)
  const missingRows = rows.filter((row) => {
    return row.snapshot_status !== 'complete' || row.allocation_status !== 'mapped' || Number(row.unresolved_count || 0) > 0
  })
  const unresolvedSourceCount = rows.reduce((sum, row) => sum + Number(row.unresolved_count || 0), 0)
  const totalGapAmount = sourceVarianceRows.reduce(
    (sum, row) => sum + Math.abs(asNumber(row.actual_total_cost) - asNumber(row.standard_total_cost)),
    0,
  )

  const reasons: string[] = []
  if (sourceVarianceRows.length > 0) reasons.push('标准成本与实际成本差异')
  if (rows.some((row) => row.snapshot_status !== 'complete')) reasons.push('利润快照待复核')
  if (rows.some((row) => ['partial', 'pending', 'unresolved'].includes(row.allocation_status))) reasons.push('来源映射未完成')
  if (unresolvedSourceCount > 0) reasons.push('未解析来源待补齐')

  return {
    parityScopeLabel: resolveParityScopeLabel(parity),
    subtitle: rows.length > 0 ? '按快照差异与缺项执行只读核对' : '当前展示只读回退样例',
    metricValues: {
      sourceVarianceCount: String(sourceVarianceRows.length),
      missingSnapshotCount: String(missingRows.length),
      unresolvedSourceCount: String(unresolvedSourceCount),
      gapAmount: formatAmount(totalGapAmount),
    },
    differenceSummary:
      sourceVarianceRows.length > 0
        ? `${sourceVarianceRows.length} 条快照存在标准成本与实际成本差异，累计差异 ${formatAmount(totalGapAmount)}。`
        : '当前筛选范围内未发现成本来源差异。',
    missingSummary:
      missingRows.length > 0
        ? `${missingRows.length} 条快照存在利润快照缺项或来源待补齐。`
        : '当前筛选范围内未发现利润快照缺项。',
    reasonSummary: buildReasonSummary(reasons, '当前筛选范围内仅保留只读核对，无新增阻断原因。'),
    readonlyGuardReason: '当前只开放利润缺口、来源差异与缺项原因的只读核对，利润生成、导出、ERPNext 同步和结算写入均已 guarded。',
    writeBoundary: STYLE_PROFIT_WRITE_BOUNDARY_LABEL,
    remainingGap: '真实写链路未开放；成本来源差异与利润快照缺项仍需人工核对。',
  }
}

export const buildStyleProfitDetailGapReadonlySummary = (
  snapshot: StyleProfitSnapshotResult | null,
  details: StyleProfitDetailItem[],
  sourceMaps: StyleProfitSourceMapItem[],
  parity: string,
): StyleProfitGapReadonlySummary => {
  const baselineDelta = Math.abs(asNumber(snapshot?.actual_total_cost) - asNumber(snapshot?.standard_total_cost))
  const unresolvedDetails = details.filter((detail) => detail.is_unresolved)
  const unresolvedMaps = sourceMaps.filter(
    (item) => Boolean(item.unresolved_reason) || item.mapping_status !== 'mapped' || item.source_status === 'unresolved',
  )
  const sourceVarianceCount = sourceMaps.filter(
    (item) => !item.include_in_profit || Boolean(item.unresolved_reason) || item.mapping_status !== 'mapped',
  ).length
  const missingCount = Math.max(snapshot?.unresolved_count ?? 0, unresolvedDetails.length, unresolvedMaps.length)

  const reasonTokens = [
    ...unresolvedDetails.map((detail) => detail.unresolved_reason || ''),
    ...unresolvedMaps.map((item) => item.unresolved_reason || ''),
  ].filter(Boolean)
  if (baselineDelta > 0.01) reasonTokens.push('标准成本与实际成本差异')
  if ((snapshot?.allocation_status || '') !== 'mapped') reasonTokens.push('来源映射未完成')
  if ((snapshot?.snapshot_status || '') !== 'complete') reasonTokens.push('利润快照待复核')

  return {
    parityScopeLabel: resolveParityScopeLabel(parity),
    subtitle: snapshot ? '按来源映射与快照明细定位利润缺口' : '当前展示只读回退样例',
    metricValues: {
      sourceVarianceCount: String(sourceVarianceCount),
      missingSnapshotCount: String(missingCount),
      unresolvedSourceCount: String(unresolvedMaps.length),
      gapAmount: formatAmount(baselineDelta),
    },
    differenceSummary:
      baselineDelta > 0.01
        ? `标准成本基线与实际成本相差 ${formatAmount(baselineDelta)}，需只读核对来源分摊。`
        : sourceVarianceCount > 0
          ? `${sourceVarianceCount} 条来源映射存在差异，需只读核对。`
          : '当前详情未发现成本来源差异。',
    missingSummary:
      missingCount > 0
        ? `${missingCount} 条利润明细或来源映射仍待补齐。`
        : '当前详情未发现利润快照缺项。',
    reasonSummary: buildReasonSummary(reasonTokens, '当前详情仅保留只读核对，无新增缺项原因。'),
    readonlyGuardReason: '详情页只开放缺口核对与来源差异读回，利润生成、导出、ERPNext 同步和结算写入均禁用。',
    writeBoundary: STYLE_PROFIT_WRITE_BOUNDARY_LABEL,
    remainingGap: '诊断结果仅供只读核对；真实写链路、导出和 ERPNext 同步仍未开放。',
  }
}
