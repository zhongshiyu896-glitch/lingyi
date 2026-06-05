import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { WarehouseBatchItem, WarehouseStockSummaryItem } from '@/api/warehouse'
import {
  WAREHOUSE_BALANCE_BATCH_READONLY_GUARD_LABEL,
  WAREHOUSE_BALANCE_BATCH_REMAINING_GAP,
  WAREHOUSE_BALANCE_BATCH_WRITE_BOUNDARY,
  WAREHOUSE_BALANCE_READONLY_STATE_LABELS,
  WAREHOUSE_BALANCE_READONLY_STATE_TAGS,
  WAREHOUSE_BATCH_READONLY_STATE_LABELS,
  WAREHOUSE_BATCH_READONLY_STATE_TAGS,
  WAREHOUSE_PARITY_SCOPE_LABELS,
  type WarehouseBalanceBatchReadonlyTagType,
  type WarehouseBalanceReadonlyState,
  type WarehouseBatchReadonlyState,
} from '@/views/warehouse/constants/warehouseBalanceBatchFields'

const FALLBACK_TEXT = '-'

export interface WarehouseBalanceBatchReadonlySummary {
  sourceLabel: string
  parityScopeLabel: string
  parityLabel: string
  parityTone: WarehouseBalanceBatchReadonlyTagType
  balanceStatusLabel: string
  balanceStatusTone: WarehouseBalanceBatchReadonlyTagType
  batchStatusLabel: string
  batchStatusTone: WarehouseBalanceBatchReadonlyTagType
  readonlyGuardLabel: string
  readonlyGuardTone: WarehouseBalanceBatchReadonlyTagType
  stockQtyTotalLabel: string
  projectedQtyTotalLabel: string
  warningSkuCountLabel: string
  batchCountLabel: string
  batchQtyTotalLabel: string
  disabledBatchCountLabel: string
  sourceGapPrompt: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  retainedCand014: boolean
  retainedCand032: boolean
}

interface UseWarehouseBalanceBatchReadonlyOptions {
  summaryRows: MaybeRef<WarehouseStockSummaryItem[]>
  batchRows: MaybeRef<WarehouseBatchItem[]>
  parity: MaybeRef<string>
  canRead: MaybeRef<boolean>
}

const formatAmount = (value: number): string => {
  if (!Number.isFinite(value)) return FALLBACK_TEXT
  return value.toFixed(2)
}

const sumNumeric = (values: Array<string | number | null | undefined>): number =>
  values.reduce<number>((sum, value) => sum + Number(value ?? 0), 0)

const resolveBalanceState = (
  rows: WarehouseStockSummaryItem[],
  canRead: boolean,
): WarehouseBalanceReadonlyState => {
  if (!canRead) return 'guarded'
  if (rows.length === 0) return 'fallback'
  if (rows.some((row) => row.threshold_missing || row.is_below_reorder || row.is_below_safety)) return 'warning'
  return 'healthy'
}

const resolveBatchState = (rows: WarehouseBatchItem[], canRead: boolean): WarehouseBatchReadonlyState => {
  if (!canRead) return 'guarded'
  if (rows.length === 0) return 'fallback'
  if (rows.some((row) => row.disabled)) return 'warning'
  return 'healthy'
}

const resolveParityLabel = (parity: string): string => {
  if (parity === 'foundation-warehouse') return 'foundation-warehouse parity'
  if (parity === 'product-stock') return 'product-stock parity'
  return 'warehouse readonly'
}

const resolveParityTone = (parity: string): WarehouseBalanceBatchReadonlyTagType => {
  if (parity === 'foundation-warehouse') return 'warning'
  if (parity === 'product-stock') return 'info'
  return 'success'
}

