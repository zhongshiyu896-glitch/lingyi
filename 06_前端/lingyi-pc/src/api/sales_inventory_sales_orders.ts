import {
  fetchSalesInventorySalesOrderDetail,
  fetchSalesInventorySalesOrders,
  type SalesInventoryListQuery,
  type SalesOrderDetailData,
  type SalesOrderListItem,
} from '@/api/sales_inventory'

export type SalesOrderReadonlyGroup = 'draft-watch' | 'delivery-followup' | 'closed'

export interface SalesOrderReadbackQuery extends SalesInventoryListQuery {
  status?: string
  followup_group?: string
}

export interface SalesOrderReadonlySummary {
  filteredCount: number
  draftCount: number
  deliveryCount: number
  closedCount: number
  customerCount: number
  totalAmount: number
}

export interface SalesOrderDetailReadonlySummary {
  itemCount: number
  totalOrderedQty: number
  deliveredQty: number
  remainingQty: number
  primaryItemCode: string
  primaryItemName: string
  deliveryCompletionRatio: string
}

const toNumber = (value?: string | number | null): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const normalizeValue = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

export const resolveSalesOrderReadonlyGroup = (
  row: Pick<SalesOrderListItem, 'status' | 'docstatus'>,
): SalesOrderReadonlyGroup => {
  const status = normalizeValue(row.status).toLowerCase()
  if (status === 'draft' || status === 'to bill' || row.docstatus === 0) {
    return 'draft-watch'
  }
  if (status === 'completed' || status === 'cancelled') {
    return 'closed'
  }
  return 'delivery-followup'
}

export const pickSalesOrderServerQuery = (
  query: SalesOrderReadbackQuery,
): SalesInventoryListQuery => ({
  order_no: normalizeValue(query.order_no),
  keyword: normalizeValue(query.keyword),
  company: normalizeValue(query.company),
  customer: normalizeValue(query.customer),
  item_code: normalizeValue(query.item_code),
  item_name: normalizeValue(query.item_name),
  from_date: normalizeValue(query.from_date),
  to_date: normalizeValue(query.to_date),
  page: query.page ?? 1,
  page_size: query.page_size ?? 20,
})

export const fetchSalesInventorySalesOrdersReadback = async (
  query: SalesOrderReadbackQuery,
) => fetchSalesInventorySalesOrders(pickSalesOrderServerQuery(query))

export const fetchSalesInventorySalesOrderDetailReadback = async (name: string) =>
  fetchSalesInventorySalesOrderDetail(name)

export const resolveFallbackSalesOrderName = async (): Promise<string> => {
  const response = await fetchSalesInventorySalesOrders({ page: 1, page_size: 1 })
  return response.data.items[0]?.name || ''
}

export const filterSalesOrderRows = (
  rows: SalesOrderListItem[],
  query: SalesOrderReadbackQuery,
): SalesOrderListItem[] => {
  const status = normalizeValue(query.status).toLowerCase()
  const followupGroup = normalizeValue(query.followup_group).toLowerCase()
  return rows.filter((row) => {
    if (status && normalizeValue(row.status).toLowerCase() !== status) {
      return false
    }
    if (followupGroup && resolveSalesOrderReadonlyGroup(row) !== followupGroup) {
      return false
    }
    return true
  })
}

export const buildSalesOrderReadonlySummary = (
  rows: SalesOrderListItem[],
): SalesOrderReadonlySummary => {
  const customers = new Set<string>()
  let totalAmount = 0
  let draftCount = 0
  let deliveryCount = 0
  let closedCount = 0

  rows.forEach((row) => {
    const group = resolveSalesOrderReadonlyGroup(row)
    totalAmount += toNumber(row.grand_total)
    if (row.customer) {
      customers.add(row.customer)
    }
    if (group === 'draft-watch') draftCount += 1
    if (group === 'delivery-followup') deliveryCount += 1
    if (group === 'closed') closedCount += 1
  })

  return {
    filteredCount: rows.length,
    draftCount,
    deliveryCount,
    closedCount,
    customerCount: customers.size,
    totalAmount,
  }
}

export const buildSalesOrderDetailReadonlySummary = (
  detail: SalesOrderDetailData,
): SalesOrderDetailReadonlySummary => {
  let totalOrderedQty = 0
  let deliveredQty = 0
  let primaryItemCode = ''
  let primaryItemName = ''
  let primaryItemQty = -1

  detail.items.forEach((item) => {
    const qty = toNumber(item.qty)
    const delivered = toNumber(item.delivered_qty)
    totalOrderedQty += qty
    deliveredQty += delivered
    if (qty > primaryItemQty) {
      primaryItemQty = qty
      primaryItemCode = item.item_code
      primaryItemName = item.item_name?.trim() || item.item_code
    }
  })

  const remainingQty = Math.max(totalOrderedQty - deliveredQty, 0)
  const ratio =
    totalOrderedQty > 0 ? `${Math.round((deliveredQty / totalOrderedQty) * 100)}%` : '0%'

  return {
    itemCount: detail.items.length,
    totalOrderedQty,
    deliveredQty,
    remainingQty,
    primaryItemCode: primaryItemCode || '-',
    primaryItemName: primaryItemName || '-',
    deliveryCompletionRatio: ratio,
  }
}
