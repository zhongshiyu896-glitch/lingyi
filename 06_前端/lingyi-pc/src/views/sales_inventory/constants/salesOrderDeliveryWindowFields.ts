export type SalesOrderDeliveryWindowTagType = 'success' | 'warning' | 'danger' | 'info'

export const SALES_ORDER_DELIVERY_WINDOW_FIELDS = [
  { key: 'recordCountLabel', label: '订单/明细' },
  { key: 'deliveryPendingLabel', label: '待交窗口' },
  { key: 'overdueCountLabel', label: '逾期窗口' },
  { key: 'sourceScopeLabel', label: '来源范围' },
  { key: 'coverageLabel', label: '覆盖状态' },
  { key: 'refreshLabel', label: '最后刷新' },
] as const

export type SalesOrderDeliveryWindowFieldKey =
  (typeof SALES_ORDER_DELIVERY_WINDOW_FIELDS)[number]['key']

export const SALES_ORDER_DELIVERY_WINDOW_PARITY_LABEL = 'sales-order parity'
export const SALES_ORDER_DELIVERY_WINDOW_FOCUS_LABEL = 'delivery-source'

export const SALES_ORDER_DELIVERY_WINDOW_READONLY_GUARD_REASON =
  '销售订单交付窗口只开放只读核对，真实出库、发运确认、导出、库存写入与跨模块执行均保持禁用。'

export const SALES_ORDER_DELIVERY_WINDOW_REMAINING_GAP =
  '未开放真实出库、发运确认、导出、stock write、ERPNext、outbox、worker 与跨模块执行。'

export const SALES_ORDER_DELIVERY_WINDOW_WRITE_BOUNDARY =
  'outbound / delivery-confirm / export / stock-write / ERPNext / outbox / worker disabled'

export const SALES_ORDER_DELIVERY_WINDOW_DISABLED_ACTIONS = [
  { label: '发运确认', reason: '本地只读试用模式：发运确认已停用' },
  { label: '导入发运', reason: '本地只读试用模式：发运导入已停用' },
  { label: '导出窗口', reason: '本地只读试用模式：交付窗口导出已停用' },
  { label: 'ERPNext 同步', reason: '本地只读试用模式：ERPNext 同步已停用' },
  { label: 'Outbox 推送', reason: '本地只读试用模式：Outbox 推送已停用' },
  { label: 'Worker 执行', reason: '本地只读试用模式：Worker 执行已停用' },
  { label: '跨模块执行', reason: '本地只读试用模式：跨模块执行已停用' },
] as const