const resolveSourceGapPrompt = (
  parity: string,
  balanceState: WarehouseBalanceReadonlyState,
  batchState: WarehouseBatchReadonlyState,
): string => {
  if (balanceState === 'guarded' || batchState === 'guarded') {
    return '当前账号仅允许仓库读侧回退，余额与批次影响只提供 guarded readonly 视图。'
  }
  if (parity === 'foundation-warehouse') {
    return 'foundation-warehouse parity 仅回读仓库余额与批次影响，不开放真实仓库写入。'
  }
  if (parity === 'product-stock') {
    return 'product-stock parity 仅回读成品库存余额与批次影响，不开放真实库存联动。'
  }
  if (balanceState === 'fallback' || batchState === 'fallback') {
    return '当前余额或批次影响存在只读回退，需结合真实仓库回读继续确认。'
  }
  if (balanceState === 'warning' || batchState === 'warning') {
    return '当前存在阈值/批次预警，提示仅用于只读确认，不触发真实库存动作。'
  }
  return '仓库余额与批次影响已回读，但真实库存动作与导出仍保持关闭。'
}

export const useWarehouseBalanceBatchReadonly = ({
  summaryRows,
  batchRows,
  parity,
  canRead,
}: UseWarehouseBalanceBatchReadonlyOptions): {
  warehouseBalanceBatchReadonlySummary: ComputedRef<WarehouseBalanceBatchReadonlySummary>
} => {
  const warehouseBalanceBatchReadonlySummary = computed<WarehouseBalanceBatchReadonlySummary>(() => {
    const currentSummaryRows = unref(summaryRows)
    const currentBatchRows = unref(batchRows)
    const parityValue = String(unref(parity) || '').trim().toLowerCase()
    const readable = Boolean(unref(canRead))
    const balanceState = resolveBalanceState(currentSummaryRows, readable)
    const batchState = resolveBatchState(currentBatchRows, readable)
    const totalQty = sumNumeric(currentSummaryRows.map((row) => row.actual_qty))
    const projectedQty = sumNumeric(currentSummaryRows.map((row) => row.projected_qty))
    const warningSkuCount = currentSummaryRows.filter(
      (row) => row.threshold_missing || row.is_below_reorder || row.is_below_safety,
    ).length
    const batchQty = sumNumeric(currentBatchRows.map((row) => row.qty))
    const disabledBatchCount = currentBatchRows.filter((row) => row.disabled).length

    return {
      sourceLabel: readable ? 'warehouse summary / batch readonly' : 'warehouse readonly fallback',
      parityScopeLabel: WAREHOUSE_PARITY_SCOPE_LABELS[parityValue] || WAREHOUSE_PARITY_SCOPE_LABELS.default,
      parityLabel: resolveParityLabel(parityValue),
      parityTone: resolveParityTone(parityValue),
      balanceStatusLabel: WAREHOUSE_BALANCE_READONLY_STATE_LABELS[balanceState],
      balanceStatusTone: WAREHOUSE_BALANCE_READONLY_STATE_TAGS[balanceState],
      batchStatusLabel: WAREHOUSE_BATCH_READONLY_STATE_LABELS[batchState],
      batchStatusTone: WAREHOUSE_BATCH_READONLY_STATE_TAGS[batchState],
      readonlyGuardLabel: 'warehouse readonly guard',
      readonlyGuardTone: readable ? 'warning' : 'danger',
      stockQtyTotalLabel: formatAmount(totalQty),
      projectedQtyTotalLabel: formatAmount(projectedQty),
      warningSkuCountLabel: String(warningSkuCount),
      batchCountLabel: String(currentBatchRows.length),
      batchQtyTotalLabel: formatAmount(batchQty),
      disabledBatchCountLabel: String(disabledBatchCount),
      sourceGapPrompt: resolveSourceGapPrompt(parityValue, balanceState, batchState),
      readonlyGuardReason: WAREHOUSE_BALANCE_BATCH_READONLY_GUARD_LABEL,
      remainingGap: WAREHOUSE_BALANCE_BATCH_REMAINING_GAP,
      writeBoundary: WAREHOUSE_BALANCE_BATCH_WRITE_BOUNDARY,
      retainedCand014: true,
      retainedCand032: true,
    }
  })

  return {
    warehouseBalanceBatchReadonlySummary,
  }
}
