export type SalesInventoryStockSourceGuardState =
  | 'ready-readonly'
  | 'query-guarded'
  | 'source-warning'
  | 'permission-guarded'

export type SalesInventoryStockSourceGuardTagType = 'success' | 'warning' | 'danger' | 'info'

export const SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_LABELS: Record<
  SalesInventoryStockSourceGuardState,
  string
> = {
  'ready-readonly': '来源状态已回读 / 只读守卫',
  'query-guarded': '查询态已收敛 / 仅保留只读守卫',
  'source-warning': '来源状态存在预警',
  'permission-guarded': 'stock-source 只读守卫',
}

export const SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_TAGS: Record<
  SalesInventoryStockSourceGuardState,
  SalesInventoryStockSourceGuardTagType
> = {
  'ready-readonly': 'success',
  'query-guarded': 'warning',
  'source-warning': 'warning',
  'permission-guarded': 'danger',
}

export const SALES_INVENTORY_STOCK_SOURCE_GUARD_SUMMARY_FIELDS = [
  { key: 'referenceCountLabel', label: '引用条数' },
  { key: 'activeReferenceCountLabel', label: '启用条数' },
  { key: 'issueCountLabel', label: '来源预警' },
  { key: 'guardedActionCountLabel', label: '禁用动作' },
] as const

export type SalesInventoryStockSourceGuardSummaryFieldKey =
  (typeof SALES_INVENTORY_STOCK_SOURCE_GUARD_SUMMARY_FIELDS)[number]['key']

export const SALES_INVENTORY_STOCK_SOURCE_GUARD_PARITY_LABEL = 'foundation-reference parity'
export const SALES_INVENTORY_STOCK_SOURCE_GUARD_FOCUS_LABEL = 'stock-source focus'
export const SALES_INVENTORY_STOCK_SOURCE_GUARD_READONLY_GUARD_REASON =
  '当前切片仅开放 stock-source / partner-source 只读核对；真实 import、export、customer-supplier write、stock-write、ERPNext、outbox、worker 与 production write 保持冻结。'
export const SALES_INVENTORY_STOCK_SOURCE_GUARD_REMAINING_GAP =
  '未开放真实 import、export、customer-supplier write、stock-write、ERPNext、outbox、worker。'
export const SALES_INVENTORY_STOCK_SOURCE_GUARD_WRITE_BOUNDARY =
  'GET-only | write_request_count=0 | enabled_write_action_texts=[] | forbidden_write_calls=[]'

export const SALES_INVENTORY_STOCK_SOURCE_GUARD_DISABLED_ACTIONS = [
  {
    label: '客户维护',
    reason: 'customer-supplier write 链路冻结',
  },
  {
    label: '供应商维护',
    reason: 'customer-supplier write 链路冻结',
  },
  {
    label: '导入引用',
    reason: 'import 链路冻结',
  },
  {
    label: '导出引用',
    reason: 'export / download 链路冻结',
  },
  {
    label: '库存写入',
    reason: 'stock-write 链路冻结',
  },
  {
    label: 'ERPNext 同步',
    reason: 'ERPNext / outbox / worker / production write 链路冻结',
  },
] as const

export const SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_STATE_LABELS: Record<
  SalesInventoryStockSourceGuardState,
  string
> = {
  'ready-readonly': '来源状态已回读 / 只读守卫',
  'query-guarded': '缺少款号 / 仅保留查询守卫',
  'source-warning': '来源状态存在预警',
  'permission-guarded': '库存来源只读守卫',
}

export const SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_STATE_TAGS: Record<
  SalesInventoryStockSourceGuardState,
  SalesInventoryStockSourceGuardTagType
> = {
  'ready-readonly': 'success',
  'query-guarded': 'warning',
  'source-warning': 'warning',
  'permission-guarded': 'danger',
}

export const SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_SUMMARY_FIELDS = [
  { key: 'sourceCoverageLabel', label: '来源覆盖' },
  { key: 'statusCoverageLabel', label: '状态覆盖' },
  { key: 'warehouseCountLabel', label: '关联仓库' },
  { key: 'warningCountLabel', label: '预警项数' },
  { key: 'droppedCountLabel', label: '丢弃摘要' },
] as const

export const SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_PARITY_LABEL = 'material-stock parity'
export const SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_FOCUS_LABEL = 'stock-source focus'
export const SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_READONLY_GUARD_REASON =
  '当前切片仅开放 stock-source / source-status 只读核对；真实 stock-entry、stock-write、outbound、transfer、count、export、ERPNext、outbox、worker 与 production write 保持冻结。'
export const SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_REMAINING_GAP =
  '未开放真实 stock-entry、stock-write、outbound、transfer、count、export、ERPNext、outbox、worker。'
export const SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_WRITE_BOUNDARY =
  'GET-only | write_request_count=0 | enabled_write_action_texts=[] | forbidden_write_calls=[]'

export const SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_DISABLED_ACTIONS = [
  {
    label: '库存入账',
    reason: 'stock-entry / stock-write 链路冻结',
  },
  {
    label: '库存出账',
    reason: 'outbound / stock-write 链路冻结',
  },
  {
    label: '调拨执行',
    reason: 'transfer / worker 链路冻结',
  },
  {
    label: '盘点过账',
    reason: 'count / stock-write 链路冻结',
  },
  {
    label: '导出台账',
    reason: 'export / download 链路冻结',
  },
  {
    label: 'ERPNext 同步',
    reason: 'ERPNext / outbox / worker / production write 链路冻结',
  },
] as const
