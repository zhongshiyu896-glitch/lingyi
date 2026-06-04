import {
  fetchSubcontractOrderDetail,
  fetchSubcontractOrders,
  type SubcontractOrderDetailData,
  type SubcontractOrderListItem,
} from '@/api/subcontract'

export interface SubcontractReadonlyQuery {
  keyword?: string
  supplier?: string
  company?: string
  process_name?: string
  status?: string
  from_date?: string
  to_date?: string
  page: number
  page_size: number
}

export interface SubcontractReadonlySummary {
  filteredCount: number
  supplierCount: number
  plannedQty: number
  issuedQty: number
  receivedQty: number
  acceptedQty: number
  processingCount: number
  waitingReceiveCount: number
  waitingInspectionCount: number
  settlementReadyCount: number
  blockedCount: number
}

export interface SubcontractDetailReadonlySummary {
  receiptBatchCount: number
  inspectionCount: number
  remainingReceiptQty: number
  remainingAcceptanceQty: number
  receiptProgressRatio: string
  acceptanceProgressRatio: string
}

export type SubcontractTimelineStatus = 'pending' | 'active' | 'success' | 'blocked'
export type SubcontractSettlementReadonlyCode = 'pending' | 'ready' | 'locked' | 'blocked'

export interface SubcontractReadonlyTimelineMilestone {
  key: 'issue' | 'receipt' | 'inspection' | 'settlement'
  ownerRole: string
  occurredAt: string
  status: SubcontractTimelineStatus
  summary: string
  guardHint: string
}

export interface SubcontractSettlementReadonlyState {
  code: SubcontractSettlementReadonlyCode
  reason: string
  blockedNode: string
  acceptedQty: number
  netAmount: number
}

export interface SubcontractReadonlyAbnormalNode {
  key: string
  label: string
  ownerRole: string
  occurredAt: string
  status: SubcontractTimelineStatus
  reason: string
  actionHint: string
}

const normalizeString = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumber = (value?: string | number | null): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const hasFailureStatus = (value?: string | null): boolean => {
  const raw = normalizeString(value).toLowerCase()
  return ['failed', 'error', 'blocked'].includes(raw)
}

const resolveTimestamp = (...values: Array<string | null | undefined>): string => {
  for (const value of values) {
    const normalized = normalizeString(value)
    if (normalized) return normalized
  }
  return ''
}

const buildRowBlockedReason = (
  row: Pick<
    SubcontractOrderListItem,
    | 'profit_scope_error_code'
    | 'latest_receipt_error_code'
    | 'latest_issue_error_code'
    | 'latest_receipt_sync_status'
    | 'latest_issue_sync_status'
    | 'received_qty'
    | 'accepted_qty'
  >,
): string => {
  const profitScopeErrorCode = normalizeString(row.profit_scope_error_code)
  if (profitScopeErrorCode) return `利润范围阻断：${profitScopeErrorCode}`

  const receiptErrorCode = normalizeString(row.latest_receipt_error_code)
  if (receiptErrorCode) return `收货同步阻断：${receiptErrorCode}`

  const issueErrorCode = normalizeString(row.latest_issue_error_code)
  if (issueErrorCode) return `发料同步阻断：${issueErrorCode}`

  if (hasFailureStatus(row.latest_receipt_sync_status)) return '收货同步失败，结算链路保持只读阻断'
  if (hasFailureStatus(row.latest_issue_sync_status)) return '发料同步失败，时间线保持只读阻断'

  const receivedQty = toNumber(row.received_qty)
  const acceptedQty = toNumber(row.accepted_qty)
  if (receivedQty > acceptedQty) {
    return `仍有 ${receivedQty - acceptedQty} 待验货数量，结算只读状态保持阻断`
  }

  return ''
}

export const buildSubcontractSettlementReadonlyStateFromRow = (
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
): SubcontractSettlementReadonlyState => {
  const blockedReason = buildRowBlockedReason(row)
  const rawStatus = normalizeString(row.status).toLowerCase()
  const acceptedQty = toNumber(row.accepted_qty)
  const netAmount = toNumber(row.net_amount)

  if (blockedReason) {
    return {
      code: 'blocked',
      reason: blockedReason,
      blockedNode: blockedReason,
      acceptedQty,
      netAmount,
    }
  }

  if (rawStatus === 'completed') {
    return {
      code: 'locked',
      reason: '已完成委外单只保留结算观察，锁定与 release 动作冻结',
      blockedNode: '',
      acceptedQty,
      netAmount,
    }
  }

  if (acceptedQty > 0) {
    return {
      code: 'ready',
      reason: `已验收 ${acceptedQty}，满足只读结算观察条件，但结算动作冻结`,
      blockedNode: '',
      acceptedQty,
      netAmount,
    }
  }

  return {
    code: 'pending',
    reason: '待验货/待结算，当前只读模式不开放结算动作',
    blockedNode: '',
    acceptedQty,
    netAmount,
  }
}

