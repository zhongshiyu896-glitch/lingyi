import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  SalesInventoryAggregationItem,
  StockLedgerItem,
  StockSummaryItem,
} from '@/api/sales_inventory'
import {
  SALES_INVENTORY_WAREHOUSE_BALANCE_DISABLED_ACTIONS,
  SALES_INVENTORY_WAREHOUSE_BALANCE_FOCUS_LABEL,
  SALES_INVENTORY_WAREHOUSE_BALANCE_PARITY_LABEL,
  SALES_INVENTORY_WAREHOUSE_BALANCE_READONLY_GUARD_REASON,
  SALES_INVENTORY_WAREHOUSE_BALANCE_REMAINING_GAP,
  SALES_INVENTORY_WAREHOUSE_BALANCE_STATE_LABELS,
  SALES_INVENTORY_WAREHOUSE_BALANCE_STATE_TAGS,
  SALES_INVENTORY_WAREHOUSE_BALANCE_SUMMARY_FIELDS,
  SALES_INVENTORY_WAREHOUSE_BALANCE_WRITE_BOUNDARY,
  type SalesInventoryWarehouseBalanceReadonlyState,
  type SalesInventoryWarehouseBalanceReadonlyTagType,
  type SalesInventoryWarehouseBalanceSummaryFieldKey,
} from '@/views/sales_inventory/constants/salesInventoryWarehouseBalanceFields'

const FALLBACK_TEXT = '-'

export interface SalesInventoryWarehouseBalanceReadonlyCard {
  key: SalesInventoryWarehouseBalanceSummaryFieldKey
  label: string
  value: string
}

export interface SalesInventoryWarehouseBalanceReadonlyAction {
  key: string
  label: string
  reason: string
}

export interface SalesInventoryWarehouseBalanceReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface SalesInventoryWarehouseBalanceReadonlyViewSummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesInventoryWarehouseBalanceReadonlyTagType
  focusLabel: string
  focusTone: SalesInventoryWarehouseBalanceReadonlyTagType
  stateLabel: string
  stateTone: SalesInventoryWarehouseBalanceReadonlyTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesInventoryWarehouseBalanceReadonlyTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: SalesInventoryWarehouseBalanceReadonlyCard[]
  disabledActions: SalesInventoryWarehouseBalanceReadonlyAction[]
  items: SalesInventoryWarehouseBalanceReadonlyItem[]
}

interface UseSalesInventoryWarehouseBalanceReadonlyOptions {
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

const stockBalanceStatusLabel = (balance: unknown): '缺货' | '低库存' | '正常' => {
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
  if (!canRead) return '当前账号无库存台账读取权限，warehouse-balance 仅保留只读壳层。'
  if (requiredItemCode) return '缺少款号，当前仅保留 warehouse-balance query state 与只读守卫用于验证。'
  if (!hasReadableSource) {
    return '当前筛选未命中 warehouse-balance 条目，仍保留 material-stock parity 与 warehouse-source focus 只读壳层。'
  }
  if (warningCount > 0) {
    return '当前仓库余额存在低库存或缺货预警，仅开放 warehouse-balance readonly 与 blocked reason 核对。'
  }
  return '当前仅开放 warehouse-balance / material-stock 只读核对，不开放真实 delivery、export、stock-write、ERPNext、outbox、worker 或 production write。'
}

const buildSummaryItems = (
  rows: StockSummaryItem[],
  blockedReason: string,
): SalesInventoryWarehouseBalanceReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `结存 ${formatAmount(row.balance_qty)} / ${stockBalanceStatusLabel(row.balance_qty)}`,
    sourceLabel: `${row.latest_posting_date || FALLBACK_TEXT} ${row.latest_posting_time || ''}`.trim(),
    blockedReason,
  }))

