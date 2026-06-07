import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  SalesInventoryAggregationItem,
  StockLedgerItem,
  StockSummaryItem,
} from '@/api/sales_inventory'
import {
  SALES_INVENTORY_STOCK_SOURCE_GUARD_DISABLED_ACTIONS,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_FOCUS_LABEL,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_PARITY_LABEL,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_READONLY_GUARD_REASON,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_REMAINING_GAP,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_LABELS,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_TAGS,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_SUMMARY_FIELDS,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_WRITE_BOUNDARY,
  type SalesInventoryStockSourceGuardState,
  type SalesInventoryStockSourceGuardSummaryFieldKey,
  type SalesInventoryStockSourceGuardTagType,
} from '@/views/sales_inventory/constants/salesInventoryStockSourceGuardFields'

const FALLBACK_TEXT = '-'

export interface SalesInventoryStockSourceGuardReadonlyCard {
  key: SalesInventoryStockSourceGuardSummaryFieldKey
  label: string
  value: string
}

export interface SalesInventoryStockSourceGuardReadonlyAction {
  label: string
  reason: string
}

export interface SalesInventoryStockSourceGuardReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface SalesInventoryStockSourceGuardReadonlyViewSummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesInventoryStockSourceGuardTagType
  focusLabel: string
  focusTone: SalesInventoryStockSourceGuardTagType
  stateLabel: string
  stateTone: SalesInventoryStockSourceGuardTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesInventoryStockSourceGuardTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: SalesInventoryStockSourceGuardReadonlyCard[]
  disabledActions: SalesInventoryStockSourceGuardReadonlyAction[]
  items: SalesInventoryStockSourceGuardReadonlyItem[]
}

interface UseSalesInventoryStockSourceGuardReadonlyOptions {
  rows: MaybeRef<StockLedgerItem[]>
  summaryRows: MaybeRef<StockSummaryItem[]>
  aggregationRows: MaybeRef<SalesInventoryAggregationItem[]>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  itemCode?: MaybeRef<string | null | undefined>
  canRead: MaybeRef<boolean>
  requiredItemCode: MaybeRef<boolean>
  lastError?: MaybeRef<string | null | undefined>
  droppedCount?: MaybeRef<number | null | undefined>
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

const stockLedgerStatusLabel = (row: StockLedgerItem): '缺货' | '低库存' | '正常' => {
  const balanceQty = toNumber(row.qty_after_transaction)
  if (balanceQty <= 0) return '缺货'
  if (balanceQty < 20) return '低库存'
  return '正常'
}

const buildFallbackReason = (canRead: boolean, requiredItemCode: boolean, errorMessage: string): string => {
  if (errorMessage) return errorMessage
  if (!canRead) return '当前账号无库存台账读取权限，source guard 仅保留只读壳层。'
  if (requiredItemCode) return '缺少款号，当前只保留 stock-source guard/query state 用于只读验证。'
  return '真实库存来源链路冻结，仅开放 stock-source/source status 只读核对。'
}

const buildLedgerItems = (
  rows: StockLedgerItem[],
  blockedReason: string,
): SalesInventoryStockSourceGuardReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `${stockLedgerStatusLabel(row)} / Δ${formatAmount(row.actual_qty)} / 结存 ${formatAmount(row.qty_after_transaction)}`,
    sourceLabel: `${row.voucher_type || FALLBACK_TEXT} / ${row.voucher_no || FALLBACK_TEXT}`,
    blockedReason,
  }))

const buildSummaryItems = (
  rows: StockSummaryItem[],
  blockedReason: string,
): SalesInventoryStockSourceGuardReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `结存 ${formatAmount(row.balance_qty)}`,
    sourceLabel: `${row.latest_posting_date || FALLBACK_TEXT} ${row.latest_posting_time || ''}`.trim(),
    blockedReason,
  }))

const buildAggregationItems = (
  rows: SalesInventoryAggregationItem[],
  blockedReason: string,
): SalesInventoryStockSourceGuardReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `实际 ${formatAmount(row.actual_qty)} / 占用 ${formatAmount(row.ordered_qty)}`,
    sourceLabel: `安全 ${formatAmount(row.safety_stock)} / 补货 ${formatAmount(row.reorder_level)}`,
    blockedReason,
  }))

