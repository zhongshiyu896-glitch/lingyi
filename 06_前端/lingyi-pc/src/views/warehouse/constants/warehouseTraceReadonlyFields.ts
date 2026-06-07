export type WarehouseTraceReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export interface WarehouseTraceReadonlyMetricField {
  key: 'traceCount' | 'batchCount' | 'serialCount' | 'sourceCount'
  label: string
}

export interface WarehouseTraceReadonlyStatusField {
  key: 'trace_item' | 'batch_status' | 'serial_status' | 'source_status'
  title: string
}

export interface WarehouseTraceReadonlyGuardedAction {
  key: 'stock_entry' | 'export' | 'erpnext' | 'outbox' | 'worker'
  label: string
  reason: string
}

export interface WarehouseTraceReadonlyGuardReasonMap {
  refreshPermission: string
  reloadModuleActions: string
}

export const WAREHOUSE_TRACE_READONLY_METRIC_FIELDS: WarehouseTraceReadonlyMetricField[] = [
  { key: 'traceCount', label: '追溯流水数' },
  { key: 'batchCount', label: '批次记录数' },
  { key: 'serialCount', label: '序列号记录数' },
  { key: 'sourceCount', label: '来源节点数' },
]

export const WAREHOUSE_TRACE_READONLY_STATUS_FIELDS: WarehouseTraceReadonlyStatusField[] = [
  { key: 'trace_item', title: '追溯流水状态' },
  { key: 'batch_status', title: '批次来源状态' },
  { key: 'serial_status', title: '序列来源状态' },
  { key: 'source_status', title: 'trace-source 状态' },
]

export const WAREHOUSE_TRACE_READONLY_ACTIONS: WarehouseTraceReadonlyGuardedAction[] = [
  {
    key: 'stock_entry',
    label: '库存动作',
    reason: '当前仅开放 trace-readonly 核对，不开放 stock-entry / inbound / outbound / count / transfer。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '当前仅开放追溯只读摘要，不开放导出执行。',
  },
  {
    key: 'erpnext',
    label: 'ERPNext',
    reason: '当前仅开放 trace-source 核对，不开放 ERPNext 适配器写入。',
  },
  {
    key: 'outbox',
    label: 'Outbox',
    reason: '当前仅开放追溯只读摘要，不开放 outbox 投递或补偿。',
  },
  {
    key: 'worker',
    label: 'Worker',
    reason: '当前仅开放追溯只读摘要，不开放 worker 执行或后台修复。',
  },
]

export const WAREHOUSE_TRACE_READONLY_GUARD_REASON_MAP: WarehouseTraceReadonlyGuardReasonMap = {
  refreshPermission: 'trace-readonly 边界保持刷新权限按钮不可执行，避免触发共享全局权限刷新。',
  reloadModuleActions: 'trace-readonly 边界保持模块动作重载按钮不可执行，避免触发共享模块动作链路。',
}

export const WAREHOUSE_TRACE_READONLY_ROUTE_LABELS = {
  defaultRoute: '/warehouse/dashboard?tab=trace-readonly',
  sourceLabel: 'trace-source',
  readonlyMode: 'WAREHOUSE_TRACE_GET_ONLY',
} as const

export const WAREHOUSE_TRACE_READONLY_GUARD_MESSAGE =
  '当前仅开放仓储追溯只读核对，不开放 stock-entry、export、ERPNext、outbox、worker 或跨模块库存执行。'

export const WAREHOUSE_TRACE_READONLY_REMAINING_GAP =
  'remaining_gap=真实 stock-entry、inbound、outbound、count、transfer、export、ERPNext、outbox、worker 与库存写入未开放；当前仅保留 trace-source 和 item/status 摘要。'

export const WAREHOUSE_TRACE_READONLY_WRITE_BOUNDARY =
  'stock-entry / export / ERPNext / outbox / worker disabled'

export const WAREHOUSE_TRACE_READONLY_BLOCKED_REASON =
  'blocked_reason=stock-entry / export / ERPNext / outbox / worker 保持关闭，当前只允许 trace-readonly 摘要与来源核对。'
