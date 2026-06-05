import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { StockLedgerImpactReadonlySnapshot } from '@/api/sales_inventory_stock_impact'
import {
  STOCK_LEDGER_IMPACT_FIELDS,
  STOCK_LEDGER_IMPACT_READONLY_GUARD_LABEL,
  STOCK_LEDGER_IMPACT_REMAINING_GAP,
  STOCK_LEDGER_IMPACT_STATE_LABELS,
  STOCK_LEDGER_IMPACT_STATE_TAGS,
  STOCK_LEDGER_IMPACT_WRITE_BOUNDARY,
  STOCK_LEDGER_PARITY_SCOPE_LABELS,
  STOCK_LEDGER_SAFETY_STATE_LABELS,
  STOCK_LEDGER_SAFETY_STATE_TAGS,
  type StockLedgerImpactFieldKey,
  type StockLedgerImpactReadonlyState,
  type StockLedgerImpactReadonlyTagType,
} from '@/views/sales_inventory/constants/stockLedgerImpactFields'

const FALLBACK_TEXT = '-'

export interface StockLedgerImpactReadonlySummary {
  sourceLabel: string
  parityScopeLabel: string
  parityLabel: string
  parityTone: StockLedgerImpactReadonlyTagType
  impactStatusLabel: string
  impactStatusTone: StockLedgerImpactReadonlyTagType
  safetyStatusLabel: string
  safetyStatusTone: StockLedgerImpactReadonlyTagType
  readonlyGuardLabel: string
  readonlyGuardTone: StockLedgerImpactReadonlyTagType
  summaryBalanceQtyLabel: string
  actualQtyTotalLabel: string
  orderedQtyTotalLabel: string
  indentedQtyTotalLabel: string
  warehouseCountLabel: string
  belowSafetyCountLabel: string
  relationSummary: string
  sourceGapPrompt: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  retainedCand014: boolean
  retainedCand032: boolean
}

interface UseStockLedgerImpactReadonlyOptions {
  snapshot: MaybeRef<StockLedgerImpactReadonlySnapshot | null>
  parity: MaybeRef<string>
  canRead: MaybeRef<boolean>
}

const formatAmount = (value: number): string => {
  if (!Number.isFinite(value)) return FALLBACK_TEXT
  return value.toFixed(2)
}

const sumNumeric = (values: Array<string | number | null | undefined>): number =>
  values.reduce<number>((sum, value) => sum + Number(value ?? 0), 0)

const resolveParityLabel = (parity: string): string => {
  if (parity === 'material-stock') return 'material-stock parity'
  return 'stock-ledger readonly'
}

const resolveParityTone = (parity: string): StockLedgerImpactReadonlyTagType => {
  if (parity === 'material-stock') return 'warning'
  return 'info'
}

const resolveImpactState = (
  snapshot: StockLedgerImpactReadonlySnapshot | null,
  canRead: boolean,
): StockLedgerImpactReadonlyState => {
  if (!canRead) return 'guarded'
  if (!snapshot || (snapshot.summaryRows.length === 0 && snapshot.aggregationRows.length === 0)) return 'fallback'
  if (snapshot.belowSafetyCount > 0) return 'warning'
  return 'healthy'
}

const resolveSafetyState = (
  snapshot: StockLedgerImpactReadonlySnapshot | null,
  canRead: boolean,
): StockLedgerImpactReadonlyState => {
  if (!canRead) return 'guarded'
  if (!snapshot || snapshot.aggregationRows.length === 0) return 'fallback'
  if (snapshot.aggregationRows.some((row) => row.is_below_safety || row.is_below_reorder)) return 'warning'
  return 'healthy'
}

