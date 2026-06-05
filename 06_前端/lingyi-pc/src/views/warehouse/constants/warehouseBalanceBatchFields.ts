export type WarehouseBalanceBatchReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export type WarehouseBalanceReadonlyState = 'healthy' | 'warning' | 'fallback' | 'guarded'
export type WarehouseBatchReadonlyState = 'healthy' | 'warning' | 'fallback' | 'guarded'

export const WAREHOUSE_BALANCE_READONLY_STATE_TAGS: Record<
  WarehouseBalanceReadonlyState,
  WarehouseBalanceBatchReadonlyTagType
> = {
  healthy: 'success',
  warning: 'warning',
  fallback: 'info',
  guarded: 'danger',
}

export const WAREHOUSE_BALANCE_READONLY_STATE_LABELS: Record<WarehouseBalanceReadonlyState, string> = {
  healthy: '仓库余额已回读',
  warning: '仓库余额存在预警',
  fallback: '仓库余额待真实校验',
  guarded: '仓库余额只读守卫',
}

export const WAREHOUSE_BATCH_READONLY_STATE_TAGS: Record<
  WarehouseBatchReadonlyState,
  WarehouseBalanceBatchReadonlyTagType
> = {
  healthy: 'success',
  warning: 'warning',
  fallback: 'info',
  guarded: 'danger',
}

export const WAREHOUSE_BATCH_READONLY_STATE_LABELS: Record<WarehouseBatchReadonlyState, string> = {
  healthy: '批次影响已回读',
  warning: '批次影响存在预警',
  fallback: '批次影响待真实校验',
  guarded: '批次影响只读守卫',
}

export const WAREHOUSE_PARITY_SCOPE_LABELS: Record<string, string> = {
  'foundation-warehouse': 'foundation-warehouse parity',
  'product-stock': 'product-stock parity',
  default: 'warehouse-readonly',
}

export const WAREHOUSE_BALANCE_BATCH_FIELDS = [
  { key: 'stockQtyTotalLabel', label: '仓库余额总量' },
  { key: 'projectedQtyTotalLabel', label: '预计结存总量' },
  { key: 'warningSkuCountLabel', label: '预警 SKU 数' },
  { key: 'batchCountLabel', label: '批次记录数' },
  { key: 'batchQtyTotalLabel', label: '批次数量合计' },
  { key: 'disabledBatchCountLabel', label: '停用批次数' },
] as const

export type WarehouseBalanceBatchFieldKey = (typeof WAREHOUSE_BALANCE_BATCH_FIELDS)[number]['key']

export const WAREHOUSE_BALANCE_BATCH_READONLY_GUARD_LABEL =
  '入库、出库、调拨、库存影响与导出动作保持只读守卫。'

export const WAREHOUSE_BALANCE_BATCH_WRITE_BOUNDARY =
  'stock-entry / transfer / export / inventory-impact disabled'

export const WAREHOUSE_BALANCE_BATCH_REMAINING_GAP =
  '未开放真实入库、出库、调拨、库存影响、导出、ERPNext、outbox、worker。'
