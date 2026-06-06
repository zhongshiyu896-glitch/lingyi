export type WarehouseFinishedGoodsInboundTagType = 'success' | 'warning' | 'danger' | 'info'

export interface WarehouseFinishedGoodsInboundMetricField {
  key: 'productStockSkuCount' | 'inboundCandidateCount' | 'blockedCandidateCount' | 'readableCandidateCount'
  label: string
}

export interface WarehouseFinishedGoodsInboundGuardedAction {
  key: 'stock_entry' | 'posting' | 'export' | 'worker'
  label: string
  reason: string
}

export const WAREHOUSE_FINISHED_GOODS_INBOUND_METRIC_FIELDS: WarehouseFinishedGoodsInboundMetricField[] = [
  { key: 'productStockSkuCount', label: '库存 SKU 数' },
  { key: 'inboundCandidateCount', label: '入库候选数' },
  { key: 'blockedCandidateCount', label: '阻断候选数' },
  { key: 'readableCandidateCount', label: '可读候选数' },
]

export const WAREHOUSE_FINISHED_GOODS_INBOUND_GUARDED_ACTIONS: WarehouseFinishedGoodsInboundGuardedAction[] = [
  {
    key: 'stock_entry',
    label: '创建入库草稿',
    reason: '当前仅开放 finished-goods inbound 只读核对，不开放真实 stock-entry 草稿创建。',
  },
  {
    key: 'posting',
    label: '成品入库过账',
    reason: '当前仅开放 inbound item/status 核对，不开放真实成品入库过账。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '当前仅开放只读视图，不开放 finished-goods inbound 导出执行。',
  },
  {
    key: 'worker',
    label: 'worker / ERPNext',
    reason: '当前仅开放只读状态镜像，不开放 outbox、worker 或 ERPNext 同步执行。',
  },
]

export const WAREHOUSE_FINISHED_GOODS_INBOUND_ROUTE_LABELS = {
  defaultRoute: '/warehouse',
  parityRoute: '/warehouse?tab=finished-goods-inbound&parity=product-stock',
  focusRoute: '/warehouse?tab=finished-goods-inbound&parity=product-stock&focus=inbound-readonly',
  sourceLabel: 'finished-goods-inbound 来源',
  readonlyMode: 'WAREHOUSE_FINISHED_GOODS_INBOUND_GET_ONLY',
} as const

export const WAREHOUSE_FINISHED_GOODS_INBOUND_GUARD_MESSAGE =
  '当前仅开放成品入库候选、product-stock parity 与 readonly inbound focus 核对，不开放真实入库草稿、过账、导出、worker 或 ERPNext 执行。'

export const WAREHOUSE_FINISHED_GOODS_INBOUND_REMAINING_GAP =
  'remaining_gap=真实成品入库、库存过账、导出、worker、ERPNext 适配与 outbox 链路未开放；仅保留 readonly candidate / blocked reason / parity 镜像。'

export const WAREHOUSE_FINISHED_GOODS_INBOUND_WRITE_BOUNDARY =
  'stock-entry / inbound-posting / export / worker disabled'
