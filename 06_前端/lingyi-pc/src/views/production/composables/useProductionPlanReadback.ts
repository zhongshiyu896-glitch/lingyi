export type ProductionPlanStatusTagType = 'success' | 'warning' | 'danger' | 'info'

export interface ProductionReadonlyGuardAction {
  label: string
  reason: string
}

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  planned: '已计划',
  material_checked: '已物料检查',
  work_order_pending: '工单待同步',
  work_order_created: '已创建工单',
  job_cards_synced: '工序卡已同步',
  cancelled: '已取消',
  failed: '失败',
  pending: '待同步',
  processing: '同步中',
  succeeded: '已同步',
  dead: '死信',
  blocked_scope: '范围阻断',
}

const STATUS_PROGRESS: Record<string, string> = {
  planned: '0%',
  material_checked: '35%',
  work_order_pending: '68%',
  work_order_created: '85%',
  job_cards_synced: '100%',
  cancelled: '0%',
  failed: '0%',
}

const PARITY_ROUTE_LABELS: Record<string, string> = {
  '': '主入口只读',
  'sample-list': '样衣计划镜像',
  'production-order': '订单计划镜像',
  'production-followup-template': '生产跟进镜像',
}

const READONLY_GUARD_ACTIONS: ProductionReadonlyGuardAction[] = [
  { label: '工单下发', reason: 'production write 冻结' },
  { label: '创建工单', reason: 'readonly guard' },
  { label: '同步工序卡', reason: 'outbox/worker 冻结' },
  { label: 'ERP 推送', reason: 'ERPNext production 冻结' },
]

export const useProductionPlanReadback = () => {
  const parseQueryString = (value: unknown): string => {
    const raw = Array.isArray(value) ? value[0] : value
    return typeof raw === 'string' ? raw.trim() : ''
  }

  const parityRouteLabel = (parity: string): string => PARITY_ROUTE_LABELS[parity] || '本地计划组'

  const groupLabel = (parity: string, company: string): string => {
    if (parity && PARITY_ROUTE_LABELS[parity]) return PARITY_ROUTE_LABELS[parity]
    return company === 'LY-LOCAL-TEST' ? '本地计划组' : company
  }

  const statusLabel = (status: string): string => STATUS_LABELS[status] || status

  const progressLabel = (status: string): string => STATUS_PROGRESS[status] || '0%'

  const statusType = (status: string): ProductionPlanStatusTagType => {
    if (status === 'work_order_created' || status === 'job_cards_synced') return 'success'
    if (status === 'failed') return 'danger'
    if (status === 'planned' || status === 'material_checked' || status === 'work_order_pending') return 'warning'
    return 'info'
  }

  return {
    groupLabel,
    parseQueryString,
    parityRouteLabel,
    progressLabel,
    readonlyGuardActions: READONLY_GUARD_ACTIONS,
    statusLabel,
    statusType,
  }
}
