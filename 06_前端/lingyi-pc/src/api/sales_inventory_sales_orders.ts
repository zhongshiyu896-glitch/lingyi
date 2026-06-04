import {
  fetchSalesInventorySalesOrderDetail,
  fetchSalesInventorySalesOrders,
  type SalesInventoryListQuery,
  type SalesOrderDetailData,
  type SalesOrderListItem,
} from '@/api/sales_inventory'
import {
  splitSalesOrderMatrixStyle,
  type SalesOrderMatrixProgressState,
} from '@/views/sales_inventory/constants/salesOrderMatrixFields'

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

export interface SalesOrderQuantityMatrixRow {
  styleKey: string
  color: string
  size: string
  orderedQty: number
  deliveredQty: number
  remainingQty: number
  completionRate: number
  completionRateLabel: string
  deliveryDateLabel: string
  progressState: SalesOrderMatrixProgressState
  sourceItemsLabel: string
}

export interface SalesOrderQuantityMatrixReadonlySummary {
  matrixCellCount: number
  colorCount: number
  sizeCount: number
  delayedLineCount: number
  completedLineCount: number
  inProgressLineCount: number
  totalOrderedQty: number
  totalDeliveredQty: number
  totalRemainingQty: number
  matrixCompletionRate: number
  matrixCompletionRateLabel: string
  rows: SalesOrderQuantityMatrixRow[]
}

const toNumber = (value?: string | number | null): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const normalizeValue = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const formatPercent = (value: number): string => `${Math.round(value)}%`

const todayStamp = (): number => {
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return now.getTime()
}

const toDateStamp = (value?: string | null): number | null => {
  const normalized = normalizeValue(value)
  if (!normalized) return null
  const stamp = new Date(normalized).getTime()
  return Number.isFinite(stamp) ? stamp : null
}

const resolveMatrixProgressState = (
  orderedQty: number,
  deliveredQty: number,
  isDelayed: boolean,
): SalesOrderMatrixProgressState => {
  if (isDelayed) return 'delayed'
  if (orderedQty > 0 && deliveredQty >= orderedQty) return 'completed'
  if (deliveredQty > 0) return 'in-progress'
  return 'not-started'
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

export const buildSalesOrderQuantityMatrixReadonlySummary = (
  detail: SalesOrderDetailData,
): SalesOrderQuantityMatrixReadonlySummary => {
  const matrixMap = new Map<
    string,
    {
      styleKey: string
      color: string
      size: string
      orderedQty: number
      deliveredQty: number
      remainingQty: number
      earliestDeliveryStamp: number | null
      deliveryDateLabel: string
      sourceItems: Set<string>
    }
  >()

  const colors = new Set<string>()
  const sizes = new Set<string>()
  const today = todayStamp()

  detail.items.forEach((item) => {
    const { styleKey, color, size } = splitSalesOrderMatrixStyle(item.item_code, item.item_name)
    const key = `${styleKey}::${color}::${size}`
    const orderedQty = toNumber(item.qty)
    const deliveredQty = Math.min(toNumber(item.delivered_qty), orderedQty)
    const remainingQty = Math.max(orderedQty - deliveredQty, 0)
    const deliveryDateLabel = normalizeValue(item.delivery_date) || detail.delivery_date || '-'
    const deliveryStamp = toDateStamp(deliveryDateLabel)

    colors.add(color)
    sizes.add(size)

    if (!matrixMap.has(key)) {
      matrixMap.set(key, {
        styleKey,
        color,
        size,
        orderedQty: 0,
        deliveredQty: 0,
        remainingQty: 0,
        earliestDeliveryStamp: deliveryStamp,
        deliveryDateLabel,
        sourceItems: new Set<string>(),
      })
    }

    const row = matrixMap.get(key)!
    row.orderedQty += orderedQty
    row.deliveredQty += deliveredQty
    row.remainingQty += remainingQty
    row.sourceItems.add(item.item_code)
    if (deliveryStamp !== null && (row.earliestDeliveryStamp === null || deliveryStamp < row.earliestDeliveryStamp)) {
      row.earliestDeliveryStamp = deliveryStamp
      row.deliveryDateLabel = deliveryDateLabel
    }
  })

  let delayedLineCount = 0
  let completedLineCount = 0
  let inProgressLineCount = 0
  let totalOrderedQty = 0
  let totalDeliveredQty = 0
  let totalRemainingQty = 0

  const rows: SalesOrderQuantityMatrixRow[] = Array.from(matrixMap.values())
    .map((row) => {
      totalOrderedQty += row.orderedQty
      totalDeliveredQty += row.deliveredQty
      totalRemainingQty += row.remainingQty
      const completionRate = row.orderedQty > 0 ? (row.deliveredQty / row.orderedQty) * 100 : 0
      const isDelayed = Boolean(
        row.remainingQty > 0 &&
          row.earliestDeliveryStamp !== null &&
          row.earliestDeliveryStamp < today,
      )
      const progressState = resolveMatrixProgressState(row.orderedQty, row.deliveredQty, isDelayed)
      if (progressState === 'delayed') delayedLineCount += 1
      if (progressState === 'completed') completedLineCount += 1
      if (progressState === 'in-progress') inProgressLineCount += 1

      return {
        styleKey: row.styleKey,
        color: row.color,
        size: row.size,
        orderedQty: row.orderedQty,
        deliveredQty: row.deliveredQty,
        remainingQty: row.remainingQty,
        completionRate,
        completionRateLabel: formatPercent(completionRate),
        deliveryDateLabel: row.deliveryDateLabel,
        progressState,
        sourceItemsLabel: Array.from(row.sourceItems).join(' / '),
      }
    })
    .sort((left, right) =>
      `${left.styleKey}-${left.color}-${left.size}`.localeCompare(`${right.styleKey}-${right.color}-${right.size}`, 'zh-CN'),
    )

  const matrixCompletionRate = totalOrderedQty > 0 ? (totalDeliveredQty / totalOrderedQty) * 100 : 0

  return {
    matrixCellCount: rows.length,
    colorCount: colors.size,
    sizeCount: sizes.size,
    delayedLineCount,
    completedLineCount,
    inProgressLineCount,
    totalOrderedQty,
    totalDeliveredQty,
    totalRemainingQty,
    matrixCompletionRate,
    matrixCompletionRateLabel: formatPercent(matrixCompletionRate),
    rows,
  }
}
