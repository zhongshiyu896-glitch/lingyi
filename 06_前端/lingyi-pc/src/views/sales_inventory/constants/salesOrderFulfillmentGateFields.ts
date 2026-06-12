export type SalesOrderFulfillmentGateState =
  | 'awaiting-fulfillment'
  | 'delivery-pending'
  | 'ready-readonly'
  | 'closed-readonly'

export type SalesOrderFulfillmentGateTagType = 'success' | 'warning' | 'danger' | 'info'

export const SALES_ORDER_FULFILLMENT_GATE_STATE_LABELS: Record<
  SalesOrderFulfillmentGateState,
  string
> = {
  'awaiting-fulfillment': '待进入履约校验',
  'delivery-pending': '待发运只读核对',
  'ready-readonly': '履约链可读 / 只读守卫',
  'closed-readonly': '已关闭 / 只读归档',
}

export const SALES_ORDER_FULFILLMENT_GATE_STATE_TAGS: Record<
  SalesOrderFulfillmentGateState,
  'success' | 'warning' | 'danger' | 'info'
> = {
  'awaiting-fulfillment': 'info',
  'delivery-pending': 'warning',
  'ready-readonly': 'success',
  'closed-readonly': 'info',
}

export const SALES_ORDER_FULFILLMENT_GATE_SUMMARY_FIELDS = [
  { key: 'sourceStatusLabel', label: '来源状态' },
  { key: 'fulfillmentStateLabel', label: '履约状态' },
  { key: 'deliveryWriteLabel', label: '发运写链路' },
  { key: 'inventoryWriteLabel', label: '库存写链路' },
  { key: 'blockingCount', label: '阻断项数' },
] as const

export const SALES_ORDER_FULFILLMENT_GATE_PARITY_LABEL = 'sales-order parity'
export const SALES_ORDER_FULFILLMENT_GATE_FOCUS_LABEL = 'fulfillment-source focus'
export const SALES_ORDER_FULFILLMENT_GATE_READONLY_GUARD_REASON =
  '当前切片仅开放 fulfillment gate 只读核对；delivery write、customer-supplier write、stock-write、outbox/worker、ERPNext 与 production write 保持冻结。'
export const SALES_ORDER_FULFILLMENT_GATE_REMAINING_GAP =
  '真实 delivery/export/customer-supplier write、stock-write、出库联动、outbox/worker、ERPNext 映射与跨模块执行仍未开放。'
export const SALES_ORDER_FULFILLMENT_GATE_WRITE_BOUNDARY =
  'GET-only | write_request_count=0 | enabled_write_action_texts=[] | forbidden_write_calls=[]'

export const SALES_ORDER_FULFILLMENT_GATE_DISABLED_ACTIONS = [
  {
    label: '发运确认',
    reason: 'delivery write 链路冻结',
  },
  {
    label: '客商回写',
    reason: 'customer-supplier write 链路冻结',
  },
  {
    label: '库存出库',
    reason: 'stock-write / outbound 链路冻结',
  },
  {
    label: '导出单据',
    reason: 'export / download 链路冻结',
  },
  {
    label: 'Outbox / Worker',
    reason: 'outbox / worker 链路冻结',
  },
  {
    label: 'ERPNext 映射',
    reason: 'ERPNext adapter / production write 保持 disabled',
  },
] as const
