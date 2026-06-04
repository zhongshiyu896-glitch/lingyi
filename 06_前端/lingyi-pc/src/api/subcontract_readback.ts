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

export type SubcontractScopeBridgeCode = 'ready' | 'pending' | 'blocked'
export type SubcontractScopeBridgeFieldKey =
  | 'sales_order'
  | 'sales_order_item'
  | 'production_plan_id'
  | 'work_order'
  | 'job_card'

export interface SubcontractReadonlyScopeBridgeField {
  key: SubcontractScopeBridgeFieldKey
  value: string
  hint: string
}

export interface SubcontractReadonlyScopeBridgeMaterialTag {
  key: string
  label: string
  value: string
  hint: string
}

export interface SubcontractReadonlyScopeBridgeSummary {
  bridgeCode: SubcontractScopeBridgeCode
  dataSource: string
  readonlyReason: string
  deviationHint: string
  bridgeSummary: string
  profitScopeStatus: string
  resourceScopeStatus: string
  profitScopeErrorCode: string
  mappingFields: SubcontractReadonlyScopeBridgeField[]
  materialTags: SubcontractReadonlyScopeBridgeMaterialTag[]
  readyCount?: number
  pendingCount?: number
  blockedCount?: number
  mappedCount?: number
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

type SubcontractScopeBridgeSource = Pick<
  SubcontractOrderListItem,
  | 'item_code'
  | 'company'
  | 'process_name'
  | 'sales_order'
  | 'sales_order_item'
  | 'production_plan_id'
  | 'work_order'
  | 'job_card'
  | 'resource_scope_status'
  | 'profit_scope_status'
  | 'profit_scope_error_code'
> &
  Partial<
    Pick<
      SubcontractOrderDetailData,
      'receipts' | 'inspections' | 'accepted_qty' | 'received_qty' | 'planned_qty' | 'subcontract_no'
    >
  >

const hasScopeBridgeMapping = (source: SubcontractScopeBridgeSource): boolean =>
  Boolean(
    normalizeString(source.sales_order) ||
      normalizeString(source.sales_order_item) ||
      normalizeString(source.work_order) ||
      normalizeString(source.job_card) ||
      source.production_plan_id,
  )

const resolveScopeBridgeCode = (source: SubcontractScopeBridgeSource): SubcontractScopeBridgeCode => {
  const profitScopeErrorCode = normalizeString(source.profit_scope_error_code)
  const resourceScopeStatus = normalizeString(source.resource_scope_status).toLowerCase()
  const profitScopeStatus = normalizeString(source.profit_scope_status).toLowerCase()

  if (profitScopeErrorCode || resourceScopeStatus === 'blocked' || profitScopeStatus === 'blocked') return 'blocked'
  if (['ready', 'resolved'].includes(profitScopeStatus) && hasScopeBridgeMapping(source)) return 'ready'
  return 'pending'
}

const resolveScopeBridgeDataSource = (source: SubcontractScopeBridgeSource, parityToken = ''): string => {
  if (parityToken === 'material-purchase') return 'materialPurchase parity / subcontract readonly snapshot'
  if (hasScopeBridgeMapping(source)) return 'subcontract readonly snapshot / sales-production bridge'
  return 'subcontract readonly snapshot'
}

const resolveScopeBridgeReadonlyReason = (
  source: SubcontractScopeBridgeSource,
  parityToken = '',
): string => {
  const code = resolveScopeBridgeCode(source)
  if (code === 'blocked') {
    return '利润范围或资源范围存在阻断，当前只读模式继续冻结收货、发料、结算、导出与库存链路。'
  }
  if (code === 'pending') {
    return parityToken === 'material-purchase'
      ? 'materialPurchase parity 仅提供桥接观察；桥接字段待核对时不释放收货、发料或结算动作。'
      : '桥接字段待核对，当前只提供来源观察与只读守卫，不释放任何真实采购或库存动作。'
  }
  return '桥接来源已对齐，当前页面仍只保留只读观察，不释放真实采购、库存、结算或导出链路。'
}

const resolveScopeBridgeDeviationHint = (source: SubcontractScopeBridgeSource): string => {
  const profitScopeErrorCode = normalizeString(source.profit_scope_error_code)
  const resourceScopeStatus = normalizeString(source.resource_scope_status).toLowerCase()
  if (profitScopeErrorCode) return `利润范围偏离：${profitScopeErrorCode}`
  if (!hasScopeBridgeMapping(source)) return '缺少销售订单/工单桥接，利润范围保持待核对。'
  if (resourceScopeStatus && resourceScopeStatus !== 'ready') return '资源范围未完全就绪，当前仅回读桥接状态。'
  return '利润范围与物料桥接已对齐，仅做只读观察。'
}

const buildScopeBridgeMappings = (
  source: SubcontractScopeBridgeSource,
): SubcontractReadonlyScopeBridgeField[] => [
  {
    key: 'sales_order',
    value: normalizeString(source.sales_order) || '-',
    hint: '委外单桥接的销售订单只读来源',
  },
  {
    key: 'sales_order_item',
    value: normalizeString(source.sales_order_item) || '-',
    hint: '销售订单行回读映射',
  },
  {
    key: 'production_plan_id',
    value: source.production_plan_id ? String(source.production_plan_id) : '-',
    hint: '生产计划桥接只读快照',
  },
  {
    key: 'work_order',
    value: normalizeString(source.work_order) || '-',
    hint: '工单桥接只读映射',
  },
  {
    key: 'job_card',
    value: normalizeString(source.job_card) || '-',
    hint: '工序卡桥接只读映射',
  },
]

const buildScopeBridgeMaterialTags = (
  source: SubcontractScopeBridgeSource,
): SubcontractReadonlyScopeBridgeMaterialTag[] => {
  const tags: SubcontractReadonlyScopeBridgeMaterialTag[] = [
    {
      key: 'item_code',
      label: '主物料',
      value: normalizeString(source.item_code) || '-',
      hint: '委外主物料只读回读',
    },
    {
      key: 'process_name',
      label: '工序',
      value: normalizeString(source.process_name) || '-',
      hint: '委外工序桥接来源',
    },
    {
      key: 'company',
      label: '公司',
      value: normalizeString(source.company) || '-',
      hint: '业务主体范围',
    },
  ]

  if (normalizeString(source.sales_order_item)) {
    tags.push({
      key: 'sales_order_item',
      label: '来源行',
      value: normalizeString(source.sales_order_item),
      hint: '销售订单行桥接已回读',
    })
  }

  if (Array.isArray(source.receipts)) {
    tags.push({
      key: 'receipt_batches',
      label: '收货批次',
      value: String(source.receipts.length),
      hint: '收货时间线只读快照',
    })
  }

  if (Array.isArray(source.inspections)) {
    tags.push({
      key: 'inspection_records',
      label: '验货记录',
      value: String(source.inspections.length),
      hint: '验货节点只读回读',
    })
  }

  return tags
}

const buildScopeBridgeSummaryText = (source: SubcontractScopeBridgeSource): string => {
  const salesOrder = normalizeString(source.sales_order) || '-'
  const workOrder = normalizeString(source.work_order) || '-'
  const productionPlan = source.production_plan_id ? String(source.production_plan_id) : '-'
  const processName = normalizeString(source.process_name) || '-'
  return `销售 ${salesOrder} / 工单 ${workOrder} / 计划 ${productionPlan} / 工序 ${processName}`
}

export const buildSubcontractReadonlyScopeBridgeFromRow = (
  row: Pick<
    SubcontractOrderListItem,
    | 'item_code'
    | 'company'
    | 'process_name'
    | 'sales_order'
    | 'sales_order_item'
    | 'production_plan_id'
    | 'work_order'
    | 'job_card'
    | 'resource_scope_status'
    | 'profit_scope_status'
    | 'profit_scope_error_code'
  >,
  parityToken = '',
): SubcontractReadonlyScopeBridgeSummary => ({
  bridgeCode: resolveScopeBridgeCode(row),
  dataSource: resolveScopeBridgeDataSource(row, parityToken),
  readonlyReason: resolveScopeBridgeReadonlyReason(row, parityToken),
  deviationHint: resolveScopeBridgeDeviationHint(row),
  bridgeSummary: buildScopeBridgeSummaryText(row),
  profitScopeStatus: normalizeString(row.profit_scope_status) || 'pending',
  resourceScopeStatus: normalizeString(row.resource_scope_status) || 'pending',
  profitScopeErrorCode: normalizeString(row.profit_scope_error_code),
  mappingFields: buildScopeBridgeMappings(row),
  materialTags: buildScopeBridgeMaterialTags(row),
})

export const buildSubcontractReadonlyScopeBridgeFromDetail = (
  detail: Pick<
    SubcontractOrderDetailData,
    | 'item_code'
    | 'company'
    | 'process_name'
    | 'sales_order'
    | 'sales_order_item'
    | 'production_plan_id'
    | 'work_order'
    | 'job_card'
    | 'resource_scope_status'
    | 'profit_scope_status'
    | 'profit_scope_error_code'
    | 'receipts'
    | 'inspections'
    | 'accepted_qty'
    | 'received_qty'
    | 'planned_qty'
    | 'subcontract_no'
  >,
  parityToken = '',
): SubcontractReadonlyScopeBridgeSummary => ({
  bridgeCode: resolveScopeBridgeCode(detail),
  dataSource: resolveScopeBridgeDataSource(detail, parityToken),
  readonlyReason: resolveScopeBridgeReadonlyReason(detail, parityToken),
  deviationHint: resolveScopeBridgeDeviationHint(detail),
  bridgeSummary: buildScopeBridgeSummaryText(detail),
  profitScopeStatus: normalizeString(detail.profit_scope_status) || 'pending',
  resourceScopeStatus: normalizeString(detail.resource_scope_status) || 'pending',
  profitScopeErrorCode: normalizeString(detail.profit_scope_error_code),
  mappingFields: buildScopeBridgeMappings(detail),
  materialTags: buildScopeBridgeMaterialTags(detail),
})

export const buildSubcontractReadonlyScopeBridgeListSummary = (
  rows: SubcontractOrderListItem[],
  parityToken = '',
): SubcontractReadonlyScopeBridgeSummary => {
  let readyCount = 0
  let pendingCount = 0
  let blockedCount = 0
  let mappedCount = 0

  const rowWithPriority =
    rows.find((row) => resolveScopeBridgeCode(row) === 'blocked') ||
    rows.find((row) => resolveScopeBridgeCode(row) === 'pending') ||
    rows[0]

  rows.forEach((row) => {
    const bridgeCode = resolveScopeBridgeCode(row)
    if (bridgeCode === 'ready') readyCount += 1
    if (bridgeCode === 'pending') pendingCount += 1
    if (bridgeCode === 'blocked') blockedCount += 1
    if (hasScopeBridgeMapping(row)) mappedCount += 1
  })

  const summary = buildSubcontractReadonlyScopeBridgeFromRow(rowWithPriority, parityToken)
  return {
    ...summary,
    bridgeSummary: `桥接就绪 ${readyCount} / 待核对 ${pendingCount} / 阻断 ${blockedCount}`,
    materialTags: [
      ...summary.materialTags,
      {
        key: 'filtered_count',
        label: '筛选单数',
        value: String(rows.length),
        hint: '当前只读结果集',
      },
    ],
    readyCount,
    pendingCount,
    blockedCount,
    mappedCount,
  }
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
