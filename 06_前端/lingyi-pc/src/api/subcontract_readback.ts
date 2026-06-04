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
}

export interface SubcontractDetailReadonlySummary {
  receiptBatchCount: number
  inspectionCount: number
  remainingReceiptQty: number
  remainingAcceptanceQty: number
  receiptProgressRatio: string
  acceptanceProgressRatio: string
}

const normalizeString = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumber = (value?: string | number | null): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
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
