export type SalesOrderDownstreamGuardState =
  | 'ready-readonly'
  | 'customer-missing'
  | 'factory-pending'
  | 'item-missing'

export type SalesOrderDownstreamGuardActionState = 'guarded' | 'blocked' | 'disabled'
export type SalesOrderDownstreamGuardTagType = 'success' | 'warning' | 'danger' | 'info'

export const SALES_ORDER_DOWNSTREAM_GUARD_STATE_LABELS: Record<
  SalesOrderDownstreamGuardState,
  string
> = {
  'ready-readonly': '来源链完整 / 只读守卫',
  'customer-missing': '缺失客户引用链',
  'factory-pending': '缺失工厂履约映射',
  'item-missing': '缺失来源款号',
}

export const SALES_ORDER_DOWNSTREAM_GUARD_STATE_TAGS: Record<
  SalesOrderDownstreamGuardState,
  'success' | 'warning' | 'danger'
> = {
  'ready-readonly': 'success',
  'customer-missing': 'danger',
  'factory-pending': 'warning',
  'item-missing': 'warning',
}

export const SALES_ORDER_DOWNSTREAM_GUARD_ACTION_TAGS: Record<
  SalesOrderDownstreamGuardActionState,
  'success' | 'warning' | 'info'
> = {
  guarded: 'warning',
  blocked: 'warning',
  disabled: 'info',
}

export const SALES_ORDER_DOWNSTREAM_GUARD_SUMMARY_FIELDS = [
  { key: 'sourceCompletenessLabel', label: '来源完整度' },
  { key: 'downstreamStateLabel', label: '联动状态' },
  { key: 'productionGuardLabel', label: '生产联动' },
  { key: 'purchaseGuardLabel', label: '采购联动' },
  { key: 'blockingCount', label: '阻断项数' },
] as const

export const SALES_ORDER_DOWNSTREAM_GUARD_PARITY_LABEL = 'sales-order parity'
export const SALES_ORDER_DOWNSTREAM_GUARD_FOCUS_LABEL = 'downstream-source focus'
export const SALES_ORDER_DOWNSTREAM_GUARD_READONLY_GUARD_REASON =
  '当前切片仅开放下游联动前置守卫只读核对；真实发运确认、库存出库、生产/采购下推与跨模块执行保持冻结。'
export const SALES_ORDER_DOWNSTREAM_GUARD_REMAINING_GAP =
  '真实发运确认、库存出库、导出、生产/采购下推、ERPNext 同步与跨模块执行仍未开放。'
export const SALES_ORDER_DOWNSTREAM_GUARD_WRITE_BOUNDARY =
  'GET-only | write_request_count=0 | enabled_write_action_texts=[] | forbidden_write_calls=[]'
export const SALES_ORDER_DOWNSTREAM_GUARD_DISABLED_ACTIONS = [
  {
    label: '发运确认',
    reason: 'delivery confirm write 链路冻结',
  },
  {
    label: '库存出库',
    reason: 'stock write / outbound 链路冻结',
  },
  {
    label: '导出单据',
    reason: 'export / download 链路冻结',
  },
  {
    label: '下推生产',
    reason: 'work-order issue / release / sync 保持 disabled',
  },
  {
    label: '下推采购',
    reason: 'purchase execution / outbox / worker 保持 disabled',
  },
  {
    label: 'ERPNext 同步',
    reason: 'ERPNext adapter / production write 保持 disabled',
  },
] as const
