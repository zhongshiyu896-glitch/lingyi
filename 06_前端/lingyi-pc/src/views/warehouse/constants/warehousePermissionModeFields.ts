export type WarehousePermissionModeTagType = 'success' | 'warning' | 'danger' | 'info'

export interface WarehousePermissionModeMetricField {
  key: 'warehouseCount' | 'materialCount' | 'blockedActionCount' | 'warningCount'
  label: string
}

export interface WarehousePermissionModeCardField {
  key: 'permission_mode' | 'readonly_baseline' | 'blocked_reason'
  title: string
  sourceRoute: string
  sourceModule: 'warehouse'
  sourceDescription: string
  blockedReason: string
}

export interface WarehousePermissionModeGuardedAction {
  key: 'inbound' | 'outbound' | 'transfer' | 'count' | 'export' | 'sync'
  label: string
  reason: string
}

export const WAREHOUSE_PERMISSION_MODE_METRIC_FIELDS: WarehousePermissionModeMetricField[] = [
  { key: 'warehouseCount', label: '仓库目录数' },
  { key: 'materialCount', label: '物料基线数' },
  { key: 'blockedActionCount', label: '阻断动作数' },
  { key: 'warningCount', label: '预警节点数' },
]

export const WAREHOUSE_PERMISSION_MODE_CARD_FIELDS: WarehousePermissionModeCardField[] = [
  {
    key: 'permission_mode',
    title: '仓库权限模式摘要',
    sourceRoute: '/warehouse?tab=permission-mode',
    sourceModule: 'warehouse',
    sourceDescription: '按仓库目录、权限模式与 parity 范围聚合当前只读核对结果。',
    blockedReason: 'blocked_reason=仓库权限模式仅开放只读核对，不开放真实库存写动作。',
  },
  {
    key: 'readonly_baseline',
    title: 'readonly baseline',
    sourceRoute: '/warehouse?tab=readonly-baseline',
    sourceModule: 'warehouse',
    sourceDescription: '核对仓库基础目录、物料基线和只读回退状态，不开放真实库存调整。',
    blockedReason: 'blocked_reason=baseline 仅用于读侧核对，不开放导出、盘点、入出库或 ERPNext 联动。',
  },
  {
    key: 'blocked_reason',
    title: 'blocked reason',
    sourceRoute: '/warehouse?tab=permission-mode',
    sourceModule: 'warehouse',
    sourceDescription: '聚合所有被禁用的库存动作和只读 guard 原因，确保页面无启用写动作。',
    blockedReason: 'blocked_reason=真实入库/出库/调拨/盘点/导出/ERPNext 动作全部保持关闭。',
  },
]

export const WAREHOUSE_PERMISSION_MODE_ACTIONS: WarehousePermissionModeGuardedAction[] = [
  {
    key: 'inbound',
    label: '入库',
    reason: '当前仅开放仓库权限模式核对，不开放真实入库执行。',
  },
  {
    key: 'outbound',
    label: '出库',
    reason: '当前仅开放 readonly baseline 与 blocked reason，不开放真实出库执行。',
  },
  {
    key: 'transfer',
    label: '调拨',
    reason: '当前仅开放 permission-mode 只读摘要，不开放调拨写入。',
  },
  {
    key: 'count',
    label: '盘点',
    reason: '当前仅开放仓库 guard 核对，不开放库存盘点写入。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '当前仅开放只读矩阵，不开放导出执行。',
  },
  {
    key: 'sync',
    label: 'ERPNext',
    reason: '当前仅开放 parity 只读核对，不开放 ERPNext 或库存同步。',
  },
]

export const WAREHOUSE_PERMISSION_MODE_ROUTE_LABELS = {
  permissionMode: '/warehouse?tab=permission-mode',
  readonlyBaseline: '/warehouse?tab=readonly-baseline',
  foundationMaterial: '/warehouse?tab=permission-mode&parity=foundation-material',
  sourceLabel: '权限模式来源',
  readonlyMode: 'WAREHOUSE_PERMISSION_MODE_GET_ONLY',
} as const

export const WAREHOUSE_PERMISSION_MODE_GUARD_MESSAGE =
  '当前仅开放仓库权限模式、readonly baseline 和 foundation-material parity 的只读核对，不开放入库、出库、调拨、盘点、导出或 ERPNext 联动。'

export const WAREHOUSE_PERMISSION_MODE_REMAINING_GAP =
  'remaining_gap=真实入库、出库、调拨、盘点、导出、ERPNext 同步与库存写入未开放；权限模式与 baseline 仍需人工核对。'

export const WAREHOUSE_PERMISSION_MODE_WRITE_BOUNDARY =
  'inbound / outbound / transfer / count / export / erpnext disabled'
