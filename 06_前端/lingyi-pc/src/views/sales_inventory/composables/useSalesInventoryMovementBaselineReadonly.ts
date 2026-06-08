import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  SalesInventoryAggregationItem,
  StockLedgerItem,
  StockSummaryItem,
} from '@/api/sales_inventory'
import {
  SALES_INVENTORY_MOVEMENT_BASELINE_DISABLED_ACTIONS,
  SALES_INVENTORY_MOVEMENT_BASELINE_FOCUS_LABEL,
  SALES_INVENTORY_MOVEMENT_BASELINE_PARITY_LABEL,
  SALES_INVENTORY_MOVEMENT_BASELINE_READONLY_GUARD_REASON,
  SALES_INVENTORY_MOVEMENT_BASELINE_REMAINING_GAP,
  SALES_INVENTORY_MOVEMENT_BASELINE_STATE_LABELS,
  SALES_INVENTORY_MOVEMENT_BASELINE_STATE_TAGS,
  SALES_INVENTORY_MOVEMENT_BASELINE_SUMMARY_FIELDS,
  SALES_INVENTORY_MOVEMENT_BASELINE_WRITE_BOUNDARY,
  type SalesInventoryMovementBaselineReadonlyState,
  type SalesInventoryMovementBaselineReadonlyTagType,
  type SalesInventoryMovementBaselineSummaryFieldKey,
} from '@/views/sales_inventory/constants/salesInventoryMovementBaselineFields'

const FALLBACK_TEXT = '-'

export interface SalesInventoryMovementBaselineReadonlyCard {
  key: SalesInventoryMovementBaselineSummaryFieldKey
  label: string
  value: string
}

export interface SalesInventoryMovementBaselineReadonlyAction {
  key: string
  label: string
  reason: string
}

export interface SalesInventoryMovementBaselineReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface SalesInventoryMovementBaselineReadonlyViewSummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesInventoryMovementBaselineReadonlyTagType
  focusLabel: string
  focusTone: SalesInventoryMovementBaselineReadonlyTagType
  stateLabel: string
  stateTone: SalesInventoryMovementBaselineReadonlyTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesInventoryMovementBaselineReadonlyTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: SalesInventoryMovementBaselineReadonlyCard[]
  disabledActions: SalesInventoryMovementBaselineReadonlyAction[]
  items: SalesInventoryMovementBaselineReadonlyItem[]
}

interface UseSalesInventoryMovementBaselineReadonlyOptions {
  rows: MaybeRef<StockLedgerItem[]>
  summaryRows: MaybeRef<StockSummaryItem[]>
  aggregationRows: MaybeRef<SalesInventoryAggregationItem[]>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  itemCode?: MaybeRef<string | null | undefined>
  warehouse?: MaybeRef<string | null | undefined>
  canRead: MaybeRef<boolean>
  requiredItemCode: MaybeRef<boolean>
  lastError?: MaybeRef<string | null | undefined>
}

const normalizeText = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumber = (value: unknown): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const formatAmount = (value: unknown): string => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : FALLBACK_TEXT
}

const stockLedgerStatusLabel = (balance: unknown): '缺货' | '低库存' | '正常' => {
  const numeric = toNumber(balance)
  if (numeric <= 0) return '缺货'
  if (numeric < 20) return '低库存'
  return '正常'
}

const buildBlockedReason = (
  canRead: boolean,
  requiredItemCode: boolean,
  hasReadableSource: boolean,
  warningCount: number,
  errorMessage: string,
): string => {
  if (errorMessage) return errorMessage
  if (!canRead) return '当前账号无库存台账读取权限，movement-baseline 仅保留只读壳层。'
  if (requiredItemCode) return '缺少款号，当前仅保留 movement-baseline query state 与只读守卫用于验证。'
  if (!hasReadableSource) {
    return '当前筛选未命中 movement-baseline 条目，仍保留 material-stock parity 与 movement-source focus 只读壳层。'
  }
  if (warningCount > 0) {
    return '当前库存流水存在低库存或缺货预警，仅开放 movement-baseline readonly 与 blocked reason 核对。'
  }
  return '当前仅开放 movement-baseline / material-stock 只读核对，不开放真实 delivery、export、stock-write、ERPNext、outbox、worker 或 production write。'
}