export const useSalesInventoryStockSourceGuardReadonly = ({
  rows,
  summaryRows,
  aggregationRows,
  tab,
  parity,
  focus,
  itemCode,
  canRead,
  requiredItemCode,
  lastError,
  droppedCount,
}: UseSalesInventoryStockSourceGuardReadonlyOptions): {
  stockSourceGuardReadonlySummary: ComputedRef<SalesInventoryStockSourceGuardReadonlyViewSummary>
} => {
  const stockSourceGuardReadonlySummary = computed<SalesInventoryStockSourceGuardReadonlyViewSummary>(() => {
    const ledgerRows = unref(rows) || []
    const sourceSummaryRows = unref(summaryRows) || []
    const sourceAggregationRows = unref(aggregationRows) || []
    const tabValue = normalizeText(unref(tab)) || 'source-guard-readonly'
    const parityValue = normalizeText(unref(parity)) || 'material-stock'
    const focusValue = normalizeText(unref(focus)) || 'stock-source'
    const normalizedItemCode = normalizeText(unref(itemCode))
    const readable = Boolean(unref(canRead))
    const itemCodeRequired = Boolean(unref(requiredItemCode))
    const errorMessage = normalizeText(unref(lastError))
    const dropped = Number(unref(droppedCount) || 0)

    const warehouseSet = new Set<string>()
    ledgerRows.forEach((row) => {
      if (row.warehouse) warehouseSet.add(row.warehouse)
    })
    sourceSummaryRows.forEach((row) => {
      if (row.warehouse) warehouseSet.add(row.warehouse)
    })
    sourceAggregationRows.forEach((row) => {
      if (row.warehouse) warehouseSet.add(row.warehouse)
    })

    const warningCount =
      ledgerRows.filter((row) => stockLedgerStatusLabel(row) !== '正常').length +
      sourceAggregationRows.filter((row) => row.is_below_safety || row.is_below_reorder).length

    const blockedReason = buildFallbackReason(readable, itemCodeRequired, errorMessage)
    const hasReadableSource =
      ledgerRows.length > 0 || sourceSummaryRows.length > 0 || sourceAggregationRows.length > 0

    let items = buildLedgerItems(ledgerRows, blockedReason)
    if (items.length === 0) items = buildSummaryItems(sourceSummaryRows, blockedReason)
    if (items.length === 0) items = buildAggregationItems(sourceAggregationRows, blockedReason)
    if (items.length === 0) {
      items = [
        {
          subjectLabel: `${normalizedItemCode || '待输入款号'} / stock-source`,
          statusLabel: itemCodeRequired ? '待输入款号' : '来源待回读',
          sourceLabel: `${parityValue || 'material-stock'} / ${focusValue || 'stock-source'}`,
          blockedReason,
        },
      ]
    }

    let state: SalesInventoryStockSourceGuardState = 'ready-readonly'
    if (!readable) {
      state = 'permission-guarded'
    } else if (itemCodeRequired) {
      state = 'query-guarded'
    } else if (errorMessage || warningCount > 0) {
      state = 'source-warning'
    }

    const cards: SalesInventoryStockSourceGuardReadonlyCard[] =
      SALES_INVENTORY_STOCK_SOURCE_GUARD_SUMMARY_FIELDS.map((field) => {
        const values: Record<SalesInventoryStockSourceGuardSummaryFieldKey, string> = {
          sourceCoverageLabel: `${ledgerRows.length} 条流水 / ${sourceSummaryRows.length} 条摘要`,
          statusCoverageLabel: `${items.length} 条来源状态 / ${hasReadableSource ? 'ready' : 'pending'}`,
          warehouseCountLabel: String(warehouseSet.size),
          warningCountLabel: String(warningCount),
          droppedCountLabel: String(dropped),
        }
        return {
          key: field.key,
          label: field.label,
          value: values[field.key],
        }
      })

    let sourceStatusLabel = 'stock-source pending'
    let sourceStatusTone: SalesInventoryStockSourceGuardTagType = 'info'
    if (!readable) {
      sourceStatusLabel = 'stock-source permission guarded'
      sourceStatusTone = 'danger'
    } else if (itemCodeRequired) {
      sourceStatusLabel = 'stock-source query waiting for item_code'
      sourceStatusTone = 'warning'
    } else if (errorMessage) {
      sourceStatusLabel = 'stock-source readback blocked'
      sourceStatusTone = 'danger'
    } else if (hasReadableSource) {
      sourceStatusLabel = `stock-source readback ready / ${items.length} rows`
      sourceStatusTone = warningCount > 0 ? 'warning' : 'success'
    }

    return {
      queryStateLabel: `${tabValue} | parity=${parityValue} | focus=${focusValue} | item_code=${normalizedItemCode || FALLBACK_TEXT}`,
      parityLabel: SALES_INVENTORY_STOCK_SOURCE_GUARD_PARITY_LABEL,
      parityTone: parityValue === 'material-stock' ? 'success' : 'warning',
      focusLabel: SALES_INVENTORY_STOCK_SOURCE_GUARD_FOCUS_LABEL,
      focusTone: focusValue === 'stock-source' ? 'warning' : 'info',
      stateLabel: SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_LABELS[state],
      stateTone: SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_TAGS[state],
      sourceStatusLabel,
      sourceStatusTone,
      itemStatusLabel: `${items.length} 条来源状态 / 仓库 ${warehouseSet.size} / 预警 ${warningCount}`,
      blockedReason,
      readonlyGuardReason: SALES_INVENTORY_STOCK_SOURCE_GUARD_READONLY_GUARD_REASON,
      remainingGap: SALES_INVENTORY_STOCK_SOURCE_GUARD_REMAINING_GAP,
      writeBoundary: SALES_INVENTORY_STOCK_SOURCE_GUARD_WRITE_BOUNDARY,
      cards,
      disabledActions: SALES_INVENTORY_STOCK_SOURCE_GUARD_DISABLED_ACTIONS.map((action) => ({
        label: action.label,
        reason: action.reason,
      })),
      items,
    }
  })

  return {
    stockSourceGuardReadonlySummary,
  }
}
