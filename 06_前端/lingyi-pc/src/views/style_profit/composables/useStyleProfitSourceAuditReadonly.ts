import { computed, unref, type ComputedRef, type MaybeRef, type Ref } from 'vue'
import type {
  StyleProfitDetailItem,
  StyleProfitSnapshotListItem,
  StyleProfitSnapshotResult,
  StyleProfitSourceMapItem,
} from '@/api/style_profit'
import {
  STYLE_PROFIT_ALLOCATION_STATUS_LABELS,
  STYLE_PROFIT_REVENUE_STATUS_LABELS,
  STYLE_PROFIT_SNAPSHOT_STATUS_LABELS,
  STYLE_PROFIT_SOURCE_STATUS_LABELS,
  STYLE_PROFIT_SOURCE_TYPE_LABELS,
} from '@/views/style_profit/constants/styleProfitReadonlyFields'
import {
  STYLE_PROFIT_SOURCE_AUDIT_BLOCKED_REASON,
  STYLE_PROFIT_SOURCE_AUDIT_GUARDED_ACTIONS,
  STYLE_PROFIT_SOURCE_AUDIT_READONLY_GUARD_MESSAGE,
  STYLE_PROFIT_SOURCE_AUDIT_REMAINING_GAP,
  STYLE_PROFIT_SOURCE_AUDIT_WRITE_BOUNDARY,
  type StyleProfitSourceAuditGuardedAction,
  type StyleProfitSourceAuditMetricKey,
  type StyleProfitSourceAuditTagTone,
} from '@/views/style_profit/constants/styleProfitSourceAuditFields'

type MetricValues = Record<StyleProfitSourceAuditMetricKey, string>
type GuardTone = StyleProfitSourceAuditTagTone

export interface StyleProfitSourceAuditReadonlyRow {
  key: string
  title: string
  scopeLabel: string
  statusLabel: string
  statusTone: GuardTone
  sourceStatusLabel: string
  blockedReason: string
  note: string
}

export interface StyleProfitSourceAuditReadonlySummary {
  subtitle: string
  queryStateLabel: string
  parityLabel: string
  focusLabel: string
  revenueModeLabel: string
  snapshotStatusLabel: string
  allocationStatusLabel: string
  sourceTypeLabel: string
  sourceStatusLabel: string
  blockedReasonSummary: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  metricValues: MetricValues
  itemRows: StyleProfitSourceAuditReadonlyRow[]
  guardedActions: Array<StyleProfitSourceAuditGuardedAction & { disabled: true }>
}

interface UseStyleProfitSourceAuditReadonlyOptions {
  mode: 'list' | 'detail'
  rows?: Ref<StyleProfitSnapshotListItem[]>
  snapshot?: Ref<StyleProfitSnapshotResult | null>
  details?: Ref<StyleProfitDetailItem[]>
  sourceMaps?: Ref<StyleProfitSourceMapItem[]>
  parity: MaybeRef<string>
  focus: MaybeRef<string>
  queryStateLabel: MaybeRef<string>
  canRead: MaybeRef<boolean>
}

const resolveLabel = (value: string | null | undefined, labels: Record<string, string>, fallback: string): string => {
  if (!value) return fallback
  return labels[value] || value
}

const joinUniqueLabels = (values: Array<string | null | undefined>, labels: Record<string, string>, fallback: string): string => {
  const normalized = values
    .map((value) => resolveLabel(value || '', labels, ''))
    .filter((value) => value && value !== '-')
  if (!normalized.length) return fallback
  return [...new Set(normalized)].join(' / ')
}

const resolveToneByStatus = (value: string | null | undefined): GuardTone => {
  if (value === 'complete' || value === 'mapped' || value === 'submitted') return 'success'
  if (value === 'incomplete' || value === 'partial' || value === 'draft') return 'warning'
  if (value === 'unresolved') return 'danger'
  return 'info'
}

const resolveFocusLabel = (focus: string, mode: 'list' | 'detail'): string => {
  if (focus === 'source-audit') return 'source-audit focus'
  return mode === 'detail' ? 'detail summary focus' : 'list summary focus'
}

const resolveParityLabel = (parity: string): string => {
  const normalized = parity.trim()
  if (!normalized || normalized === 'style-profit') return 'style-profit parity'
  return `${normalized} parity`
}