const buildLedgerItems = (
  rows: StockLedgerItem[],
  blockedReason: string,
): SalesInventoryMovementBaselineReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `${stockLedgerStatusLabel(row.qty_after_transaction)} / Δ${formatAmount(row.actual_qty)} / 结存 ${formatAmount(row.qty_after_transaction)}`,
    sourceLabel: `${row.voucher_type || FALLBACK_TEXT} / ${row.voucher_no || FALLBACK_TEXT}`,
    blockedReason,
  }))

const buildSummaryItems = (
  rows: StockSummaryItem[],
  blockedReason: string,
): SalesInventoryMovementBaselineReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `结存 ${formatAmount(row.balance_qty)} / ${stockLedgerStatusLabel(row.balance_qty)}`,
    sourceLabel: `${row.latest_posting_date || FALLBACK_TEXT} ${row.latest_posting_time || ''}`.trim(),
    blockedReason,
  }))

const buildAggregationItems = (
  rows: SalesInventoryAggregationItem[],
  blockedReason: string,
): SalesInventoryMovementBaselineReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `实际 ${formatAmount(row.actual_qty)} / 占用 ${formatAmount(row.ordered_qty)}`,
    sourceLabel: `安全 ${formatAmount(row.safety_stock)} / 补货 ${formatAmount(row.reorder_level)}`,
    blockedReason,
  }))