const resolveSourceGapPrompt = (
  parity: string,
  snapshot: StockLedgerImpactReadonlySnapshot | null,
  canRead: boolean,
  impactState: StockLedgerImpactReadonlyState,
): string => {
  if (!canRead) {
    return '当前账号仅允许 StockLedger 只读回退，库存影响与安全库存状态不触发真实业务链路。'
  }
  if (!snapshot || (snapshot.summaryRows.length === 0 && snapshot.aggregationRows.length === 0)) {
    return '当前无库存影响聚合数据，物料/仓库/批次关系与安全库存状态保持只读回退。'
  }
  if (parity === 'material-stock') {
    return 'material-stock parity 仅回读库存影响摘要与安全库存状态，不开放真实库存联动。'
  }
  if (impactState === 'warning') {
    return '当前存在安全库存预警，库存影响摘要仅用于只读确认，不触发真实库存动作。'
  }
  return '库存影响快照已回读，但真实库存写入与导出仍保持关闭。'
}

export const useStockLedgerImpactReadonly = ({
  snapshot,
  parity,
  canRead,
}: UseStockLedgerImpactReadonlyOptions): {
  stockLedgerImpactReadonlySummary: ComputedRef<StockLedgerImpactReadonlySummary>
} => {
  const stockLedgerImpactReadonlySummary = computed<StockLedgerImpactReadonlySummary>(() => {
    const currentSnapshot = unref(snapshot)
    const parityValue = String(unref(parity) || '').trim().toLowerCase()
    const readable = Boolean(unref(canRead))
    const impactState = resolveImpactState(currentSnapshot, readable)
    const safetyState = resolveSafetyState(currentSnapshot, readable)
    const summaryRows = currentSnapshot?.summaryRows || []
    const aggregationRows = currentSnapshot?.aggregationRows || []
    const summaryBalanceQty = sumNumeric(summaryRows.map((row) => row.balance_qty))
    const actualQtyTotal = sumNumeric(aggregationRows.map((row) => row.actual_qty))
    const orderedQtyTotal = sumNumeric(aggregationRows.map((row) => row.ordered_qty))
    const indentedQtyTotal = sumNumeric(aggregationRows.map((row) => row.indented_qty))
    const warehouseCount = currentSnapshot?.warehouseCount ?? 0
    const belowSafetyCount = currentSnapshot?.belowSafetyCount ?? 0
    const relationSummary = currentSnapshot?.batchRelationFallback || '当前暂无物料/仓库/批次关系回读。'

    return {
      sourceLabel: readable ? 'stock-ledger impact readonly snapshot' : 'stock-ledger readonly fallback',
      parityScopeLabel: STOCK_LEDGER_PARITY_SCOPE_LABELS[parityValue] || STOCK_LEDGER_PARITY_SCOPE_LABELS.default,
      parityLabel: resolveParityLabel(parityValue),
      parityTone: resolveParityTone(parityValue),
      impactStatusLabel: STOCK_LEDGER_IMPACT_STATE_LABELS[impactState],
      impactStatusTone: STOCK_LEDGER_IMPACT_STATE_TAGS[impactState],
      safetyStatusLabel: STOCK_LEDGER_SAFETY_STATE_LABELS[safetyState],
      safetyStatusTone: STOCK_LEDGER_SAFETY_STATE_TAGS[safetyState],
      readonlyGuardLabel: 'stock-ledger readonly guard',
      readonlyGuardTone: readable ? 'warning' : 'danger',
      summaryBalanceQtyLabel: formatAmount(summaryBalanceQty),
      actualQtyTotalLabel: formatAmount(actualQtyTotal),
      orderedQtyTotalLabel: formatAmount(orderedQtyTotal),
      indentedQtyTotalLabel: formatAmount(indentedQtyTotal),
      warehouseCountLabel: String(warehouseCount),
      belowSafetyCountLabel: String(belowSafetyCount),
      relationSummary,
      sourceGapPrompt: resolveSourceGapPrompt(parityValue, currentSnapshot, readable, impactState),
      readonlyGuardReason: STOCK_LEDGER_IMPACT_READONLY_GUARD_LABEL,
      remainingGap: STOCK_LEDGER_IMPACT_REMAINING_GAP,
      writeBoundary: STOCK_LEDGER_IMPACT_WRITE_BOUNDARY,
      retainedCand014: true,
      retainedCand032: true,
    }
  })

  return {
    stockLedgerImpactReadonlySummary,
  }
}

export type { StockLedgerImpactFieldKey }
export { STOCK_LEDGER_IMPACT_FIELDS }
