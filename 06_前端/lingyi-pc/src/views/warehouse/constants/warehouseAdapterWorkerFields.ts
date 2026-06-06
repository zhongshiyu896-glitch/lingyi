export type WarehouseAdapterWorkerTagType = 'success' | 'warning' | 'danger' | 'info'

export interface WarehouseAdapterWorkerMetricField {
  key: 'productStockSkuCount' | 'adapterPendingCount' | 'workerPendingCount' | 'blockedChainCount'
  label: string
}

export interface WarehouseAdapterWorkerDiagnosticField {
  key: 'other_inbound_adapter' | 'purchase_return_adapter' | 'semi_finished_worker'
  title: string
  sourceRoute: string
  sourceModule: 'warehouse'
  sourceDescription: string
  blockedReason: string
}

export interface WarehouseAdapterWorkerGuardedAction {
  key: 'stock_entry' | 'outbound' | 'count' | 'export' | 'worker'
  label: string
  reason: string
}

export const WAREHOUSE_ADAPTER_WORKER_METRIC_FIELDS: WarehouseAdapterWorkerMetricField[] = [
  { key: 'productStockSkuCount', label: '库存 SKU 数' },
  { key: 'adapterPendingCount', label: 'adapter 待处理' },
  { key: 'workerPendingCount', label: 'worker 待处理' },
  { key: 'blockedChainCount', label: 'blocked 链路数' },
]

export const WAREHOUSE_ADAPTER_WORKER_DIAGNOSTIC_FIELDS: WarehouseAdapterWorkerDiagnosticField[] = [
  {
    key: 'other_inbound_adapter',
    title: '其他入仓 adapter',
    sourceRoute: '/warehouse?tab=adapter-worker&parity=product-stock',
    sourceModule: 'warehouse',
    sourceDescription: '核对其他入仓读侧状态与 adapter 待处理数量，只展示只读状态镜像。',
    blockedReason: 'blocked_reason=确认入仓、撤销入仓与导出保持关闭，当前只允许只读核对。',
  },
  {
    key: 'purchase_return_adapter',
    title: '采购退料出仓 adapter',
    sourceRoute: '/warehouse?tab=adapter-worker&parity=product-stock',
    sourceModule: 'warehouse',
    sourceDescription: '核对采购退料出仓状态与 adapter 阻断项，不开放真实出仓执行。',
    blockedReason: 'blocked_reason=确认出仓、撤销出仓与导出保持关闭，当前只允许只读核对。',
  },
  {
    key: 'semi_finished_worker',
    title: '半成品出仓 worker',
    sourceRoute: '/warehouse?tab=adapter-worker&parity=product-stock&focus=worker-chain',
    sourceModule: 'warehouse',
    sourceDescription: '核对半成品出仓 worker-chain 状态与待处理数量，不开放真实 worker 执行。',
    blockedReason: 'blocked_reason=worker 执行、打印、导出与 ERPNext 同步保持关闭，当前只允许只读核对。',
  },
]

export const WAREHOUSE_ADAPTER_WORKER_GUARDED_ACTIONS: WarehouseAdapterWorkerGuardedAction[] = [
  {
    key: 'stock_entry',
    label: '库存入库',
    reason: '当前仅开放 adapter-worker 只读核对，不开放真实库存入库动作。',
  },
  {
    key: 'outbound',
    label: '库存出库',
    reason: '当前仅开放 adapter-worker 只读核对，不开放真实库存出库动作。',
  },
  {
    key: 'count',
    label: '库存盘点',
    reason: '当前仅开放 worker-chain 状态镜像，不开放盘点写入。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '当前仅开放只读视图，不开放导出执行。',
  },
  {
    key: 'worker',
    label: 'worker 执行',
    reason: '当前仅开放 worker-chain focus 状态核对，不开放 outbox/worker/ERPNext 执行。',
  },
]

export const WAREHOUSE_ADAPTER_WORKER_ROUTE_LABELS = {
  defaultRoute: '/warehouse',
  parityRoute: '/warehouse?tab=adapter-worker&parity=product-stock',
  focusRoute: '/warehouse?tab=adapter-worker&parity=product-stock&focus=worker-chain',
  sourceLabel: 'adapter-worker 来源',
  readonlyMode: 'WAREHOUSE_ADAPTER_WORKER_GET_ONLY',
} as const

export const WAREHOUSE_ADAPTER_WORKER_GUARD_MESSAGE =
  '当前仅开放 adapter-worker 状态镜像、worker-chain focus 和只读链路核对，不开放 stock entry、outbound、count、export、worker 或 ERPNext 执行。'

export const WAREHOUSE_ADAPTER_WORKER_REMAINING_GAP =
  'remaining_gap=真实库存入库、出库、盘点、导出、worker 执行、ERPNext 适配与 outbox 链路未开放；仅保留只读状态镜像与阻断提示。'

export const WAREHOUSE_ADAPTER_WORKER_WRITE_BOUNDARY =
  'stock entry / outbound / count / export / worker disabled'
