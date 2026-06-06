import { computed, unref, type ComputedRef, type MaybeRef, type Ref } from 'vue'
import type {
  StyleProfitDetailItem,
  StyleProfitSnapshotListItem,
  StyleProfitSnapshotResult,
  StyleProfitSourceMapItem,
} from '@/api/style_profit'
import {
  STYLE_PROFIT_ALLOCATION_STATUS_LABELS,
  STYLE_PROFIT_PARITY_SCOPE_LABELS,
  STYLE_PROFIT_READONLY_GUARD_REASON_MAP,
  STYLE_PROFIT_REMAINING_GAP_LABEL,
  STYLE_PROFIT_REVENUE_STATUS_LABELS,
  STYLE_PROFIT_SNAPSHOT_STATUS_LABELS,
  STYLE_PROFIT_SNAPSHOT_READONLY_GUARDED_ACTIONS,
  STYLE_PROFIT_SNAPSHOT_READONLY_GUARD_MESSAGE,
  STYLE_PROFIT_SNAPSHOT_READONLY_METRIC_FIELDS,
  STYLE_PROFIT_SNAPSHOT_READONLY_REMAINING_GAP,
  STYLE_PROFIT_SNAPSHOT_READONLY_ROUTE_LABELS,
  STYLE_PROFIT_SNAPSHOT_READONLY_WRITE_BOUNDARY,
  STYLE_PROFIT_SOURCE_STATUS_LABELS,
  STYLE_PROFIT_SOURCE_TYPE_LABELS,
  STYLE_PROFIT_WRITE_BOUNDARY_LABEL,
  type StyleProfitSnapshotReadonlyGuardedAction,
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

type GuardTone = StyleProfitReadonlyTagType

export interface StyleProfitSnapshotReadonlyMetric {
  key: string
  label: string
  value: string
}

export interface StyleProfitSnapshotReadonlyItem {
  key: string
  title: string
  scopeLabel: string
  statusLabel: string
  statusTone: GuardTone
  sourceStatusLabel: string
  blockedReason: string
  note: string
}

export interface StyleProfitSnapshotReadonlySectionSummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: StyleProfitSnapshotReadonlyMetric[]
  items: StyleProfitSnapshotReadonlyItem[]
  guardedActions: Array<StyleProfitSnapshotReadonlyGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  parityLabel: string
  focusStateLabel: string
  sourceStatusLabel: string
  queryStateLabel: string
  itemStatusLabel: string
  itemStatusTone: GuardTone
  snapshotSummary: string
  blockedReasonSummary: string
  guardMessage: string
  remainingGap: string
  writeBoundary: string
}