const buildListRows = (rows: StyleProfitSnapshotListItem[], queryStateLabel: string): StyleProfitSourceAuditReadonlyRow[] => {
  const items = rows.slice(0, 2)
  if (items.length === 0) {
    return [
      {
        key: 'pending-list-row',
        title: 'pending-style-profit-snapshot',
        scopeLabel: 'style=pending-item; company=pending-company',
        statusLabel: '待加载只读样本',
        statusTone: 'warning',
        sourceStatusLabel: '来源状态待加载',
        blockedReason: STYLE_PROFIT_SOURCE_AUDIT_BLOCKED_REASON,
        note: `query_state=${queryStateLabel}`,
      },
    ]
  }
  return items.map((row) => ({
    key: `list-${row.id}`,
    title: row.snapshot_no || `snapshot-${row.id}`,
    scopeLabel: `style=${row.item_code || '-'}; company=${row.company || '-'}`,
    statusLabel: resolveLabel(row.snapshot_status, STYLE_PROFIT_SNAPSHOT_STATUS_LABELS, '待复核'),
    statusTone: resolveToneByStatus(row.snapshot_status),
    sourceStatusLabel: `${resolveLabel(row.allocation_status, STYLE_PROFIT_ALLOCATION_STATUS_LABELS, '待补齐来源')} / unresolved=${row.unresolved_count || 0}`,
    blockedReason: STYLE_PROFIT_SOURCE_AUDIT_BLOCKED_REASON,
    note: `source_ref=${row.sales_order || '-'}; revenue=${resolveLabel(row.revenue_status, STYLE_PROFIT_REVENUE_STATUS_LABELS, '-')}; query_state=${queryStateLabel}`,
  }))
}

const buildDetailRows = (
  snapshot: StyleProfitSnapshotResult | null,
  details: StyleProfitDetailItem[],
  sourceMaps: StyleProfitSourceMapItem[],
  queryStateLabel: string,
): StyleProfitSourceAuditReadonlyRow[] => {
  const sourceItems = sourceMaps.slice(0, 2)
  if (sourceItems.length > 0) {
    return sourceItems.map((item) => ({
      key: `source-${item.id}`,
      title: item.source_name || `source-${item.id}`,
      scopeLabel: `style=${item.style_item_code || '-'}; system=${item.source_system || '-'}`,
      statusLabel: resolveLabel(item.source_status || item.mapping_status, STYLE_PROFIT_SOURCE_STATUS_LABELS, '待复核'),
      statusTone: resolveToneByStatus(item.source_status || item.mapping_status),
      sourceStatusLabel: `${resolveLabel(item.mapping_status, STYLE_PROFIT_ALLOCATION_STATUS_LABELS, '待补齐来源')} / include_in_profit=${item.include_in_profit ? 'yes' : 'no'}`,
      blockedReason: STYLE_PROFIT_SOURCE_AUDIT_BLOCKED_REASON,
      note: `source_line=${item.source_line_no || '-'}; source_item=${item.source_item_code || '-'}; query_state=${queryStateLabel}`,
    }))
  }

  const detailItems = details.slice(0, 2)
  if (detailItems.length > 0) {
    return detailItems.map((item) => ({
      key: `detail-${item.id}`,
      title: item.source_name || `detail-${item.id}`,
      scopeLabel: `cost_type=${item.cost_type || '-'}; source_type=${item.source_type || '-'}`,
      statusLabel: item.is_unresolved ? '待复核' : '已映射',
      statusTone: item.is_unresolved ? 'warning' : 'success',
      sourceStatusLabel: item.unresolved_reason || '来源样本已就绪',
      blockedReason: STYLE_PROFIT_SOURCE_AUDIT_BLOCKED_REASON,
      note: `formula=${item.formula_code || '-'}; item_code=${item.item_code || '-'}; query_state=${queryStateLabel}`,
    }))
  }

  return [
    {
      key: 'pending-detail-row',
      title: snapshot?.snapshot_no || 'pending-detail-snapshot',
      scopeLabel: `style=${snapshot?.item_code || 'pending-item'}; sales_order=${snapshot?.sales_order || '-'}`,
      statusLabel: resolveLabel(snapshot?.snapshot_status, STYLE_PROFIT_SNAPSHOT_STATUS_LABELS, '待复核'),
      statusTone: resolveToneByStatus(snapshot?.snapshot_status),
      sourceStatusLabel: '来源状态待加载',
      blockedReason: STYLE_PROFIT_SOURCE_AUDIT_BLOCKED_REASON,
      note: `query_state=${queryStateLabel}`,
    },
  ]
}

