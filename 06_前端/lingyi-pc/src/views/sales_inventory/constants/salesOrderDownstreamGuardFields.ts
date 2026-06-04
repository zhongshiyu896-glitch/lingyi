export type SalesOrderDownstreamGuardState =
  | 'ready-readonly'
  | 'customer-missing'
  | 'factory-pending'
  | 'item-missing'

export type SalesOrderDownstreamGuardActionState = 'guarded' | 'blocked' | 'disabled'

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
