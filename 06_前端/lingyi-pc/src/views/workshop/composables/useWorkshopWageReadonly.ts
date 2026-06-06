import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { WorkshopWageRateRow } from '@/api/workshop'
import {
  WORKSHOP_WAGE_READONLY_GUARDED_ACTIONS,
  WORKSHOP_WAGE_READONLY_GUARD_MESSAGE,
  WORKSHOP_WAGE_READONLY_METRIC_FIELDS,
  WORKSHOP_WAGE_READONLY_REMAINING_GAP,
  WORKSHOP_WAGE_READONLY_ROUTE_LABELS,
  WORKSHOP_WAGE_READONLY_WRITE_BOUNDARY,
  type WorkshopWageReadonlyGuardedAction,
  type WorkshopWageReadonlyTagType,
} from '@/views/workshop/constants/workshopWageReadonlyFields'

type GuardTone = WorkshopWageReadonlyTagType

export interface WorkshopWageReadonlyMetric {
  key: string
  label: string
  value: string
}

export interface WorkshopWageReadonlyItem {
  key: string
  title: string
  scopeLabel: string
  rateLabel: string
  statusLabel: string
  statusTone: GuardTone
  sourceStatusLabel: string
  blockedReason: string
  note: string
}

export interface WorkshopWageReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: WorkshopWageReadonlyMetric[]
  items: WorkshopWageReadonlyItem[]
  guardedActions: Array<WorkshopWageReadonlyGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  parityLabel: string
  focusStateLabel: string
  sourceStatusLabel: string
  queryStateLabel: string
  rateStatusLabel: string
  rateStatusTone: GuardTone
  wageSummary: string
  blockedReasonSummary: string
  guardMessage: string
  remainingGap: string
  writeBoundary: string
}

interface UseWorkshopWageReadonlyOptions {
  rows: MaybeRef<WorkshopWageRateRow[]>
  canRead: MaybeRef<boolean>
  currentPath: MaybeRef<string>
  parity: MaybeRef<string>
  focus: MaybeRef<string>
  filterStateLabel: MaybeRef<string>
}

const resolveRouteLabel = (currentPath: string): string => {
  if (currentPath.includes('focus=rate-source')) return WORKSHOP_WAGE_READONLY_ROUTE_LABELS.focusRoute
  if (currentPath.includes('tab=readonly-wage')) return WORKSHOP_WAGE_READONLY_ROUTE_LABELS.parityRoute
  return WORKSHOP_WAGE_READONLY_ROUTE_LABELS.defaultRoute
}

const resolveFocusStateLabel = (focus: string): string => (
  focus === 'rate-source' ? 'rate-source focus' : 'summary focus'
)

const resolveParityLabel = (parity: string): string => (
  parity === 'production-order' ? 'production-order parity' : 'production-order parity'
)

const resolveParityTone = (parity: string): GuardTone => (
  parity === 'production-order' ? 'info' : 'warning'
)

const buildStatus = (
  readable: boolean,
  totalCount: number,
  activeCount: number,
): { label: string; tone: GuardTone } => {
  if (!readable) return { label: '只读受限', tone: 'danger' }
  if (totalCount === 0) return { label: '待回读', tone: 'info' }
  if (activeCount < totalCount) return { label: '含停用档案', tone: 'warning' }
  return { label: '已回读', tone: 'success' }
}