export const useStyleProfitSourceAuditReadonlySection = ({
  mode,
  rows,
  snapshot,
  details,
  sourceMaps,
  parity,
  focus,
  queryStateLabel,
  canRead,
}: UseStyleProfitSourceAuditReadonlyOptions): {
  styleProfitSourceAuditReadonlySummary: ComputedRef<StyleProfitSourceAuditReadonlySummary>
} => {
  const styleProfitSourceAuditReadonlySummary = computed<StyleProfitSourceAuditReadonlySummary>(() => {
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedFocus = String(unref(focus) || '').trim().toLowerCase()
    const normalizedQueryState = String(unref(queryStateLabel) || '').trim() || 'company=ALL; item_code=ALL'
    const canReadValue = Boolean(unref(canRead))
    const currentRows = rows?.value || []
    const currentSnapshot = snapshot?.value || null
    const currentDetails = details?.value || []
    const currentSourceMaps = sourceMaps?.value || []

    const snapshotCount = mode === 'detail' ? (currentSnapshot ? 1 : 0) : currentRows.length
    const sourceCount = mode === 'detail' ? currentSourceMaps.length || currentDetails.length : currentRows.length
    const unresolvedCount = mode === 'detail'
      ? currentSnapshot?.unresolved_count ?? currentDetails.filter((item) => item.is_unresolved).length
      : currentRows.reduce((sum, row) => sum + Number(row.unresolved_count || 0), 0)

    const revenueModeLabel = mode === 'detail'
      ? resolveLabel(currentSnapshot?.revenue_status, STYLE_PROFIT_REVENUE_STATUS_LABELS, '本地只读回退')
      : joinUniqueLabels(currentRows.map((row) => row.revenue_status), STYLE_PROFIT_REVENUE_STATUS_LABELS, '本地只读回退')
    const snapshotStatusLabel = mode === 'detail'
      ? resolveLabel(currentSnapshot?.snapshot_status, STYLE_PROFIT_SNAPSHOT_STATUS_LABELS, '待复核')
      : joinUniqueLabels(currentRows.map((row) => row.snapshot_status), STYLE_PROFIT_SNAPSHOT_STATUS_LABELS, '待复核')
    const allocationStatusLabel = mode === 'detail'
      ? resolveLabel(currentSnapshot?.allocation_status, STYLE_PROFIT_ALLOCATION_STATUS_LABELS, '待补齐来源')
      : joinUniqueLabels(currentRows.map((row) => row.allocation_status), STYLE_PROFIT_ALLOCATION_STATUS_LABELS, '待补齐来源')
    const sourceTypeLabel = mode === 'detail'
      ? joinUniqueLabels(
          currentSourceMaps.map((item) => item.source_system || item.source_doctype),
          STYLE_PROFIT_SOURCE_TYPE_LABELS,
          '本地只读回退',
        )
      : '利润快照汇总'
    const sourceStatusLabel = unresolvedCount > 0
      ? '待复核'
      : mode === 'detail'
        ? joinUniqueLabels(
            currentSourceMaps.map((item) => item.mapping_status || item.source_status),
            STYLE_PROFIT_SOURCE_STATUS_LABELS,
            currentSnapshot ? '已映射' : '待加载',
          )
        : snapshotCount > 0
          ? '已映射'
          : '待加载'

    return {
      subtitle: canReadValue
        ? (mode === 'detail' ? '当前仅核对 detail source-audit / provenance 只读摘要。' : '当前仅核对 list source-audit / provenance 只读摘要。')
        : '当前账号无款式利润查看权限，仅保留 source-audit 只读核对摘要。',
      queryStateLabel: normalizedQueryState,
      parityLabel: resolveParityLabel(normalizedParity),
      focusLabel: resolveFocusLabel(normalizedFocus, mode),
      revenueModeLabel,
      snapshotStatusLabel,
      allocationStatusLabel,
      sourceTypeLabel,
      sourceStatusLabel,
      blockedReasonSummary: canReadValue
        ? '当前仅开放 source-audit 与 provenance 只读核对；真实利润重算、导出、提交、source collector 写入、ERPNext、outbox、worker 与生产写入保持关闭。'
        : '当前账号无款式利润查看权限；页面仅保留 source-audit 只读核对摘要。',
      readonlyGuardReason: STYLE_PROFIT_SOURCE_AUDIT_READONLY_GUARD_MESSAGE,
      remainingGap: STYLE_PROFIT_SOURCE_AUDIT_REMAINING_GAP,
      writeBoundary: STYLE_PROFIT_SOURCE_AUDIT_WRITE_BOUNDARY,
      metricValues: {
        snapshotCount: String(snapshotCount),
        sourceCount: String(sourceCount),
        unresolvedCount: String(unresolvedCount),
        guardedActionCount: String(STYLE_PROFIT_SOURCE_AUDIT_GUARDED_ACTIONS.length),
      },
      itemRows: mode === 'detail'
        ? buildDetailRows(currentSnapshot, currentDetails, currentSourceMaps, normalizedQueryState)
        : buildListRows(currentRows, normalizedQueryState),
      guardedActions: STYLE_PROFIT_SOURCE_AUDIT_GUARDED_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
    }
  })

  return {
    styleProfitSourceAuditReadonlySummary,
  }
}
