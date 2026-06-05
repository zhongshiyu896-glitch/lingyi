export type WarehouseTraceReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export interface WarehouseTraceReadonlyMetricField {
  key: 'batchCount' | 'serialCount' | 'ledgerCount' | 'anomalyNodeCount'
  label: string
}

export interface WarehouseTraceReadonlyDiagnosticField {
  key: 'anomaly_nodes' | 'batch_breakpoint' | 'document_breakpoint'
  title: string
  sourceRoute: '/warehouse?tab=diagnostic'
  sourceModule: 'warehouse'
  sourceDescription: string
  blockedReason: string
}

export interface WarehouseTraceReadonlyGuardedAction {
  key: 'inbound' | 'outbound' | 'transfer' | 'count' | 'export' | 'sync'
  label: string
  reason: string
}

export const WAREHOUSE_TRACE_READONLY_METRIC_FIELDS: WarehouseTraceReadonlyMetricField[] = [
  { key: 'batchCount', label: '批次记录数' },
  { key: 'serialCount', label: '序列号记录数' },
  { key: 'ledgerCount', label: '追溯流水数' },
  { key: 'anomalyNodeCount', label: '异常节点数' },
]

export const WAREHOUSE_TRACE_READONLY_DIAGNOSTIC_FIELDS: WarehouseTraceReadonlyDiagnosticField[] = [
  {
    key: 'anomaly_nodes',
    title: '异常节点摘要',
    sourceRoute: '/warehouse?tab=diagnostic',
    sourceModule: 'warehouse',
    sourceDescription: '聚合批次停用、序列状态异常和追溯流水缺口，只提供只读诊断摘要。',
    blockedReason: 'blocked_reason=异常节点修复不在本切片开放范围内，仅允许只读核对。',
  },
  {
    key: 'batch_breakpoint',
    title: '批次断点',
    sourceRoute: '/warehouse?tab=diagnostic',
    sourceModule: 'warehouse',
    sourceDescription: '核对追溯流水与批次目录是否断链，保留批次断点只读提示。',
    blockedReason: 'blocked_reason=批次补链与库存修正保持关闭，当前仅开放只读定位。',
  },
  {
    key: 'document_breakpoint',
    title: '单据断点',
    sourceRoute: '/warehouse?tab=diagnostic',
    sourceModule: 'warehouse',
    sourceDescription: '核对序列号入出单据和追溯凭证是否缺失，只保留单据断点只读摘要。',
    blockedReason: 'blocked_reason=单据补录、导出和跨模块执行未开放，仅允许只读追踪。',
  },
]

export const WAREHOUSE_TRACE_READONLY_ACTIONS: WarehouseTraceReadonlyGuardedAction[] = [
  {
    key: 'inbound',
    label: '入库',
    reason: '当前仅开放仓库追溯诊断只读核对，不开放真实入库动作。',
  },
  {
    key: 'outbound',
    label: '出库',
    reason: '当前仅开放仓库链路诊断，不开放真实出库动作。',
  },
  {
    key: 'transfer',
    label: '调拨',
    reason: '当前仅开放追溯断点只读区，不开放调拨执行。',
  },
  {
    key: 'count',
    label: '盘点',
    reason: '当前仅开放异常节点摘要，不开放库存盘点写入。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '当前仅开放追溯诊断视图，不开放导出执行。',
  },
  {
    key: 'sync',
    label: '同步',
    reason: '当前仅开放只读诊断，不开放 ERPNext 或库存同步写入。',
  },
]

export const WAREHOUSE_TRACE_READONLY_ROUTE_LABELS = {
  traceability: '/warehouse?tab=traceability',
  diagnostic: '/warehouse?tab=diagnostic',
  productStockTraceability: '/warehouse?parity=product-stock&tab=traceability',
  sourceLabel: '追溯诊断来源',
  readonlyMode: 'WAREHOUSE_TRACE_GET_ONLY',
} as const

export const WAREHOUSE_TRACE_READONLY_GUARD_MESSAGE =
  '当前仅开放仓库追溯诊断、异常节点摘要和只读链路核对，不开放入库、出库、调拨、盘点、导出、同步或跨模块执行。'

export const WAREHOUSE_TRACE_READONLY_REMAINING_GAP =
  'remaining_gap=真实入库、出库、调拨、盘点、导出、ERPNext 同步和库存写入未开放；批次/单据断点仍需人工核对。'

export const WAREHOUSE_TRACE_READONLY_WRITE_BOUNDARY =
  'inbound / outbound / transfer / count / export / sync disabled'