export const useSalesInventoryMovementBaselineReadonly = ({
  rows,
  summaryRows,
  aggregationRows,
  tab,
  parity,
  focus,
  itemCode,
  warehouse,
  canRead,
  requiredItemCode,
  lastError,
}: UseSalesInventoryMovementBaselineReadonlyOptions): {
  salesInventoryMovementBaselineReadonlySummary: ComputedRef<SalesInventoryMovementBaselineReadonlyViewSummary>
} => {
  const salesInventoryMovementBaselineReadonlySummary =
    computed<SalesInventoryMovementBaselineReadonlyViewSummary>(() => {
      const ledgerRows = unref(rows) || []
      const currentSummaryRows = unref(summaryRows) || []
      const currentAggregationRows = unref(aggregationRows) || []
      const tabValue = normalizeText(unref(tab)) || 'movement-baseline-readonly'
      const parityValue = normalizeText(unref(parity)) || 'material-stock'
      const focusValue = normalizeText(unref(focus)) || 'movement-source'
      const itemCodeValue = normalizeText(unref(itemCode))
      const warehouseValue = normalizeText(unref(warehouse))
      const readable = Boolean(unref(canRead))
      const itemCodeRequired = Boolean(unref(requiredItemCode))
      const errorMessage = normalizeText(unref(lastError))

      const warehouseSet = new Set<string>()
      ledgerRows.forEach((row) => {
        if (row.warehouse) warehouseSet.add(row.warehouse)
      })
      currentSummaryRows.forEach((row) => {
        if (row.warehouse) warehouseSet.add(row.warehouse)
      })
      currentAggregationRows.forEach((row) => {
        if (row.warehouse) warehouseSet.add(row.warehouse)
      })

      const movementTotal = ledgerRows.reduce((sum, row) => sum + toNumber(row.actual_qty), 0)
      const warningCount =
        ledgerRows.filter((row) => stockLedgerStatusLabel(row.qty_after_transaction) !== '正常').length +
        currentSummaryRows.filter((row) => stockLedgerStatusLabel(row.balance_qty) !== '正常').length +
        currentAggregationRows.filter((row) => row.is_below_safety || row.is_below_reorder).length
      const hasReadableSource =
        ledgerRows.length > 0 || currentSummaryRows.length > 0 || currentAggregationRows.length > 0

      const blockedReason = buildBlockedReason(
        readable,
        itemCodeRequired,
        hasReadableSource,
        warningCount,
        errorMessage,
      )

      let items = buildLedgerItems(ledgerRows, blockedReason)
      if (items.length === 0) items = buildSummaryItems(currentSummaryRows, blockedReason)
      if (items.length === 0) items = buildAggregationItems(currentAggregationRows, blockedReason)
      if (items.length === 0) {
        items = [
          {
            subjectLabel: `${itemCodeValue || '待输入款号'} / ${warehouseValue || 'movement-source'}`,
            statusLabel: itemCodeRequired ? '待输入款号 / 流水待回读' : 'movement-baseline 待回读',
            sourceLabel: `${parityValue || 'material-stock'} / ${focusValue || 'movement-source'}`,
            blockedReason,
          },
        ]
      }

      let state: SalesInventoryMovementBaselineReadonlyState = 'ready-readonly'
      if (!readable) {
        state = 'permission-guarded'
      } else if (itemCodeRequired) {
        state = 'query-guarded'
      } else if (errorMessage || warningCount > 0) {
        state = 'source-warning'
      }

      const cards: SalesInventoryMovementBaselineReadonlyCard[] =
        SALES_INVENTORY_MOVEMENT_BASELINE_SUMMARY_FIELDS.map((field) => {
          const values: Record<SalesInventoryMovementBaselineSummaryFieldKey, string> = {
            movementCoverageLabel: `${ledgerRows.length} 条流水 / ${currentSummaryRows.length} 条摘要`,
            deltaCoverageLabel: `${formatAmount(movementTotal)} / ${currentAggregationRows.length} 条聚合`,
            warehouseCoverageLabel: `${warehouseSet.size} 仓 / 预警 ${warningCount}`,
            guardedActionCountLabel: String(SALES_INVENTORY_MOVEMENT_BASELINE_DISABLED_ACTIONS.length),
          }
          return {
            key: field.key,
            label: field.label,
            value: values[field.key],
          }
        })

      let sourceStatusLabel = 'movement-source pending'
      let sourceStatusTone: SalesInventoryMovementBaselineReadonlyTagType = 'info'
      if (!readable) {
        sourceStatusLabel = 'movement-source permission guarded'
        sourceStatusTone = 'danger'
      } else if (itemCodeRequired) {
        sourceStatusLabel = 'movement-source query waiting for item_code'
        sourceStatusTone = 'warning'
      } else if (errorMessage) {
        sourceStatusLabel = 'movement-source readback blocked'
        sourceStatusTone = 'danger'
      } else if (!hasReadableSource) {
        sourceStatusLabel = 'movement-source guarded / no rows'
        sourceStatusTone = 'warning'
      } else {
        sourceStatusLabel = `movement-source readback ready / ${items.length} rows`
        sourceStatusTone = warningCount > 0 ? 'warning' : 'success'
      }

      return {
        queryStateLabel: `${tabValue} | parity=${parityValue} | focus=${focusValue} | item_code=${itemCodeValue || FALLBACK_TEXT}`,
        parityLabel: SALES_INVENTORY_MOVEMENT_BASELINE_PARITY_LABEL,
        parityTone: parityValue === 'material-stock' ? 'success' : 'warning',
        focusLabel: SALES_INVENTORY_MOVEMENT_BASELINE_FOCUS_LABEL,
        focusTone: focusValue === 'movement-source' ? 'warning' : 'info',
        stateLabel: SALES_INVENTORY_MOVEMENT_BASELINE_STATE_LABELS[state],
        stateTone: SALES_INVENTORY_MOVEMENT_BASELINE_STATE_TAGS[state],
        sourceStatusLabel,
        sourceStatusTone,
        itemStatusLabel: `${items.length} 条 movement 状态 / 仓库 ${warehouseSet.size} / 预警 ${warningCount}`,
        blockedReason,
        readonlyGuardReason: SALES_INVENTORY_MOVEMENT_BASELINE_READONLY_GUARD_REASON,
        remainingGap: SALES_INVENTORY_MOVEMENT_BASELINE_REMAINING_GAP,
        writeBoundary: SALES_INVENTORY_MOVEMENT_BASELINE_WRITE_BOUNDARY,
        cards,
        disabledActions: SALES_INVENTORY_MOVEMENT_BASELINE_DISABLED_ACTIONS.map((action) => ({
          key: action.key,
          label: action.label,
          reason: action.reason,
        })),
        items,
      }
    })

  return {
    salesInventoryMovementBaselineReadonlySummary,
  }
}
