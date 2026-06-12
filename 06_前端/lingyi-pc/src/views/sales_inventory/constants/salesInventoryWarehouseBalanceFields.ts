export type SalesInventoryWarehouseBalanceReadonlyState =
  | 'ready-readonly'
  | 'query-guarded'
  | 'source-warning'
  | 'permission-guarded'

export type SalesInventoryWarehouseBalanceReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export const SALES_INVENTORY_WAREHOUSE_BALANCE_STATE_LABELS: Record<
  SalesInventoryWarehouseBalanceReadonlyState,
  string
> = {
  'ready-readonly': 'warehouse-balance 已回读 / 只读守卫',
  'query-guarded': '缺少款号 / 保留查询守卫',
  'source-warning': 'warehouse-balance 存在预警',
  'permission-guarded': 'warehouse-balance 权限只读守卫',
}

export const SALES_INVENTORY_WAREHOUSE_BALANCE_STATE_TAGS: Record<
  SalesInventoryWarehouseBalanceReadonlyState,
  SalesInventoryWarehouseBalanceReadonlyTagType
> = {
  'ready-readonly': 'success',
  'query-guarded': 'warning',
  'source-warning': 'warning',
  'permission-guarded': 'danger',
}

export const SALES_INVENTORY_WAREHOUSE_BALANCE_SUMMARY_FIELDS = [
  { key: 'warehouseCoverageLabel', label: '仓库覆盖' },
  { key: 'balanceCoverageLabel', label: '结存覆盖' },
  { key: 'warningCountLabel', label: '余额预警' },
  { key: 'guardedActionCountLabel', label: '禁用动作' },
] as const

export type SalesInventoryWarehouseBalanceSummaryFieldKey =
  (typeof SALES_INVENTORY_WAREHOUSE_BALANCE_SUMMARY_FIELDS)[number]['key']

export const SALES_INVENTORY_WAREHOUSE_BALANCE_PARITY_LABEL = 'material-stock parity'
export const SALES_INVENTORY_WAREHOUSE_BALANCE_FOCUS_LABEL = 'warehouse-source focus'
export const SALES_INVENTORY_WAREHOUSE_BALANCE_READONLY_GUARD_REASON =
  '当前切片仅开放 warehouse-balance 只读核对；真实 delivery/export/stock-write/outbox/worker/ERPNext/production write 保持冻结。'
export const SALES_INVENTORY_WAREHOUSE_BALANCE_REMAINING_GAP =
  '未开放真实 delivery、export、stock-write、ERPNext、outbox、worker。'
export const SALES_INVENTORY_WAREHOUSE_BALANCE_WRITE_BOUNDARY =
  'GET-only | write_request_count=0 | enabled_write_action_texts=[] | forbidden_write_calls=[]'

export const SALES_INVENTORY_WAREHOUSE_BALANCE_DISABLED_ACTIONS = [
  {
    key: 'delivery-outbound',
    label: '发货出库',
    reason: 'delivery / stock-write disabled',
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