export const useWorkshopWageReadonly = ({
  rows,
  canRead,
  currentPath,
  parity,
  focus,
  filterStateLabel,
}: UseWorkshopWageReadonlyOptions): {
  workshopWageReadonlySummary: ComputedRef<WorkshopWageReadonlySummary>
} => {
  const workshopWageReadonlySummary = computed<WorkshopWageReadonlySummary>(() => {
    const readable = Boolean(unref(canRead))
    const currentRows = unref(rows)
    const normalizedCurrentPath = String(unref(currentPath) || '').trim()
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedFocus = String(unref(focus) || '').trim().toLowerCase()
    const filterLabel = String(unref(filterStateLabel) || '').trim() || 'scope=all; item=GLOBAL; company=ALL_COMPANY'
    const activeCount = currentRows.filter((row) => row.status === 'active').length
    const globalCount = currentRows.filter((row) => row.is_global).length
    const blockedActionCount = WORKSHOP_WAGE_READONLY_GUARDED_ACTIONS.length
    const rateStatus = buildStatus(readable, currentRows.length, activeCount)
    const routeLabel = resolveRouteLabel(normalizedCurrentPath)
    const focusStateLabel = resolveFocusStateLabel(normalizedFocus)
    const sourceStatusLabel = normalizedFocus === 'rate-source' ? 'rate-source locked' : 'rate-source summary'

    const tags = [
      {
        key: 'source',
        label: `${WORKSHOP_WAGE_READONLY_ROUTE_LABELS.sourceLabel}: ${routeLabel}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: WORKSHOP_WAGE_READONLY_ROUTE_LABELS.readonlyMode,
        type: 'success' as GuardTone,
      },
      {
        key: 'parity',
        label: resolveParityLabel(normalizedParity),
        type: resolveParityTone(normalizedParity),
      },
      {
        key: 'focus',
        label: focusStateLabel,
        type: normalizedFocus === 'rate-source' ? ('warning' as GuardTone) : ('info' as GuardTone),
      },
      {
        key: 'status',
        label: rateStatus.label,
        type: rateStatus.tone,
      },
    ]

    const metrics = WORKSHOP_WAGE_READONLY_METRIC_FIELDS.map((field) => {
      switch (field.key) {
        case 'rateCount':
          return { key: field.key, label: field.label, value: String(currentRows.length) }
        case 'activeRateCount':
          return { key: field.key, label: field.label, value: String(activeCount) }
        case 'globalRateCount':
          return { key: field.key, label: field.label, value: String(globalCount) }
        case 'blockedActionCount':
          return { key: field.key, label: field.label, value: String(blockedActionCount) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const items = currentRows.length > 0
      ? currentRows.map((row) => {
        const sourceLabel = row.is_global ? 'global-rate-source' : 'item-rate-source'
        const companyLabel = row.company || 'ALL_COMPANY'
        const itemLabel = row.item_code || 'GLOBAL'
        const statusLabel = row.status || 'unknown'
        return {
          key: String(row.id),
          title: `${row.process_name} / ${companyLabel}`,
          scopeLabel: `item=${itemLabel}; source=${sourceLabel}`,
          rateLabel: `wage_rate=${row.wage_rate}; effective=${row.effective_from}~${row.effective_to || 'open'}`,
          statusLabel,
          statusTone: (statusLabel === 'active' ? 'success' : statusLabel === 'inactive' ? 'warning' : 'info') as GuardTone,
          sourceStatusLabel: sourceLabel,
          blockedReason:
            statusLabel === 'inactive'
              ? 'blocked_reason=当前档案为停用状态，仅做只读核对，不允许真实维护或复用执行。'
              : 'blocked_reason=当前仅开放工价档案只读摘要，不允许真实工价维护、导入、导出或 worker 执行。',
          note: `created_by=${row.created_by}; updated_at=${row.updated_at}; query_state=${filterLabel}`,
        }
      })
      : [{
        key: 'readonly-rate-source-placeholder',
        title: 'production-order parity / rate-source guard',
        scopeLabel: `item=GLOBAL; source=readonly-rate-source; route=${routeLabel}`,
        rateLabel: 'wage_rate=readonly-summary; effective=guarded-range',
        statusLabel: readable ? 'guarded' : 'readonly-restricted',
        statusTone: readable ? ('info' as GuardTone) : ('danger' as GuardTone),
        sourceStatusLabel,
        blockedReason:
          'blocked_reason=当前仅开放工价档案只读摘要，不开放真实工价维护、导入、导出、worker、ERPNext 或跨模块执行。',
        note: `query_state=${filterLabel}; remaining_gap=${WORKSHOP_WAGE_READONLY_REMAINING_GAP}`,
      }]

    const wageSummary = !readable
      ? '当前账号仅允许 workshop wage 读侧回退，工价档案只保留 guarded readonly 提示。'
      : currentRows.length === 0
        ? `${routeLabel} 当前未命中工价档案数据，仍保留 production-order parity、rate item/status、rate-source focus 与只读 guard 可见标记。`
        : `${routeLabel} 已回读工价档案 ${currentRows.length} 条，其中 active ${activeCount} 条、通用工价 ${globalCount} 条。`

    const blockedReasonSummary = !readable
      ? '无工价查看权限，工价档案只读摘要仅保留 guard 状态。'
      : '当前仅开放工价档案、production-order parity 与 rate-source focus 核对；新增、停用、导入、导出、worker、ERPNext 与跨模块执行保持关闭。'

    return {
      tags,
      metrics,
      items,
      guardedActions: WORKSHOP_WAGE_READONLY_GUARDED_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: routeLabel,
      readonlyModeLabel: WORKSHOP_WAGE_READONLY_ROUTE_LABELS.readonlyMode,
      parityLabel: resolveParityLabel(normalizedParity),
      focusStateLabel,
      sourceStatusLabel,
      queryStateLabel: filterLabel,
      rateStatusLabel: rateStatus.label,
      rateStatusTone: rateStatus.tone,
      wageSummary,
      blockedReasonSummary,
      guardMessage: WORKSHOP_WAGE_READONLY_GUARD_MESSAGE,
      remainingGap: WORKSHOP_WAGE_READONLY_REMAINING_GAP,
      writeBoundary: WORKSHOP_WAGE_READONLY_WRITE_BOUNDARY,
    }
  })

  return {
    workshopWageReadonlySummary,
  }
}
