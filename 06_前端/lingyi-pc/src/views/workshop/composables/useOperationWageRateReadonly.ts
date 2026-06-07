import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { WorkshopWageRateRow } from '@/api/workshop'
import {
  OPERATION_WAGE_RATE_READONLY_DISABLED_ACTIONS,
  OPERATION_WAGE_RATE_READONLY_FOCUS_LABEL,
  OPERATION_WAGE_RATE_READONLY_GUARD_REASON,
  OPERATION_WAGE_RATE_READONLY_PARITY_LABEL,
  OPERATION_WAGE_RATE_READONLY_REMAINING_GAP,
  OPERATION_WAGE_RATE_READONLY_STATE_LABELS,
  OPERATION_WAGE_RATE_READONLY_STATE_TAGS,
  OPERATION_WAGE_RATE_READONLY_SUMMARY_FIELDS,
  OPERATION_WAGE_RATE_READONLY_WRITE_BOUNDARY,
  type OperationWageRateReadonlyState,
  type OperationWageRateReadonlySummaryFieldKey,
  type OperationWageRateReadonlyTagType,
} from '@/views/workshop/constants/operationWageRateReadonlyFields'

export interface OperationWageRateReadonlyCard {
  key: OperationWageRateReadonlySummaryFieldKey
  label: string
  value: string
}

export interface OperationWageRateReadonlyAction {
  label: string
  reason: string
}

export interface OperationWageRateReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface OperationWageRateReadonlyViewSummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: OperationWageRateReadonlyTagType
  focusLabel: string
  focusTone: OperationWageRateReadonlyTagType
  stateLabel: string
  stateTone: OperationWageRateReadonlyTagType
  sourceStatusLabel: string
  sourceStatusTone: OperationWageRateReadonlyTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: OperationWageRateReadonlyCard[]
  disabledActions: OperationWageRateReadonlyAction[]
  items: OperationWageRateReadonlyItem[]
}

interface UseOperationWageRateReadonlyOptions {
  rows: MaybeRef<WorkshopWageRateRow[]>
  canRead: MaybeRef<boolean>
  currentPath: MaybeRef<string>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  filterStateLabel: MaybeRef<string>
}

const normalizeText = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const buildBlockedReason = (canRead: boolean, hasRows: boolean): string => {
  if (!canRead) return '当前账号无工价档案读取权限，source-guard 仅保留只读壳层。'
  if (!hasRows) return '当前筛选未命中工价档案，仍保留 wage-rate parity / rate-source focus 只读守卫。'
  return '当前仅开放工价来源、source/item status 与只读守卫核对，不开放真实工价维护、导入、导出、worker、ERPNext 或跨模块执行。'
}

const summarizeItemStatus = (rows: WorkshopWageRateRow[]): string => {
  const activeCount = rows.filter((row) => row.status === 'active').length
  const inactiveCount = rows.filter((row) => row.status === 'inactive').length
  if (rows.length === 0) return '0 rows / guarded'
  return `${rows.length} rows / active ${activeCount} / inactive ${inactiveCount}`
}

const buildItems = (
  rows: WorkshopWageRateRow[],
  blockedReason: string,
): OperationWageRateReadonlyItem[] => {
  if (rows.length === 0) {
    return [
      {
        subjectLabel: 'wage-rate source guard / default',
        statusLabel: 'guarded / waiting',
        sourceLabel: 'rate-source / parity mirror',
        blockedReason,
      },
    ]
  }

  return rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.process_name} / ${row.company || 'ALL_COMPANY'}`,
    statusLabel: `${row.status || 'unknown'} / ${row.is_global ? 'global' : row.item_code || 'item-specific'}`,
    sourceLabel: `${row.item_code || 'GLOBAL'} / ${row.effective_from}~${row.effective_to || 'open'}`,
    blockedReason,
  }))
}

export const useOperationWageRateReadonly = ({
  rows,
  canRead,
  currentPath,
  tab,
  parity,
  focus,
  filterStateLabel,
}: UseOperationWageRateReadonlyOptions): {
  operationWageRateReadonlySummary: ComputedRef<OperationWageRateReadonlyViewSummary>
} => {
  const operationWageRateReadonlySummary = computed<OperationWageRateReadonlyViewSummary>(() => {
    const currentRows = unref(rows) || []
    const readable = Boolean(unref(canRead))
    const tabValue = normalizeText(unref(tab)) || 'source-readonly'
    const parityValue = normalizeText(unref(parity)) || 'wage-rate'
    const focusValue = normalizeText(unref(focus)) || 'rate-source'
    const currentPathValue = normalizeText(unref(currentPath)) || '/workshop/wage-rates'
    const filterLabel = normalizeText(unref(filterStateLabel)) || 'scope=all; item=GLOBAL; company=ALL_COMPANY; process=ALL_PROCESS; status=all'
    const hasRows = currentRows.length > 0
    const blockedReason = buildBlockedReason(readable, hasRows)
    const activeCount = currentRows.filter((row) => row.status === 'active').length
    const globalCount = currentRows.filter((row) => row.is_global).length
    const state: OperationWageRateReadonlyState = !readable
      ? 'permission-guarded'
      : hasRows
        ? 'ready-readonly'
        : 'query-guarded'

    const sourceStatusLabel = readable
      ? hasRows
        ? `rate-source readback ready / ${currentRows.length} rows`
        : 'rate-source guarded / no rows'
      : 'rate-source permission guarded'

    const items = buildItems(currentRows, blockedReason)
    const cards: OperationWageRateReadonlyCard[] = OPERATION_WAGE_RATE_READONLY_SUMMARY_FIELDS.map((field) => {
      const values: Record<OperationWageRateReadonlySummaryFieldKey, string> = {
        rateCountLabel: String(currentRows.length),
        activeRateCountLabel: String(activeCount),
        globalRateCountLabel: String(globalCount),
        blockedActionCountLabel: String(OPERATION_WAGE_RATE_READONLY_DISABLED_ACTIONS.length),
      }
      return {
        key: field.key,
        label: field.label,
        value: values[field.key],
      }
    })

    return {
      queryStateLabel: `tab=${tabValue}; route=${currentPathValue}; filters=${filterLabel}`,
      parityLabel: parityValue === 'wage-rate' ? OPERATION_WAGE_RATE_READONLY_PARITY_LABEL : `${parityValue} / fallback`,
      parityTone: parityValue === 'wage-rate' ? 'success' : 'warning',
      focusLabel: focusValue === 'rate-source' ? OPERATION_WAGE_RATE_READONLY_FOCUS_LABEL : `${focusValue || 'rate-source'} / fallback`,
      focusTone: focusValue === 'rate-source' ? 'success' : 'warning',
      stateLabel: OPERATION_WAGE_RATE_READONLY_STATE_LABELS[state],
      stateTone: OPERATION_WAGE_RATE_READONLY_STATE_TAGS[state],
      sourceStatusLabel,
      sourceStatusTone: readable ? (hasRows ? 'success' : 'warning') : 'danger',
      itemStatusLabel: summarizeItemStatus(currentRows),
      blockedReason,
      readonlyGuardReason: OPERATION_WAGE_RATE_READONLY_GUARD_REASON,
      remainingGap: OPERATION_WAGE_RATE_READONLY_REMAINING_GAP,
      writeBoundary: OPERATION_WAGE_RATE_READONLY_WRITE_BOUNDARY,
      cards,
      disabledActions: OPERATION_WAGE_RATE_READONLY_DISABLED_ACTIONS.map((action) => ({
        label: action.label,
        reason: action.reason,
      })),
      items,
    }
  })

  return {
    operationWageRateReadonlySummary,
  }
}
