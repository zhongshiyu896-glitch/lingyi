import type { SubcontractOrderDetailData, SubcontractOrderListItem } from '@/api/subcontract'
import {
  buildSubcontractDetailReadonlySummary,
  buildSubcontractReadonlyAbnormalNodes,
  buildSubcontractReadonlyScopeBridgeFromDetail,
  buildSubcontractReadonlyScopeBridgeListSummary,
  buildSubcontractReadonlyTimelineMilestones,
  buildSubcontractSettlementReadonlyState,
  buildSubcontractSettlementReadonlyStateFromRow,
  type SubcontractReadonlyAbnormalNode,
  type SubcontractReadonlyScopeBridgeField,
  type SubcontractReadonlyScopeBridgeMaterialTag,
  type SubcontractReadonlyScopeBridgeSummary,
  type SubcontractReadonlyTimelineMilestone,
  type SubcontractSettlementReadonlyState,
} from '@/api/subcontract_readback'
import {
  SUBCONTRACT_MILESTONE_LABELS,
  SUBCONTRACT_SETTLEMENT_LABELS,
  SUBCONTRACT_SETTLEMENT_TAGS,
  SUBCONTRACT_TIMELINE_STATUS_LABELS,
  SUBCONTRACT_TIMELINE_STATUS_TAGS,
} from '../constants/subcontractMilestoneFields'
import {
  SUBCONTRACT_SCOPE_BRIDGE_FIELD_LABELS,
  SUBCONTRACT_SCOPE_BRIDGE_STATUS_LABELS,
  SUBCONTRACT_SCOPE_BRIDGE_STATUS_TAGS,
} from '../constants/subcontractScopeBridgeFields'

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

export interface SubcontractTimelineMilestoneView extends SubcontractReadonlyTimelineMilestone {
  label: string
  statusLabel: string
  statusType: SubcontractTagType
}

export interface SubcontractSettlementReadonlyView extends SubcontractSettlementReadonlyState {
  label: string
  type: SubcontractTagType
  acceptedQtyLabel: string
  netAmountLabel: string
}

export interface SubcontractAbnormalNodeView extends SubcontractReadonlyAbnormalNode {
  statusLabel: string
  statusType: SubcontractTagType
}

export interface SubcontractScopeBridgeFieldView extends SubcontractReadonlyScopeBridgeField {
  label: string
}

export interface SubcontractScopeBridgeMaterialTagView extends SubcontractReadonlyScopeBridgeMaterialTag {
  type: SubcontractTagType
}