const includesIgnoreCase = (source: unknown, target: string): boolean =>
  normalizeString(source).toLowerCase().includes(target.toLowerCase())

export const buildDefaultSubcontractReadonlyQuery = (): SubcontractReadonlyQuery => ({
  keyword: '',
  supplier: '',
  company: '',
  process_name: '',
  status: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

export const hasSubcontractReadonlyFilters = (query: SubcontractReadonlyQuery): boolean =>
  [
    query.keyword,
    query.supplier,
    query.company,
    query.process_name,
    query.status,
    query.from_date,
    query.to_date,
  ].some((value) => normalizeString(value).length > 0)

export const pickSubcontractServerQuery = (query: SubcontractReadonlyQuery) => ({
  supplier: normalizeString(query.supplier) || undefined,
  status: normalizeString(query.status) || undefined,
  from_date: normalizeString(query.from_date) || undefined,
  to_date: normalizeString(query.to_date) || undefined,
  page: query.page ?? 1,
  page_size: query.page_size ?? 20,
})

export const fetchSubcontractOrdersReadback = async (query: SubcontractReadonlyQuery) =>
  fetchSubcontractOrders(pickSubcontractServerQuery(query))

export const fetchSubcontractOrderDetailReadback = async (orderId: number) =>
  fetchSubcontractOrderDetail(orderId)

export const resolveFallbackSubcontractOrderRow = async (): Promise<SubcontractOrderListItem | null> => {
  try {
    const response = await fetchSubcontractOrders({ page: 1, page_size: 1 })
    return response.data.items?.[0] ?? null
  } catch {
    return null
  }
}

export const filterSubcontractRows = (
  rows: SubcontractOrderListItem[],
  query: SubcontractReadonlyQuery,
): SubcontractOrderListItem[] => {
  const keyword = normalizeString(query.keyword)
  const company = normalizeString(query.company)
  const processName = normalizeString(query.process_name)
  const status = normalizeString(query.status).toLowerCase()

  return rows.filter((row) => {
    if (
      keyword &&
      ![
        row.subcontract_no,
        row.supplier,
        row.item_code,
        row.company,
        row.sales_order,
        row.work_order,
        row.job_card,
      ].some((value) => includesIgnoreCase(value, keyword))
    ) {
      return false
    }
    if (company && !includesIgnoreCase(row.company, company)) {
      return false
    }
    if (processName && !includesIgnoreCase(row.process_name, processName)) {
      return false
    }
    if (status && normalizeString(row.status).toLowerCase() !== status) {
      return false
    }
    return true
  })
}

export const buildSubcontractReadonlySummary = (
  rows: SubcontractOrderListItem[],
): SubcontractReadonlySummary => {
  const suppliers = new Set<string>()
  let plannedQty = 0
  let issuedQty = 0
  let receivedQty = 0
  let acceptedQty = 0
  let processingCount = 0
  let waitingReceiveCount = 0
  let waitingInspectionCount = 0
  let settlementReadyCount = 0
  let blockedCount = 0

  rows.forEach((row) => {
    suppliers.add(normalizeString(row.supplier))
    plannedQty += toNumber(row.planned_qty)
    issuedQty += toNumber(row.issued_qty)
    receivedQty += toNumber(row.received_qty)
    acceptedQty += toNumber(row.accepted_qty)

    const status = normalizeString(row.status).toLowerCase()
    if (status === 'processing') processingCount += 1
    if (status === 'waiting_receive') waitingReceiveCount += 1
    if (status === 'waiting_inspection') waitingInspectionCount += 1

    const settlementState = buildSubcontractSettlementReadonlyStateFromRow(row)
    if (settlementState.code === 'ready') settlementReadyCount += 1
    if (settlementState.code === 'blocked') blockedCount += 1
  })

  return {
    filteredCount: rows.length,
    supplierCount: suppliers.size,
    plannedQty,
    issuedQty,
    receivedQty,
    acceptedQty,
    processingCount,
    waitingReceiveCount,
    waitingInspectionCount,
    settlementReadyCount,
    blockedCount,
  }
}

export const buildSubcontractDetailReadonlySummary = (
  detail: SubcontractOrderDetailData,
): SubcontractDetailReadonlySummary => {
  const plannedQty = toNumber(detail.planned_qty)
  const receivedQty = toNumber(detail.received_qty)
  const acceptedQty = toNumber(detail.accepted_qty)
  const remainingReceiptQty = Math.max(plannedQty - receivedQty, 0)
  const remainingAcceptanceQty = Math.max(receivedQty - acceptedQty, 0)

  return {
    receiptBatchCount: detail.receipts.length,
    inspectionCount: detail.inspections.length,
    remainingReceiptQty,
    remainingAcceptanceQty,
    receiptProgressRatio: plannedQty > 0 ? `${Math.round((receivedQty / plannedQty) * 100)}%` : '0%',
    acceptanceProgressRatio: receivedQty > 0 ? `${Math.round((acceptedQty / receivedQty) * 100)}%` : '0%',
  }
}

export const buildSubcontractReadonlyAbnormalNodes = (
  detail: SubcontractOrderDetailData,
): SubcontractReadonlyAbnormalNode[] => {
  const nodes: SubcontractReadonlyAbnormalNode[] = []
  const latestReceipt = detail.receipts[detail.receipts.length - 1]
  const latestInspection = detail.inspections[detail.inspections.length - 1]
  const receivedQty = toNumber(detail.received_qty)
  const acceptedQty = toNumber(detail.accepted_qty)

  const pushNode = (node: SubcontractReadonlyAbnormalNode) => {
    if (!nodes.some((item) => item.key === node.key)) nodes.push(node)
  }

  const receiptErrorCode = normalizeString(detail.latest_receipt_error_code)
  if (receiptErrorCode) {
    pushNode({
      key: 'receipt-sync',
      label: '收货同步阻断',
      ownerRole: '仓库收货',
      occurredAt: resolveTimestamp(latestReceipt?.received_at, detail.updated_at, detail.created_at),
      status: 'blocked',
      reason: receiptErrorCode,
      actionHint: '需核对收货同步结果；只读模式不释放重试或库存动作',
    })
  } else if (hasFailureStatus(detail.latest_receipt_sync_status)) {
    pushNode({
      key: 'receipt-sync',
      label: '收货同步阻断',
      ownerRole: '仓库收货',
      occurredAt: resolveTimestamp(latestReceipt?.received_at, detail.updated_at, detail.created_at),
      status: 'blocked',
      reason: normalizeString(detail.latest_receipt_sync_status) || 'failed',
      actionHint: '收货同步失败；只读模式保持阻断，不释放库存或 worker 链路',
    })
  }

  const profitScopeErrorCode = normalizeString(detail.profit_scope_error_code)
  if (profitScopeErrorCode) {
    pushNode({
      key: 'profit-scope',
      label: '利润范围阻断',
      ownerRole: '采购结算',
      occurredAt: resolveTimestamp(detail.updated_at, latestInspection?.inspected_at, detail.created_at),
      status: 'blocked',
      reason: profitScopeErrorCode,
      actionHint: '需先核对利润范围；只读模式不释放结算或导出动作',
    })
  }

  if (receivedQty > acceptedQty) {
    pushNode({
      key: 'inspection-pending',
      label: '验货待完成',
      ownerRole: '质检验货',
      occurredAt: resolveTimestamp(latestInspection?.inspected_at, latestReceipt?.received_at, detail.created_at),
      status: 'pending',
      reason: `仍有 ${receivedQty - acceptedQty} 待验货数量`,
      actionHint: '仅回读阻断节点和处理提示，不释放验货或结算动作',
    })
  }

  const issueErrorCode = normalizeString(detail.latest_issue_error_code)
  if (issueErrorCode || hasFailureStatus(detail.latest_issue_sync_status)) {
    pushNode({
      key: 'issue-sync',
      label: '发料同步阻断',
      ownerRole: '生产备料',
      occurredAt: resolveTimestamp(detail.updated_at, detail.created_at),
      status: 'blocked',
      reason: issueErrorCode || normalizeString(detail.latest_issue_sync_status) || 'failed',
      actionHint: '发料链路存在异常；当前页面仅展示阻断信息，不触发补发或 release',
    })
  }

  return nodes
}

export const buildSubcontractSettlementReadonlyState = (
  detail: SubcontractOrderDetailData,
): SubcontractSettlementReadonlyState => {
  const abnormalNodes = buildSubcontractReadonlyAbnormalNodes(detail)
  const rawStatus = normalizeString(detail.settlement_status).toLowerCase()
  const acceptedQty = toNumber(detail.accepted_qty)
  const netAmount = toNumber(detail.net_amount)

  if (abnormalNodes.some((node) => node.status === 'blocked')) {
    const blockedNode = abnormalNodes.find((node) => node.status === 'blocked')
    return {
      code: 'blocked',
      reason: blockedNode?.reason || '存在阻断节点，结算动作保持只读冻结',
      blockedNode: blockedNode?.label || '',
      acceptedQty,
      netAmount,
    }
  }

  if (['locked', 'settlement_locked', 'locked_readonly'].includes(rawStatus)) {
    return {
      code: 'locked',
      reason: '结算状态已锁定，当前页面只保留结果回读，不开放 release 或导出',
      blockedNode: '',
      acceptedQty,
      netAmount,
    }
  }

  if (acceptedQty > 0) {
    return {
      code: 'ready',
      reason: `已验收 ${acceptedQty}，满足只读结算观察条件，但结算动作冻结`,
      blockedNode: '',
      acceptedQty,
      netAmount,
    }
  }

  return {
    code: 'pending',
    reason: '待验货/待结算，当前只读模式不开放结算动作',
    blockedNode: '',
    acceptedQty,
    netAmount,
  }
}

export const buildSubcontractReadonlyTimelineMilestones = (
  detail: SubcontractOrderDetailData,
): SubcontractReadonlyTimelineMilestone[] => {
  const issuedQty = toNumber(detail.issued_qty)
  const receivedQty = toNumber(detail.received_qty)
  const acceptedQty = toNumber(detail.accepted_qty)
  const latestReceipt = detail.receipts[detail.receipts.length - 1]
  const latestInspection = detail.inspections[detail.inspections.length - 1]
  const settlementState = buildSubcontractSettlementReadonlyState(detail)
  const hasIssueFailure = Boolean(normalizeString(detail.latest_issue_error_code)) || hasFailureStatus(detail.latest_issue_sync_status)
  const hasReceiptFailure = Boolean(normalizeString(detail.latest_receipt_error_code)) || hasFailureStatus(detail.latest_receipt_sync_status)
  const inspectionPendingQty = Math.max(receivedQty - acceptedQty, 0)

  return [
    {
      key: 'issue',
      ownerRole: '生产备料',
      occurredAt: resolveTimestamp(detail.created_at),
      status: hasIssueFailure ? 'blocked' : issuedQty > 0 ? 'success' : 'pending',
      summary: `发料 ${issuedQty} / 计划 ${toNumber(detail.planned_qty)}`,
      guardHint: hasIssueFailure
        ? '发料同步存在异常，当前页面仅回读阻断状态，不释放补发或库存链路'
        : issuedQty > 0
          ? '基础发料节点已回读，后续只读观察收货与验货流转'
          : '待发料节点仅展示，不释放任何写动作',
    },
    {
      key: 'receipt',
      ownerRole: normalizeString(latestReceipt?.received_by) || '仓库收货',
      occurredAt: resolveTimestamp(latestReceipt?.received_at, detail.updated_at, detail.created_at),
      status: hasReceiptFailure
        ? 'blocked'
        : receivedQty >= issuedQty && issuedQty > 0
          ? 'success'
          : receivedQty > 0
            ? 'active'
            : 'pending',
      summary: `回料 ${receivedQty} / 发料 ${issuedQty}`,
      guardHint:
        receivedQty >= issuedQty && issuedQty > 0
          ? '收货时间线已闭环，但收货写动作继续冻结'
          : `仍有 ${Math.max(issuedQty - receivedQty, 0)} 待回料数量，收货动作保持只读`,
    },
    {
      key: 'inspection',
      ownerRole: normalizeString(latestInspection?.inspected_by) || '质检验货',
      occurredAt: resolveTimestamp(latestInspection?.inspected_at, latestReceipt?.received_at, detail.created_at),
      status:
        inspectionPendingQty > 0
          ? 'active'
          : acceptedQty >= receivedQty && receivedQty > 0
            ? 'success'
            : receivedQty > 0
              ? 'active'
              : 'pending',
      summary: `验收 ${acceptedQty} / 回料 ${receivedQty} / 不良 ${toNumber(detail.rejected_qty)}`,
      guardHint: inspectionPendingQty === 0 && acceptedQty >= receivedQty && receivedQty > 0
        ? '验货节点已完成，但验货与后续结算动作继续冻结'
        : `仍有 ${inspectionPendingQty} 待验货数量，当前只读模式仅展示阻断提示`,
    },
    {
      key: 'settlement',
      ownerRole: '采购结算',
      occurredAt: resolveTimestamp(detail.updated_at, latestInspection?.inspected_at, detail.created_at),
      status:
        settlementState.code === 'blocked'
          ? 'blocked'
          : settlementState.code === 'locked'
            ? 'success'
            : settlementState.code === 'ready'
              ? 'active'
              : 'pending',
      summary: `净额 ${netAmountLabel(detail.net_amount)} / 验收 ${acceptedQty}`,
      guardHint: settlementState.reason,
    },
  ]
}

const netAmountLabel = (value?: string | number | null): string => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toLocaleString('zh-CN', { maximumFractionDigits: 2 }) : '0'
}
