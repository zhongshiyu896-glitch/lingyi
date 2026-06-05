export type StockLedgerImpactReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export type StockLedgerImpactReadonlyState = 'healthy' | 'warning' | 'fallback' | 'guarded'

export const STOCK_LEDGER_IMPACT_STATE_TAGS: Record<
  StockLedgerImpactReadonlyState,
  StockLedgerImpactReadonlyTagType
> = {
  healthy: 'success',
  warning: 'warning',
  fallback: 'info',
  guarded: 'danger',
}

export const STOCK_LEDGER_IMPACT_STATE_LABELS: Record<StockLedgerImpactReadonlyState, string> = {
  healthy: '库存影响已回读',
  warning: '库存影响存在预警',
  fallback: '库存影响待真实校验',
  guarded: '库存影响只读守卫',
}

export const STOCK_LEDGER_SAFETY_STATE_TAGS: Record<
  StockLedgerImpactReadonlyState,
  StockLedgerImpactReadonlyTagType
> = {
  healthy: 'success',
  warning: 'warning',
  fallback: 'info',
  guarded: 'danger',
}

export const STOCK_LEDGER_SAFETY_STATE_LABELS: Record<StockLedgerImpactReadonlyState, string> = {
  healthy: '安全库存状态已回读',
  warning: '安全库存存在预警',
  fallback: '安全库存待真实校验',
  guarded: '安全库存只读守卫',
}

export const STOCK_LEDGER_PARITY_SCOPE_LABELS: Record<string, string> = {
  'material-stock': 'material-stock parity',
  default: 'stock-ledger-readonly',
}

export const STOCK_LEDGER_IMPACT_FIELDS = [
  { key: 'summaryBalanceQtyLabel', label: '台账结存合计' },
  { key: 'actualQtyTotalLabel', label: '实际库存合计' },
  { key: 'orderedQtyTotalLabel', label: '占用库存合计' },
  { key: 'indentedQtyTotalLabel', label: '待入库存合计' },
  { key: 'warehouseCountLabel', label: '关联仓库数' },
  { key: 'belowSafetyCountLabel', label: '安全库存预警' },
] as const

export type StockLedgerImpactFieldKey = (typeof STOCK_LEDGER_IMPACT_FIELDS)[number]['key']

export const STOCK_LEDGER_IMPACT_READONLY_GUARD_LABEL =
  'StockLedger 仅开放只读回退，入库、出库、调拨、库存影响与导出动作保持禁用。'

export const STOCK_LEDGER_IMPACT_WRITE_BOUNDARY =
  'stock-ledger / stock-entry / transfer / export disabled'

export const STOCK_LEDGER_IMPACT_REMAINING_GAP =
  '未开放真实入库、出库、调拨、库存影响、导出、ERPNext、outbox、worker。'