export interface SubcontractScopeBridgeReadonlyView
  extends Omit<SubcontractReadonlyScopeBridgeSummary, 'bridgeCode' | 'mappingFields' | 'materialTags'> {
  bridgeStatusLabel: string
  bridgeStatusType: SubcontractTagType
  profitScopeLabel: string
  profitScopeType: SubcontractTagType
  resourceScopeLabel: string
  resourceScopeType: SubcontractTagType
  mappingFields: SubcontractScopeBridgeFieldView[]
  materialTags: SubcontractScopeBridgeMaterialTagView[]
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
  { label: '发料', reason: 'issue-material 冻结' },
  { label: '收货', reason: 'receive 冻结' },
  { label: '结算', reason: 'settlement lock/release 冻结' },
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

  const settlementReadonlyLabelFromCode = (code: SubcontractSettlementReadonlyState['code']): string =>
    SUBCONTRACT_SETTLEMENT_LABELS[code]

  const settlementReadonlyTypeFromCode = (code: SubcontractSettlementReadonlyState['code']): SubcontractTagType =>
    SUBCONTRACT_SETTLEMENT_TAGS[code]

  const settlementReadonlyState = (detail: SubcontractOrderDetailData): SubcontractSettlementReadonlyView => {
    const state = buildSubcontractSettlementReadonlyState(detail)
    return {
      ...state,
      label: settlementReadonlyLabelFromCode(state.code),
      type: settlementReadonlyTypeFromCode(state.code),
      acceptedQtyLabel: toNumberLabel(state.acceptedQty),
      netAmountLabel: toNumberLabel(state.netAmount, 2),
    }
  }

  const settlementReadonlyLabel = (
    row: Pick<
      SubcontractOrderListItem,
      | 'accepted_qty'
      | 'net_amount'
      | 'status'
      | 'profit_scope_error_code'
      | 'latest_receipt_error_code'
      | 'latest_issue_error_code'
      | 'latest_receipt_sync_status'
      | 'latest_issue_sync_status'
      | 'received_qty'
    >,
  ): string => settlementReadonlyLabelFromCode(buildSubcontractSettlementReadonlyStateFromRow(row).code)

  const settlementReadonlyType = (
    row: Pick<
      SubcontractOrderListItem,
      | 'accepted_qty'
      | 'net_amount'
      | 'status'
      | 'profit_scope_error_code'
      | 'latest_receipt_error_code'
      | 'latest_issue_error_code'
      | 'latest_receipt_sync_status'
      | 'latest_issue_sync_status'
      | 'received_qty'
    >,
  ): SubcontractTagType => settlementReadonlyTypeFromCode(buildSubcontractSettlementReadonlyStateFromRow(row).code)

  const settlementReadonlyReason = (
    row: Pick<
      SubcontractOrderListItem,
      | 'accepted_qty'
      | 'net_amount'
      | 'status'
      | 'profit_scope_error_code'
      | 'latest_receipt_error_code'
      | 'latest_issue_error_code'
      | 'latest_receipt_sync_status'
      | 'latest_issue_sync_status'
      | 'received_qty'
    >,
  ): string => buildSubcontractSettlementReadonlyStateFromRow(row).reason

  const timelineMilestones = (detail: SubcontractOrderDetailData): SubcontractTimelineMilestoneView[] =>
    buildSubcontractReadonlyTimelineMilestones(detail).map((milestone) => ({
      ...milestone,
      label: SUBCONTRACT_MILESTONE_LABELS[milestone.key],
      statusLabel: SUBCONTRACT_TIMELINE_STATUS_LABELS[milestone.status],
      statusType: SUBCONTRACT_TIMELINE_STATUS_TAGS[milestone.status],
      occurredAt: formatDateTimeTime(milestone.occurredAt),
    }))

  const abnormalNodes = (detail: SubcontractOrderDetailData): SubcontractAbnormalNodeView[] => {
    const nodes = buildSubcontractReadonlyAbnormalNodes(detail)
    if (nodes.length === 0) {
      return [
        {
          key: 'readonly-observer',
          label: '异常节点观察',
          ownerRole: '只读守卫',
          occurredAt: formatDateTimeTime(detail.updated_at || detail.created_at),
          status: 'success',
          reason: '当前未识别阻断异常，链路保持只读观察。',
          actionHint: '收货、验货、结算与导出动作继续冻结，不释放真实写链路。',
          statusLabel: SUBCONTRACT_TIMELINE_STATUS_LABELS.success,
          statusType: SUBCONTRACT_TIMELINE_STATUS_TAGS.success,
        },
      ]
    }
    return nodes.map((node) => ({
      ...node,
      occurredAt: formatDateTimeTime(node.occurredAt),
      statusLabel: SUBCONTRACT_TIMELINE_STATUS_LABELS[node.status],
      statusType: SUBCONTRACT_TIMELINE_STATUS_TAGS[node.status],
    }))
  }

  const toScopeBridgeView = (
    summary: SubcontractReadonlyScopeBridgeSummary,
  ): SubcontractScopeBridgeReadonlyView => {
    const bridgeStatusType = SUBCONTRACT_SCOPE_BRIDGE_STATUS_TAGS[summary.bridgeCode]
    return {
      ...summary,
      bridgeStatusLabel: SUBCONTRACT_SCOPE_BRIDGE_STATUS_LABELS[summary.bridgeCode],
      bridgeStatusType,
      profitScopeLabel: profitScopeLabel(summary.profitScopeStatus),
      profitScopeType: profitScopeType(summary.profitScopeStatus),
      resourceScopeLabel: resourceScopeLabel(summary.resourceScopeStatus),
      resourceScopeType: resourceScopeType(summary.resourceScopeStatus),
      mappingFields: summary.mappingFields.map((field) => ({
        ...field,
        label: SUBCONTRACT_SCOPE_BRIDGE_FIELD_LABELS[field.key],
      })),
      materialTags: summary.materialTags.map((tag) => ({
        ...tag,
        type: bridgeStatusType,
      })),
    }
  }

  const scopeBridgeDetailSummary = (
    detail: SubcontractOrderDetailData,
    parityToken = '',
  ): SubcontractScopeBridgeReadonlyView =>
    toScopeBridgeView(buildSubcontractReadonlyScopeBridgeFromDetail(detail, parityToken))

  const scopeBridgeListSummary = (
    rows: SubcontractOrderListItem[],
    parityToken = '',
  ): SubcontractScopeBridgeReadonlyView | null =>
    rows.length > 0 ? toScopeBridgeView(buildSubcontractReadonlyScopeBridgeListSummary(rows, parityToken)) : null

  const scopeGuardStates = (summary: SubcontractScopeBridgeReadonlyView | null): SubcontractGuardState[] => {
    if (!summary) return []
    const blocked = summary.bridgeStatusType === 'danger'
    const pending = summary.bridgeStatusType === 'warning'
    return [
      {
        label: '发料',
        reason: blocked
          ? summary.deviationHint
          : '当前切片仅回读桥接状态，不开放发料、补发或 release 链路',
        type: blocked ? 'danger' : pending ? 'warning' : 'info',
      },
      {
        label: '收货',
        reason: summary.readonlyReason,
        type: blocked ? 'danger' : pending ? 'warning' : 'info',
      },
      {
        label: '结算',
        reason: blocked
          ? `${summary.deviationHint}；结算锁定与 release 保持冻结`
          : '利润范围只保留观察，结算锁定、release 与导出动作继续冻结',
        type: blocked ? 'danger' : pending ? 'warning' : 'info',
      },
      {
        label: '导出',
        reason: 'export 冻结',
        type: 'info',
      },
      {
        label: '库存影响',
        reason: `来源 ${summary.dataSource}；inventory impact 冻结`,
        type: blocked ? 'danger' : 'warning',
      },
    ]
  }

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

  const formatDateTimeTime = (value?: string | null): string => {
    const raw = normalizeString(value)
    if (!raw) return '-'
    const date = new Date(raw)
    if (Number.isNaN(date.getTime())) return raw
    return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')} ${String(date.getHours()).padStart(2, '0')}:${String(date.getMinutes()).padStart(2, '0')}`
  }

  return {
    abnormalNodes,
    buildReceiptPreconditionGuard,
    detailSummary,
    formatDateTime,
    formatDateTimeTime,
    formatNumber: toNumberLabel,
    profitScopeLabel,
    profitScopeType,
    progressStageLabel,
    progressStageType,
    readonlyGuardActions: READONLY_GUARD_ACTIONS,
    resourceScopeLabel,
    resourceScopeType,
    scopeBridgeDetailSummary,
    scopeBridgeListSummary,
    scopeGuardStates,
    settlementReadonlyLabel,
    settlementReadonlyReason,
    settlementReadonlyState,
    settlementReadonlyType,
    statusLabel,
    statusType,
    timelineMilestones,
  }
}
