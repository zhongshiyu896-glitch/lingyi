import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { SalesInventoryReferenceRow, SalesInventoryReferenceTab } from '@/api/sales_inventory_references'
import {
  SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_DISABLED_ACTIONS,
  SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_FOCUS_LABEL,
  SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_PARITY_LABEL,
  SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_READONLY_GUARD_REASON,
  SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_REMAINING_GAP,
  SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_STATE_LABELS,
  SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_STATE_TAGS,
  SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_SUMMARY_FIELDS,
  SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_WRITE_BOUNDARY,
  type SalesInventoryReferencePartnerScopeReadonlyState,
  type SalesInventoryReferencePartnerScopeReadonlyTagType,
  type SalesInventoryReferencePartnerScopeSummaryFieldKey,
} from '@/views/sales_inventory/constants/salesInventoryReferencePartnerScopeFields'

export interface SalesInventoryReferencePartnerScopeReadonlyCard {
  key: SalesInventoryReferencePartnerScopeSummaryFieldKey
  label: string
  value: string
}

export interface SalesInventoryReferencePartnerScopeReadonlyAction {
  key: string
  label: string
  reason: string
}

export interface SalesInventoryReferencePartnerScopeReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface SalesInventoryReferencePartnerScopeReadonlyViewSummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesInventoryReferencePartnerScopeReadonlyTagType
  focusLabel: string
  focusTone: SalesInventoryReferencePartnerScopeReadonlyTagType
  stateLabel: string
  stateTone: SalesInventoryReferencePartnerScopeReadonlyTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesInventoryReferencePartnerScopeReadonlyTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: SalesInventoryReferencePartnerScopeReadonlyCard[]
  disabledActions: SalesInventoryReferencePartnerScopeReadonlyAction[]
  items: SalesInventoryReferencePartnerScopeReadonlyItem[]
}

interface UseSalesInventoryReferencePartnerScopeReadonlyOptions {
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
  if (!canRead) return '当前账号无引用档案读取权限，partner-scope 仅保留只读壳层。'
  if (!hasRows) return '当前筛选未命中 partner-scope 条目，仍保留 foundation-reference parity 与 partner-source focus 只读壳层。'
  if (missingCount > 0) {
    return tabValue === 'suppliers'
      ? '供应商 partner-source 当前缺少 ERPNext 直连来源，只保留 foundation-reference parity 与本地只读守卫。'
      : '当前 partner-source 存在缺失，仅保留 partner-scope readonly 与 blocked reason 核对。'
  }
  if (usingFallbackValue) {
    return '客户 partner-source 当前已切换到本地只读回退视图，不开放真实客户/供应商维护、导入、导出或库存写入。'
  }
  return '当前仅开放 partner-scope / foundation-reference 只读核对，不开放客户/供应商真实维护、导入、导出、库存写入或跨模块执行。'
}

