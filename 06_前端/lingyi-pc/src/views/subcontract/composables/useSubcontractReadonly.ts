import type { SubcontractOrderDetailData, SubcontractOrderListItem } from '@/api/subcontract'
import { buildSubcontractDetailReadonlySummary } from '@/api/subcontract_readback'

export type SubcontractTagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

export interface SubcontractReadonlyGuardAction {
  label: string
  reason: string
}

export interface SubcontractGuardState {
  label: string
  reason: string
  type: SubcontractTagType
}

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿待核对',
  issued: '已发料',
  processing: '加工中',
  waiting_receive: '待收货',
  waiting_inspection: '待验货',
  completed: '已完成',
  cancelled: '已取消',
}

const STATUS_TYPES: Record<string, SubcontractTagType> = {
  draft: 'info',
  issued: 'primary',
  processing: 'warning',
  waiting_receive: 'warning',
  waiting_inspection: 'primary',
  completed: 'success',
  cancelled: 'info',
}

const RESOURCE_SCOPE_LABELS: Record<string, string> = {
  ready: '资源范围就绪',
  pending: '资源范围待核对',
  blocked: '资源范围阻塞',
}

const RESOURCE_SCOPE_TYPES: Record<string, SubcontractTagType> = {
  ready: 'success',
  pending: 'warning',
  blocked: 'danger',
}

const PROFIT_SCOPE_LABELS: Record<string, string> = {
  resolved: '利润范围已对齐',
  pending: '利润范围待核对',
  blocked: '利润范围阻塞',
}

const PROFIT_SCOPE_TYPES: Record<string, SubcontractTagType> = {
  resolved: 'success',
  pending: 'warning',
  blocked: 'danger',
}

const READONLY_GUARD_ACTIONS: SubcontractReadonlyGuardAction[] = [
  { label: '收货', reason: 'readonly guard' },
  { label: '入库', reason: 'inventory impact 冻结' },
  { label: '取消', reason: 'write action 冻结' },
  { label: '导出', reason: 'export 冻结' },
  { label: '库存影响', reason: 'stock effect 冻结' },
]

const normalizeString = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumber = (value?: string | number | null): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const toNumberLabel = (value?: string | number | null, digits = 0): string => {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return String(value)
  return numeric.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits === 0 ? 2 : digits,
  })
}

export const useSubcontractReadonly = () => {
  const statusLabel = (status?: string | null): string => {
    const raw = normalizeString(status).toLowerCase()
    return STATUS_LABELS[raw] || raw || '未标记'
  }

  const statusType = (status?: string | null): SubcontractTagType => {
    const raw = normalizeString(status).toLowerCase()
    return STATUS_TYPES[raw] || 'info'
  }

  const resourceScopeLabel = (status?: string | null): string => {
    const raw = normalizeString(status).toLowerCase()
    return RESOURCE_SCOPE_LABELS[raw] || raw || '未标记'
  }

  const resourceScopeType = (status?: string | null): SubcontractTagType => {
    const raw = normalizeString(status).toLowerCase()
    return RESOURCE_SCOPE_TYPES[raw] || 'info'
  }

  const profitScopeLabel = (status?: string | null): string => {
    const raw = normalizeString(status).toLowerCase()
    return PROFIT_SCOPE_LABELS[raw] || raw || '未标记'
  }

  const profitScopeType = (status?: string | null): SubcontractTagType => {
    const raw = normalizeString(status).toLowerCase()
    return PROFIT_SCOPE_TYPES[raw] || 'info'
  }

  const progressStageLabel = (row: Pick<SubcontractOrderListItem, 'status' | 'planned_qty' | 'issued_qty' | 'received_qty' | 'accepted_qty'>): string => {
    const plannedQty = toNumber(row.planned_qty)
    const issuedQty = toNumber(row.issued_qty)
    const receivedQty = toNumber(row.received_qty)
    const acceptedQty = toNumber(row.accepted_qty)
    const status = normalizeString(row.status).toLowerCase()

    if (status === 'waiting_receive' || issuedQty > receivedQty) return '待收货'
    if (status === 'waiting_inspection' || receivedQty > acceptedQty) return '待验货'
    if (status === 'processing' || issuedQty > 0) return '加工中'
    if (acceptedQty >= plannedQty && plannedQty > 0) return '已验收'
    return '待发料'
  }

  const progressStageType = (row: Pick<SubcontractOrderListItem, 'status' | 'planned_qty' | 'issued_qty' | 'received_qty' | 'accepted_qty'>): SubcontractTagType => {
    const stage = progressStageLabel(row)
    if (stage === '已验收') return 'success'
    if (stage === '待收货' || stage === '待验货') return 'warning'
    if (stage === '加工中') return 'primary'
    return 'info'
  }

  const detailSummary = (detail: SubcontractOrderDetailData) =>
    buildSubcontractDetailReadonlySummary(detail)

  const buildReceiptPreconditionGuard = (detail: SubcontractOrderDetailData): SubcontractGuardState[] => {
    const plannedQty = toNumber(detail.planned_qty)
    const issuedQty = toNumber(detail.issued_qty)
    const receivedQty = toNumber(detail.received_qty)
    const acceptedQty = toNumber(detail.accepted_qty)
    const remainingReceiptQty = Math.max(plannedQty - receivedQty, 0)
    const remainingAcceptanceQty = Math.max(receivedQty - acceptedQty, 0)

    return [
      {
        label: '收货',
        reason:
          issuedQty > receivedQty
            ? `仍有 ${toNumberLabel(issuedQty - receivedQty)} 待回料；当前只读模式不释放收货动作`
            : '当前无待回料数量，收货动作保持只读禁用',
        type: issuedQty > receivedQty ? 'warning' : 'info',
      },
      {
        label: '入库',
        reason:
          acceptedQty > 0
            ? `已回读 ${toNumberLabel(acceptedQty)} 合格数量，但库存入库链路冻结`
            : `待验货数量 ${toNumberLabel(remainingAcceptanceQty)}，入库前置条件未满足`,
        type: acceptedQty > 0 ? 'warning' : 'info',
      },
      {
        label: '取消',
        reason: normalizeString(detail.status).toLowerCase() === 'completed' ? '已完成单据不可取消' : 'write action 冻结',
        type: 'info',
      },
      {
        label: '导出',
        reason: 'export 冻结',
        type: 'info',
      },
      {
        label: '库存影响',
        reason:
          remainingReceiptQty > 0
            ? `剩余 ${toNumberLabel(remainingReceiptQty)} 未收货；库存影响链路冻结`
            : 'inventory impact 冻结',
        type: 'danger',
      },
    ]
  }

  const formatDateTime = (value?: string | null): string => {
    const raw = normalizeString(value)
    if (!raw) return '-'
    const date = new Date(raw)
    if (Number.isNaN(date.getTime())) return raw
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
  }

  return {
    buildReceiptPreconditionGuard,
    detailSummary,
    formatDateTime,
    formatNumber: toNumberLabel,
    profitScopeLabel,
    profitScopeType,
    progressStageLabel,
    progressStageType,
    readonlyGuardActions: READONLY_GUARD_ACTIONS,
    resourceScopeLabel,
    resourceScopeType,
    statusLabel,
    statusType,
  }
}
