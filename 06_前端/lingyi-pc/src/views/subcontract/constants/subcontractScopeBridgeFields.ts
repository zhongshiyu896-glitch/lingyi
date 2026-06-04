export type SubcontractScopeBridgeTagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

export type SubcontractScopeBridgeStatusCode = 'ready' | 'pending' | 'blocked'

export type SubcontractScopeBridgeFieldKey =
  | 'sales_order'
  | 'sales_order_item'
  | 'production_plan_id'
  | 'work_order'
  | 'job_card'

export const SUBCONTRACT_SCOPE_BRIDGE_STATUS_LABELS: Record<SubcontractScopeBridgeStatusCode, string> = {
  ready: '桥接已对齐',
  pending: '桥接待核对',
  blocked: '桥接阻断',
}

export const SUBCONTRACT_SCOPE_BRIDGE_STATUS_TAGS: Record<
  SubcontractScopeBridgeStatusCode,
  SubcontractScopeBridgeTagType
> = {
  ready: 'success',
  pending: 'warning',
  blocked: 'danger',
}

export const SUBCONTRACT_SCOPE_BRIDGE_FIELD_LABELS: Record<SubcontractScopeBridgeFieldKey, string> = {
  sales_order: '销售订单',
  sales_order_item: '销售订单行',
  production_plan_id: '生产计划',
  work_order: '工单',
  job_card: '工序卡',
}