interface UseStyleProfitSnapshotReadonlySectionOptions {
  mode: 'list' | 'detail'
  rows?: Ref<StyleProfitSnapshotListItem[]>
  snapshot?: Ref<StyleProfitSnapshotResult | null>
  details?: Ref<StyleProfitDetailItem[]>
  sourceMaps?: Ref<StyleProfitSourceMapItem[]>
  canRead: MaybeRef<boolean>
  currentPath: MaybeRef<string>
  parity: MaybeRef<string>
  focus: MaybeRef<string>
  queryStateLabel: MaybeRef<string>
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

const resolveRouteLabel = (currentPath: string): string => {
  if (currentPath.includes('mode=readonly-source')) {
    return STYLE_PROFIT_SNAPSHOT_READONLY_ROUTE_LABELS.focusRoute
  }
  if (currentPath.includes('tab=snapshot-readonly')) {
    return STYLE_PROFIT_SNAPSHOT_READONLY_ROUTE_LABELS.parityRoute
  }
  return STYLE_PROFIT_SNAPSHOT_READONLY_ROUTE_LABELS.defaultRoute
}

const resolveFocusStateLabel = (focus: string): string => (
  focus === 'source-map' ? 'source-map focus' : 'snapshot-summary focus'
)

const resolveParityLabel = (parity: string): string => (
  parity === 'style-profit' ? 'style-profit parity' : 'style-profit parity'
)

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

const buildSnapshotStatus = (
  canRead: boolean,
  unresolvedCount: number,
  snapshotCount: number,
  sourceMapCount: number,
): { label: string; tone: GuardTone } => {
  if (!canRead) {
    return { label: '无款式利润查看权限，仅保留只读核对', tone: 'danger' }
  }
  if (snapshotCount === 0) {
    return { label: '待加载利润快照样本', tone: 'warning' }
  }
  if (unresolvedCount > 0) {
    return { label: '来源映射待复核', tone: 'warning' }
  }
  if (sourceMapCount > 0) {
    return { label: 'source-map 只读样本已就绪', tone: 'success' }
  }
  return { label: '利润快照只读样本已就绪', tone: 'success' }
}

const resolvePrimaryRow = (rows: StyleProfitSnapshotListItem[]): StyleProfitSnapshotListItem | null => {
  if (rows.length === 0) {
    return null
  }
  return rows[0]
}

const resolvePrimarySourceMap = (sourceMaps: StyleProfitSourceMapItem[]): StyleProfitSourceMapItem | null => {
  if (sourceMaps.length === 0) {
    return null
  }
  return sourceMaps[0]
}

export const useStyleProfitSnapshotReadonlySection = ({
  mode,
  rows,
  snapshot,
  details,
  sourceMaps,
  canRead,
  currentPath,
  parity,
  focus,
  queryStateLabel,
}: UseStyleProfitSnapshotReadonlySectionOptions): {
  styleProfitSnapshotReadonlySummary: ComputedRef<StyleProfitSnapshotReadonlySectionSummary>
} => {
  const styleProfitSnapshotReadonlySummary = computed<StyleProfitSnapshotReadonlySectionSummary>(() => {
    const normalizedPath = String(unref(currentPath) || '').trim()
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedFocus = String(unref(focus) || '').trim().toLowerCase()
    const normalizedQueryState = String(unref(queryStateLabel) || '').trim() || 'company=ALL; item_code=ALL'
    const canReadValue = Boolean(unref(canRead))
    const currentRows = rows?.value || []
    const currentSnapshot = snapshot?.value || null
    const currentDetails = details?.value || []
    const currentSourceMaps = sourceMaps?.value || []
    const routeLabel = resolveRouteLabel(normalizedPath)
    const focusStateLabel = resolveFocusStateLabel(normalizedFocus)
    const parityLabel = resolveParityLabel(normalizedParity)
    const listPrimaryRow = resolvePrimaryRow(currentRows)
    const detailPrimaryMap = resolvePrimarySourceMap(currentSourceMaps)
    const snapshotCount = mode === 'list' ? currentRows.length : currentSnapshot ? 1 : 0
    const sourceMapCount = mode === 'detail'
      ? currentSourceMaps.length
      : currentRows.filter((row) => row.allocation_status === 'mapped').length
    const unresolvedCount = mode === 'detail'
      ? currentSnapshot?.unresolved_count ?? currentDetails.filter((detailItem) => detailItem.is_unresolved).length
      : currentRows.reduce((sum, row) => sum + Number(row.unresolved_count || 0), 0)
    const status = buildSnapshotStatus(canReadValue, unresolvedCount, snapshotCount, sourceMapCount)
    const sourceStatusLabel = mode === 'detail'
      ? `source-map=${detailPrimaryMap?.mapping_status || 'pending'} / snapshot=${currentSnapshot?.snapshot_status || 'pending'}`
      : `source-map=${sourceMapCount > 0 ? 'mapped' : 'pending'} / snapshot=${listPrimaryRow?.snapshot_status || 'pending'}`

    const tags = [
      {
        key: 'source',
        label: `${STYLE_PROFIT_SNAPSHOT_READONLY_ROUTE_LABELS.sourceLabel}: ${routeLabel}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: STYLE_PROFIT_SNAPSHOT_READONLY_ROUTE_LABELS.readonlyMode,
        type: 'success' as GuardTone,
      },
      {
        key: 'parity',
        label: parityLabel,
        type: 'info' as GuardTone,
      },
      {
        key: 'focus',
        label: focusStateLabel,
        type: normalizedFocus === 'source-map' ? ('warning' as GuardTone) : ('info' as GuardTone),
      },
      {
        key: 'status',
        label: status.label,
        type: status.tone,
      },
    ]

    const items: StyleProfitSnapshotReadonlyItem[] = mode === 'detail'
      ? [
          {
            key: 'detail-primary',
            title: `快照详情 / ${currentSnapshot?.snapshot_no || 'pending-snapshot'}`,
            scopeLabel: `style=${currentSnapshot?.item_code || 'pending-item'}; sales_order=${currentSnapshot?.sales_order || 'pending-order'}`,
            statusLabel: status.label,
            statusTone: status.tone,
            sourceStatusLabel,
            blockedReason: 'blocked_reason=当前仅开放 snapshot-readonly 与 source-map 核对，不允许真实利润重算、提交、导出或 ERPNext 执行。',
            note: `request_hash=${currentSnapshot?.request_hash || 'pending-hash'}; detail_count=${currentDetails.length}; query_state=${normalizedQueryState}`,
          },
          {
            key: 'detail-source-map',
            title: `来源追溯 / ${detailPrimaryMap?.source_name || 'pending-source-map'}`,
            scopeLabel: `source=${detailPrimaryMap?.source_system || 'pending-source'}; doctype=${detailPrimaryMap?.source_doctype || 'pending-doctype'}`,
            statusLabel: unresolvedCount > 0 ? 'source-map 待复核' : 'source-map 已就绪',
            statusTone: unresolvedCount > 0 ? ('warning' as GuardTone) : ('success' as GuardTone),
            sourceStatusLabel,
            blockedReason: 'blocked_reason=当前仅开放 source-map 只读核对，不允许真实利润重算、导出、ERPNext、outbox、worker 或生产写入。',
            note: `source_ref=${detailPrimaryMap?.source_name || 'pending-source-map'}; include_in_profit=${detailPrimaryMap?.include_in_profit ? 'yes' : 'no'}; query_state=${normalizedQueryState}`,
          },
        ]
      : [
          {
            key: 'list-primary',
            title: `快照样本 / ${listPrimaryRow?.snapshot_no || 'pending-snapshot'}`,
            scopeLabel: `style=${listPrimaryRow?.item_code || 'pending-item'}; company=${listPrimaryRow?.company || 'pending-company'}`,
            statusLabel: status.label,
            statusTone: status.tone,
            sourceStatusLabel,
            blockedReason: 'blocked_reason=当前仅开放 snapshot-readonly 与 style-profit parity 核对，不允许真实利润重算、提交、导出或 ERPNext 执行。',
            note: `sales_order=${listPrimaryRow?.sales_order || 'pending-order'}; revenue_status=${listPrimaryRow?.revenue_status || 'pending-mode'}; query_state=${normalizedQueryState}`,
          },
          {
            key: 'list-source-map',
            title: `来源映射 / ${listPrimaryRow?.allocation_status || 'pending-allocation'}`,
            scopeLabel: `snapshot_status=${listPrimaryRow?.snapshot_status || 'pending'}; formula=${listPrimaryRow?.formula_version || 'pending-formula'}`,
            statusLabel: unresolvedCount > 0 ? 'source-map 待复核' : 'source-map 已映射',
            statusTone: unresolvedCount > 0 ? ('warning' as GuardTone) : ('success' as GuardTone),
            sourceStatusLabel,
            blockedReason: 'blocked_reason=当前仅开放 source-map 只读核对，不允许真实利润重算、导出、ERPNext、outbox、worker 或生产写入。',
            note: `unresolved_count=${unresolvedCount}; page_scope=${routeLabel}; query_state=${normalizedQueryState}`,
          },
        ]

    const metrics = STYLE_PROFIT_SNAPSHOT_READONLY_METRIC_FIELDS.map((field) => {
      switch (field.key) {
        case 'snapshotCount':
          return { key: field.key, label: field.label, value: String(snapshotCount) }
        case 'sourceMapCount':
          return { key: field.key, label: field.label, value: String(sourceMapCount) }
        case 'unresolvedCount':
          return { key: field.key, label: field.label, value: String(unresolvedCount) }
        case 'guardedActionCount':
          return { key: field.key, label: field.label, value: String(STYLE_PROFIT_SNAPSHOT_READONLY_GUARDED_ACTIONS.length) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const snapshotSummary = mode === 'detail'
      ? (currentSnapshot
        ? `当前展示快照 ${currentSnapshot.snapshot_no} 的只读来源映射，样本款式 ${currentSnapshot.item_code}。`
        : '当前查询范围未命中快照详情样本，保留 source-map 只读占位摘要。')
      : (listPrimaryRow
        ? `当前展示快照 ${listPrimaryRow.snapshot_no} 的只读汇总，样本款式 ${listPrimaryRow.item_code}。`
        : '当前查询范围未命中快照列表样本，保留 snapshot-readonly 只读占位摘要。')

    const blockedReasonSummary = !canReadValue
      ? '当前账号无款式利润查看权限；页面仅保留 snapshot-readonly 只读核对摘要。'
      : '当前仅开放 style-profit parity 与 source-map 只读核对；真实利润重算、导出、提交、ERPNext、outbox、worker 与生产写入保持关闭。'

    return {
      tags,
      metrics,
      items,
      guardedActions: STYLE_PROFIT_SNAPSHOT_READONLY_GUARDED_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: routeLabel,
      readonlyModeLabel: STYLE_PROFIT_SNAPSHOT_READONLY_ROUTE_LABELS.readonlyMode,
      parityLabel,
      focusStateLabel,
      sourceStatusLabel,
      queryStateLabel: normalizedQueryState,
      itemStatusLabel: status.label,
      itemStatusTone: status.tone,
      snapshotSummary,
      blockedReasonSummary,
      guardMessage: STYLE_PROFIT_SNAPSHOT_READONLY_GUARD_MESSAGE,
      remainingGap: STYLE_PROFIT_SNAPSHOT_READONLY_REMAINING_GAP,
      writeBoundary: STYLE_PROFIT_SNAPSHOT_READONLY_WRITE_BOUNDARY,
    }
  })

  return {
    styleProfitSnapshotReadonlySummary,
  }
}
