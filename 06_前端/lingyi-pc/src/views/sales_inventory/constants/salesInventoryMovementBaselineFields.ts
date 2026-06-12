export type SalesInventoryMovementBaselineReadonlyState =
  | 'ready-readonly'
  | 'query-guarded'
  | 'source-warning'
  | 'permission-guarded'

export type SalesInventoryMovementBaselineReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export const SALES_INVENTORY_MOVEMENT_BASELINE_STATE_LABELS: Record<
  SalesInventoryMovementBaselineReadonlyState,
  string
> = {
  'ready-readonly': 'movement-baseline 已回读 / 只读守卫',
  'query-guarded': '缺少款号 / 保留查询守卫',
  'source-warning': 'movement-baseline 存在预警',
  'permission-guarded': 'movement-baseline 权限只读守卫',
}

export const SALES_INVENTORY_MOVEMENT_BASELINE_STATE_TAGS: Record<
  SalesInventoryMovementBaselineReadonlyState,
  SalesInventoryMovementBaselineReadonlyTagType
> = {
  'ready-readonly': 'success',
  'query-guarded': 'warning',
  'source-warning': 'warning',
  'permission-guarded': 'danger',
}

export const SALES_INVENTORY_MOVEMENT_BASELINE_SUMMARY_FIELDS = [
  { key: 'movementCoverageLabel', label: '流水覆盖' },
  { key: 'deltaCoverageLabel', label: '变动合计' },
  { key: 'warehouseCoverageLabel', label: '仓库覆盖' },
  { key: 'guardedActionCountLabel', label: '禁用动作' },
] as const

export type SalesInventoryMovementBaselineSummaryFieldKey =
  (typeof SALES_INVENTORY_MOVEMENT_BASELINE_SUMMARY_FIELDS)[number]['key']

export const SALES_INVENTORY_MOVEMENT_BASELINE_PARITY_LABEL = 'material-stock parity'
export const SALES_INVENTORY_MOVEMENT_BASELINE_FOCUS_LABEL = 'movement-source focus'
export const SALES_INVENTORY_MOVEMENT_BASELINE_READONLY_GUARD_REASON =
  '当前切片仅开放 movement-baseline 只读核对；真实 delivery/export/stock-write/outbox/worker/ERPNext/production write 保持冻结。'
export const SALES_INVENTORY_MOVEMENT_BASELINE_REMAINING_GAP =
  '未开放真实 delivery、export、stock-write、ERPNext、outbox、worker。'
export const SALES_INVENTORY_MOVEMENT_BASELINE_WRITE_BOUNDARY =
  'GET-only | write_request_count=0 | enabled_write_action_texts=[] | forbidden_write_calls=[]'

export const SALES_INVENTORY_MOVEMENT_BASELINE_DISABLED_ACTIONS = [
  {
    key: 'delivery-outbound',
    label: '发货出库',
    reason: 'delivery disabled',
  },
  {
    key: 'ledger-export',
    label: '导出台账',
    reason: 'export / download disabled',
  },
  {
    key: 'stock-write',
    label: '库存写入',
    reason: 'stock-write disabled',
  },
  {
    key: 'outbox-worker',
    label: 'Outbox / Worker',
    reason: 'outbox / worker / production write disabled',
  },
  {
    key: 'erpnext-bridge',
    label: 'ERPNext 映射',
    reason: 'ERPNext adapter disabled',
  },
] as const
