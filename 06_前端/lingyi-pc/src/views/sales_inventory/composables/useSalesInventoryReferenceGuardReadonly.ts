import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { SalesInventoryReferenceRow, SalesInventoryReferenceTab } from '@/api/sales_inventory_references'
import {
  SALES_INVENTORY_REFERENCE_GUARD_DISABLED_ACTIONS,
  SALES_INVENTORY_REFERENCE_GUARD_FOCUS_LABEL,
  SALES_INVENTORY_REFERENCE_GUARD_PARITY_LABEL,
  SALES_INVENTORY_REFERENCE_GUARD_READONLY_GUARD_REASON,
  SALES_INVENTORY_REFERENCE_GUARD_REMAINING_GAP,
  SALES_INVENTORY_REFERENCE_GUARD_STATE_LABELS,
  SALES_INVENTORY_REFERENCE_GUARD_STATE_TAGS,
  SALES_INVENTORY_REFERENCE_GUARD_SUMMARY_FIELDS,
  SALES_INVENTORY_REFERENCE_GUARD_WRITE_BOUNDARY,
  type SalesInventoryReferenceGuardReadonlyState,
  type SalesInventoryReferenceGuardReadonlyTagType,
  type SalesInventoryReferenceGuardSummaryFieldKey,
} from '@/views/sales_inventory/constants/salesInventoryReferenceGuardFields'

export interface SalesInventoryReferenceGuardReadonlyCard {
  key: SalesInventoryReferenceGuardSummaryFieldKey
  label: string
  value: string
}

export interface SalesInventoryReferenceGuardReadonlyAction {
  label: string
  reason: string
}

export interface SalesInventoryReferenceGuardReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface SalesInventoryReferenceGuardReadonlyViewSummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesInventoryReferenceGuardReadonlyTagType
  focusLabel: string
  focusTone: SalesInventoryReferenceGuardReadonlyTagType
  stateLabel: string
  stateTone: SalesInventoryReferenceGuardReadonlyTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesInventoryReferenceGuardReadonlyTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: SalesInventoryReferenceGuardReadonlyCard[]
  disabledActions: SalesInventoryReferenceGuardReadonlyAction[]
  items: SalesInventoryReferenceGuardReadonlyItem[]
}

interface UseSalesInventoryReferenceGuardReadonlyOptions {
  rows: MaybeRef<SalesInventoryReferenceRow[]>
  activeTab: MaybeRef<SalesInventoryReferenceTab>
  currentPath: MaybeRef<string>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  filterStateLabel: MaybeRef<string>
  usingFallback: MaybeRef<boolean>
  canRead: MaybeRef<boolean>
}

const FALLBACK_TEXT = '-'

const normalizeText = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const buildBlockedReason = (
  canRead: boolean,
  hasRows: boolean,
  usingFallbackValue: boolean,
  missingCount: number,
  tabValue: SalesInventoryReferenceTab,
): string => {
  if (!canRead) return '当前账号无引用档案读取权限，source-guard 仅保留只读壳层。'
  if (!hasRows) return '当前筛选未命中引用档案，仍保留 foundation-source guard / reference-source focus 只读壳层。'
  if (missingCount > 0) {
    return tabValue === 'suppliers'
      ? '供应商引用当前缺少 ERPNext 直连来源，只保留 foundation-reference parity 与本地只读守卫。'
      : '当前引用来源存在缺失，仅保留 foundation-source guard 与 blocked reason 只读核对。'
  }
  if (usingFallbackValue) {
    return '客户引用当前已切换到本地只读回退视图，不开放真实客户/供应商维护、导入、导出或库存写入。'
  }
  return '当前仅开放 foundation-source / source-status 只读核对，不开放客户/供应商真实维护、导入、导出、库存写入或跨模块执行。'
}