const buildLedgerItems = (
  rows: StockLedgerItem[],
  blockedReason: string,
): SalesInventoryWarehouseBalanceReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `Δ${formatAmount(row.actual_qty)} / 结存 ${formatAmount(row.qty_after_transaction)} / ${stockBalanceStatusLabel(row.qty_after_transaction)}`,
    sourceLabel: `${row.voucher_type || FALLBACK_TEXT} / ${row.voucher_no || FALLBACK_TEXT}`,
    blockedReason,
  }))

const buildAggregationItems = (
  rows: SalesInventoryAggregationItem[],
  blockedReason: string,
): SalesInventoryWarehouseBalanceReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `实际 ${formatAmount(row.actual_qty)} / 安全 ${formatAmount(row.safety_stock)}`,
    sourceLabel: `补货 ${formatAmount(row.reorder_level)} / 占用 ${formatAmount(row.ordered_qty)}`,
    blockedReason,
  }))

export const useSalesInventoryWarehouseBalanceReadonly = ({
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
}: UseSalesInventoryWarehouseBalanceReadonlyOptions): {
  salesInventoryWarehouseBalanceReadonlySummary: ComputedRef<SalesInventoryWarehouseBalanceReadonlyViewSummary>
} => {
  const salesInventoryWarehouseBalanceReadonlySummary =
    computed<SalesInventoryWarehouseBalanceReadonlyViewSummary>(() => {
      const ledgerRows = unref(rows) || []
      const currentSummaryRows = unref(summaryRows) || []
      const currentAggregationRows = unref(aggregationRows) || []
      const tabValue = normalizeText(unref(tab)) || 'warehouse-balance-readonly'
      const parityValue = normalizeText(unref(parity)) || 'material-stock'
      const focusValue = normalizeText(unref(focus)) || 'warehouse-source'
      const itemCodeValue = normalizeText(unref(itemCode))
      const warehouseValue = normalizeText(unref(warehouse))
      const readable = Boolean(unref(canRead))
      const itemCodeRequired = Boolean(unref(requiredItemCode))
      const errorMessage = normalizeText(unref(lastError))

      const warehouseSet = new Set<string>()
      currentSummaryRows.forEach((row) => {
        if (row.warehouse) warehouseSet.add(row.warehouse)
      })
      ledgerRows.forEach((row) => {
        if (row.warehouse) warehouseSet.add(row.warehouse)
      })
      currentAggregationRows.forEach((row) => {
        if (row.warehouse) warehouseSet.add(row.warehouse)
      })

      const summaryBalanceTotal = currentSummaryRows.reduce((sum, row) => sum + toNumber(row.balance_qty), 0)
      const lowBalanceCount =
        currentSummaryRows.filter((row) => stockBalanceStatusLabel(row.balance_qty) !== '正常').length ||
        ledgerRows.filter((row) => stockBalanceStatusLabel(row.qty_after_transaction) !== '正常').length
      const aggregationWarningCount = currentAggregationRows.filter(
        (row) => row.is_below_safety || row.is_below_reorder,
      ).length
      const warningCount = lowBalanceCount + aggregationWarningCount
      const hasReadableSource =
        currentSummaryRows.length > 0 || ledgerRows.length > 0 || currentAggregationRows.length > 0

      const blockedReason = buildBlockedReason(
        readable,
        itemCodeRequired,
        hasReadableSource,
        warningCount,
        errorMessage,
      )

      let items = buildSummaryItems(currentSummaryRows, blockedReason)
      if (items.length === 0) items = buildLedgerItems(ledgerRows, blockedReason)
      if (items.length === 0) items = buildAggregationItems(currentAggregationRows, blockedReason)
      if (items.length === 0) {
        items = [
          {
            subjectLabel: `${itemCodeValue || '待输入款号'} / ${warehouseValue || 'warehouse-balance'}`,
            statusLabel: itemCodeRequired ? '待输入款号 / 余额待回读' : 'warehouse-balance 待回读',
            sourceLabel: `${parityValue || 'material-stock'} / ${focusValue || 'warehouse-source'}`,
            blockedReason,
          },
        ]
      }

      let state: SalesInventoryWarehouseBalanceReadonlyState = 'ready-readonly'
      if (!readable) {
        state = 'permission-guarded'
      } else if (itemCodeRequired) {
        state = 'query-guarded'
      } else if (errorMessage || warningCount > 0) {
        state = 'source-warning'
      }

      const cards: SalesInventoryWarehouseBalanceReadonlyCard[] =
        SALES_INVENTORY_WAREHOUSE_BALANCE_SUMMARY_FIELDS.map((field) => {
          const values: Record<SalesInventoryWarehouseBalanceSummaryFieldKey, string> = {
            warehouseCoverageLabel: `${warehouseSet.size} 仓 / ${currentSummaryRows.length} 条余额`,
            balanceCoverageLabel: `${formatAmount(summaryBalanceTotal)} / ${ledgerRows.length} 条流水`,
            warningCountLabel: `${warningCount} 条预警`,
            guardedActionCountLabel: String(SALES_INVENTORY_WAREHOUSE_BALANCE_DISABLED_ACTIONS.length),
          }
          return {
            key: field.key,
            label: field.label,
            value: values[field.key],
          }
        })

      let sourceStatusLabel = 'warehouse-source pending'
      let sourceStatusTone: SalesInventoryWarehouseBalanceReadonlyTagType = 'info'
      if (!readable) {
        sourceStatusLabel = 'warehouse-source permission guarded'
        sourceStatusTone = 'danger'
      } else if (itemCodeRequired) {
        sourceStatusLabel = 'warehouse-source query waiting for item_code'
        sourceStatusTone = 'warning'
      } else if (errorMessage) {
        sourceStatusLabel = 'warehouse-source readback blocked'
        sourceStatusTone = 'danger'
      } else if (!hasReadableSource) {
        sourceStatusLabel = 'warehouse-source guarded / no rows'
        sourceStatusTone = 'warning'
      } else {
        sourceStatusLabel = `warehouse-source readback ready / ${items.length} rows`
        sourceStatusTone = warningCount > 0 ? 'warning' : 'success'
      }

      return {
        queryStateLabel: `tab=${tabValue}; parity=${parityValue}; focus=${focusValue}; item_code=${itemCodeValue || FALLBACK_TEXT}; warehouse=${warehouseValue || FALLBACK_TEXT}`,
        parityLabel:
          parityValue === 'material-stock'
            ? SALES_INVENTORY_WAREHOUSE_BALANCE_PARITY_LABEL
            : `${parityValue || 'material-stock'} / fallback`,
        parityTone: parityValue === 'material-stock' ? 'success' : 'warning',
        focusLabel:
          focusValue === 'warehouse-source'
            ? SALES_INVENTORY_WAREHOUSE_BALANCE_FOCUS_LABEL
            : `${focusValue || 'warehouse-source'} / fallback`,
        focusTone: focusValue === 'warehouse-source' ? 'success' : 'warning',
        stateLabel: SALES_INVENTORY_WAREHOUSE_BALANCE_STATE_LABELS[state],
        stateTone: SALES_INVENTORY_WAREHOUSE_BALANCE_STATE_TAGS[state],
        sourceStatusLabel,
        sourceStatusTone,
        itemStatusLabel: `${items.length} 条条目 / 仓库 ${warehouseSet.size} / 预警 ${warningCount}`,
        blockedReason,
        readonlyGuardReason: SALES_INVENTORY_WAREHOUSE_BALANCE_READONLY_GUARD_REASON,
        remainingGap: SALES_INVENTORY_WAREHOUSE_BALANCE_REMAINING_GAP,
        writeBoundary: SALES_INVENTORY_WAREHOUSE_BALANCE_WRITE_BOUNDARY,
        cards,
        disabledActions: SALES_INVENTORY_WAREHOUSE_BALANCE_DISABLED_ACTIONS.map((action) => ({
          key: action.key,
          label: action.label,
          reason: action.reason,
        })),
        items,
      }
    })

  return {
    salesInventoryWarehouseBalanceReadonlySummary,
  }
}
