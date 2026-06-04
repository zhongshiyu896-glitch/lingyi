export type ProductionOrderParityTagType = 'success' | 'warning' | 'danger' | 'info'

export type ProductionOrderParityMetricKey =
  | 'mirroredOrderCount'
  | 'jobCardReadyCount'
  | 'blockedCount'
  | 'statusSnapshot'

export const PRODUCTION_ORDER_PARITY_METRIC_FIELDS = [
  { key: 'mirroredOrderCount', label: '订单镜像' },
  { key: 'jobCardReadyCount', label: '工序已镜像' },
  { key: 'blockedCount', label: '阻断提示' },
  { key: 'statusSnapshot', label: '状态摘要' },
] as const satisfies ReadonlyArray<{ key: ProductionOrderParityMetricKey; label: string }>

export const PRODUCTION_ORDER_PARITY_SCOPE_LABELS: Record<string, string> = {
  '': '主入口只读',
  'production-order': 'production-order parity',
}

export const PRODUCTION_ORDER_PARITY_REMAINING_GAPS = [
  '真实生产派工未开放',
  '生产状态变更未开放',
  '库存影响与 ERPNext production 未开放',
  'job-card sync / outbox / worker 未开放',
] as const