const buildItems = (
  rows: SalesInventoryReferenceRow[],
  blockedReason: string,
): SalesInventoryReferenceGuardReadonlyItem[] => {
  if (rows.length === 0) {
    return [
      {
        subjectLabel: 'foundation-reference / default',
        statusLabel: 'guarded / waiting',
        sourceLabel: 'reference-source / parity mirror',
        blockedReason,
      },
    ]
  }

  return rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.referenceType === 'customers' ? '客户' : '供应商'} / ${row.code || FALLBACK_TEXT}`,
    statusLabel: `${row.status || FALLBACK_TEXT} / ${row.name || FALLBACK_TEXT}`,
    sourceLabel: `${row.readonlySourceTag || FALLBACK_TEXT} / ${row.parityScope || FALLBACK_TEXT}`,
    blockedReason: row.missingSourcePrompt || blockedReason,
  }))
}

export const useSalesInventoryReferenceGuardReadonly = ({
  rows,
  activeTab,
  currentPath,
  tab,
  parity,
  focus,
  filterStateLabel,
  usingFallback,
  canRead,
}: UseSalesInventoryReferenceGuardReadonlyOptions): {
  salesInventoryReferenceGuardReadonlySummary: ComputedRef<SalesInventoryReferenceGuardReadonlyViewSummary>
} => {
  const salesInventoryReferenceGuardReadonlySummary =
    computed<SalesInventoryReferenceGuardReadonlyViewSummary>(() => {
      const currentRows = unref(rows) || []
      const activeTabValue = unref(activeTab) || 'customers'
      const currentPathValue = normalizeText(unref(currentPath)) || '/sales-inventory/references'
      const tabValue = normalizeText(unref(tab)) || 'source-guard-readonly'
      const parityValue = normalizeText(unref(parity)) || 'foundation-reference'
      const focusValue = normalizeText(unref(focus)) || 'reference-source'
      const filterLabel = normalizeText(unref(filterStateLabel)) || 'keyword=-; status=all; source=all'
      const usingFallbackValue = Boolean(unref(usingFallback))
      const readable = Boolean(unref(canRead))
      const hasRows = currentRows.length > 0
      const activeCount = currentRows.filter((row) => row.status === 'active').length
      const inactiveCount = currentRows.filter((row) => row.status === 'inactive').length
      const issueCount = currentRows.filter((row) => row.sourceValidationState !== 'verified').length
      const missingCount = currentRows.filter((row) => row.sourceValidationState === 'missing').length

      const blockedReason = buildBlockedReason(
        readable,
        hasRows,
        usingFallbackValue,
        missingCount,
        activeTabValue,
      )
      const items = buildItems(currentRows, blockedReason)

      let state: SalesInventoryReferenceGuardReadonlyState = 'ready-readonly'
      if (!readable) {
        state = 'permission-guarded'
      } else if (!hasRows) {
        state = 'query-guarded'
      } else if (issueCount > 0) {
        state = 'source-warning'
      }

      let sourceStatusLabel = 'reference-source pending'
      let sourceStatusTone: SalesInventoryReferenceGuardReadonlyTagType = 'info'
      if (!readable) {
        sourceStatusLabel = 'reference-source permission guarded'
        sourceStatusTone = 'danger'
      } else if (!hasRows) {
        sourceStatusLabel = 'reference-source guarded / no rows'
        sourceStatusTone = 'warning'
      } else if (missingCount > 0) {
        sourceStatusLabel = `reference-source missing / ${issueCount} rows`
        sourceStatusTone = 'danger'
      } else if (issueCount > 0) {
        sourceStatusLabel = `reference-source fallback / ${issueCount} rows`
        sourceStatusTone = 'warning'
      } else {
        sourceStatusLabel = `reference-source readback ready / ${currentRows.length} rows`
        sourceStatusTone = 'success'
      }

      const cards: SalesInventoryReferenceGuardReadonlyCard[] =
        SALES_INVENTORY_REFERENCE_GUARD_SUMMARY_FIELDS.map((field) => {
          const values: Record<SalesInventoryReferenceGuardSummaryFieldKey, string> = {
            referenceCountLabel: String(currentRows.length),
            activeReferenceCountLabel: String(activeCount),
            sourceIssueCountLabel: String(issueCount),
            guardedActionCountLabel: String(SALES_INVENTORY_REFERENCE_GUARD_DISABLED_ACTIONS.length),
          }
          return {
            key: field.key,
            label: field.label,
            value: values[field.key],
          }
        })

      return {
        queryStateLabel: `tab=${tabValue}; active_tab=${activeTabValue}; route=${currentPathValue}; filters=${filterLabel}`,
        parityLabel:
          parityValue === 'foundation-reference'
            ? SALES_INVENTORY_REFERENCE_GUARD_PARITY_LABEL
            : `${parityValue || 'foundation-reference'} / fallback`,
        parityTone: parityValue === 'foundation-reference' ? 'success' : 'warning',
        focusLabel:
          focusValue === 'reference-source'
            ? SALES_INVENTORY_REFERENCE_GUARD_FOCUS_LABEL
            : `${focusValue || 'reference-source'} / fallback`,
        focusTone: focusValue === 'reference-source' ? 'success' : 'warning',
        stateLabel: SALES_INVENTORY_REFERENCE_GUARD_STATE_LABELS[state],
        stateTone: SALES_INVENTORY_REFERENCE_GUARD_STATE_TAGS[state],
        sourceStatusLabel,
        sourceStatusTone,
        itemStatusLabel: `${currentRows.length} rows / active ${activeCount} / inactive ${inactiveCount}`,
        blockedReason,
        readonlyGuardReason: SALES_INVENTORY_REFERENCE_GUARD_READONLY_GUARD_REASON,
        remainingGap: SALES_INVENTORY_REFERENCE_GUARD_REMAINING_GAP,
        writeBoundary: SALES_INVENTORY_REFERENCE_GUARD_WRITE_BOUNDARY,
        cards,
        disabledActions: SALES_INVENTORY_REFERENCE_GUARD_DISABLED_ACTIONS.map((action) => ({
          label: action.label,
          reason: action.reason,
        })),
        items,
      }
    })

  return {
    salesInventoryReferenceGuardReadonlySummary,
  }
}