const buildItems = (
  rows: SalesInventoryReferenceRow[],
  blockedReason: string,
): SalesInventoryReferencePartnerScopeReadonlyItem[] => {
  if (rows.length === 0) {
    return [
      {
        subjectLabel: 'partner-scope / default',
        statusLabel: 'guarded / waiting',
        sourceLabel: 'partner-source / parity mirror',
        blockedReason,
      },
    ]
  }

  return rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.referenceType === 'customers' ? '客户' : '供应商'} / ${row.code || FALLBACK_TEXT}`,
    statusLabel: `${row.status || FALLBACK_TEXT} / ${row.name || FALLBACK_TEXT}`,
    sourceLabel: `${row.parityScope || FALLBACK_TEXT} / ${row.readonlySourceTag || FALLBACK_TEXT}`,
    blockedReason: row.missingSourcePrompt || blockedReason,
  }))
}

export const useSalesInventoryReferencePartnerScopeReadonly = ({
  rows,
  activeTab,
  currentPath,
  tab,
  parity,
  focus,
  filterStateLabel,
  usingFallback,
  canRead,
}: UseSalesInventoryReferencePartnerScopeReadonlyOptions): {
  salesInventoryReferencePartnerScopeReadonlySummary: ComputedRef<SalesInventoryReferencePartnerScopeReadonlyViewSummary>
} => {
  const salesInventoryReferencePartnerScopeReadonlySummary =
    computed<SalesInventoryReferencePartnerScopeReadonlyViewSummary>(() => {
      const currentRows = unref(rows) || []
      const activeTabValue = unref(activeTab) || 'customers'
      const currentPathValue = normalizeText(unref(currentPath)) || '/sales-inventory/references'
      const tabValue = normalizeText(unref(tab)) || 'partner-scope-readonly'
      const parityValue = normalizeText(unref(parity)) || 'foundation-reference'
      const focusValue = normalizeText(unref(focus)) || 'partner-source'
      const filterLabel = normalizeText(unref(filterStateLabel)) || 'keyword=-; status=all; source=all'
      const usingFallbackValue = Boolean(unref(usingFallback))
      const readable = Boolean(unref(canRead))
      const hasRows = currentRows.length > 0
      const activeCount = currentRows.filter((row) => row.status === 'active').length
      const issueCount = currentRows.filter((row) => row.sourceValidationState !== 'verified').length
      const missingCount = currentRows.filter((row) => row.sourceValidationState === 'missing').length
      const customerCount = currentRows.filter((row) => row.referenceType === 'customers').length
      const supplierCount = currentRows.filter((row) => row.referenceType === 'suppliers').length

      const blockedReason = buildBlockedReason(
        readable,
        hasRows,
        usingFallbackValue,
        missingCount,
        activeTabValue,
      )
      const items = buildItems(currentRows, blockedReason)

      let state: SalesInventoryReferencePartnerScopeReadonlyState = 'ready-readonly'
      if (!readable) {
        state = 'permission-guarded'
      } else if (!hasRows) {
        state = 'query-guarded'
      } else if (issueCount > 0) {
        state = 'source-warning'
      }

      let sourceStatusLabel = 'partner-source pending'
      let sourceStatusTone: SalesInventoryReferencePartnerScopeReadonlyTagType = 'info'
      if (!readable) {
        sourceStatusLabel = 'partner-source permission guarded'
        sourceStatusTone = 'danger'
      } else if (!hasRows) {
        sourceStatusLabel = 'partner-source guarded / no rows'
        sourceStatusTone = 'warning'
      } else if (missingCount > 0) {
        sourceStatusLabel = `partner-source missing / ${missingCount} rows`
        sourceStatusTone = 'danger'
      } else if (issueCount > 0) {
        sourceStatusLabel = `partner-source fallback / ${issueCount} rows`
        sourceStatusTone = 'warning'
      } else {
        sourceStatusLabel = `partner-source readback ready / ${currentRows.length} rows`
        sourceStatusTone = 'success'
      }

      const cards: SalesInventoryReferencePartnerScopeReadonlyCard[] =
        SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_SUMMARY_FIELDS.map((field) => {
          const values: Record<SalesInventoryReferencePartnerScopeSummaryFieldKey, string> = {
            referenceCountLabel: String(currentRows.length),
            activeReferenceCountLabel: String(activeCount),
            partnerIssueCountLabel: String(issueCount),
            guardedActionCountLabel: String(SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_DISABLED_ACTIONS.length),
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
            ? SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_PARITY_LABEL
            : `${parityValue || 'foundation-reference'} / fallback`,
        parityTone: parityValue === 'foundation-reference' ? 'success' : 'warning',
        focusLabel:
          focusValue === 'partner-source'
            ? SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_FOCUS_LABEL
            : `${focusValue || 'partner-source'} / fallback`,
        focusTone: focusValue === 'partner-source' ? 'success' : 'warning',
        stateLabel: SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_STATE_LABELS[state],
        stateTone: SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_STATE_TAGS[state],
        sourceStatusLabel,
        sourceStatusTone,
        itemStatusLabel: `${currentRows.length} rows / customers ${customerCount} / suppliers ${supplierCount}`,
        blockedReason,
        readonlyGuardReason: SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_READONLY_GUARD_REASON,
        remainingGap: SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_REMAINING_GAP,
        writeBoundary: SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_WRITE_BOUNDARY,
        cards,
        disabledActions: SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_DISABLED_ACTIONS.map((action) => ({
          key: action.key,
          label: action.label,
          reason: action.reason,
        })),
        items,
      }
    })

  return {
    salesInventoryReferencePartnerScopeReadonlySummary,
  }
}
