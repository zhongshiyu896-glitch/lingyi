import { request, type ApiResponse } from '@/api/request'

type NumericLike = string | number

export interface SalesInventoryListQuery {
  order_no?: string
  keyword?: string
  company?: string
  customer?: string
  item_code?: string
  item_name?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface SalesOrderListItem {
  name: string
  company: string
  customer?: string | null
  transaction_date?: string | null
  delivery_date?: string | null
  status?: string | null
  docstatus: number
  grand_total?: NumericLike | null
  currency?: string | null
}

export interface SalesOrderLineItem {
  name?: string | null
  item_code: string
  item_name?: string | null
  qty: NumericLike
  delivered_qty?: NumericLike | null
  rate?: NumericLike | null
  amount?: NumericLike | null
  warehouse?: string | null
  delivery_date?: string | null
}

export interface SalesOrderDetailData extends SalesOrderListItem {
  items: SalesOrderLineItem[]
}

export interface SalesInventoryListData<T> {
  items: T[]
  total: number
  page: number
  page_size: number
}

export interface StockSummaryItem {
  company: string
  item_code: string
  warehouse: string
  balance_qty: NumericLike
  latest_posting_date?: string | null
  latest_posting_time?: string | null
}

export interface StockSummaryData {
  item_code: string
  company?: string | null
  warehouse?: string | null
  items: StockSummaryItem[]
  dropped_count: number
}

export interface StockLedgerQuery {
  company?: string
  warehouse?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface StockLedgerItem {
  name?: string | null
  company: string
  item_code: string
  warehouse: string
  posting_date: string
  posting_time?: string | null
  actual_qty: NumericLike
  qty_after_transaction: NumericLike
  voucher_type?: string | null
  voucher_no?: string | null
}

export interface StockLedgerData {
  items: StockLedgerItem[]
  total: number
  page: number
  page_size: number
  dropped_count: number
}

export interface FinishedGoodsReportQuery {
  no?: string
  style?: string
  warehouse?: string
  from_date?: string
  to_date?: string
  keyword?: string
  page?: number
  page_size?: number
}

export interface FinishedGoodsReportItem {
  image_url?: string | null
  processing_no?: string | null
  production_order?: string | null
  order_no: string
  item_code: string
  item_name?: string | null
  warehouse?: string | null
  season?: string | null
  style_type?: string | null
  qty: NumericLike
  receipt_date?: string | null
  week_day_0?: string | null
  week_day_1?: string | null
  week_day_2?: string | null
  week_day_3?: string | null
  week_day_4?: string | null
  week_day_5?: string | null
  week_day_6?: string | null
  message_title?: string | null
  sent_at?: string | null
  message_status?: string | null
  sender?: string | null
}

export interface FinishedGoodsReportData {
  items: FinishedGoodsReportItem[]
  total: number
  page: number
  page_size: number
  dropped_count: number
}

export interface WarehouseListQuery {
  company?: string
  page?: number
  page_size?: number
}

export interface WarehouseItem {
  name: string
  company?: string | null
  warehouse_name?: string | null
  disabled?: boolean | null
}

export interface CustomerListQuery {
  page?: number
  page_size?: number
}

export interface CustomerItem {
  name: string
  customer_name?: string | null
  disabled?: boolean | null
}

export interface SalesInventoryAggregationQuery {
  company?: string
  item_code?: string
  warehouse?: string
}

export interface SalesInventoryAggregationItem {
  item_code: string
  warehouse: string
  actual_qty: NumericLike
  ordered_qty: NumericLike
  indented_qty: NumericLike
  safety_stock: NumericLike
  reorder_level: NumericLike
  is_below_safety: boolean
  is_below_reorder: boolean
}

export interface SalesInventoryAggregationData {
  company?: string | null
  item_code?: string | null
  warehouse?: string | null
  items: SalesInventoryAggregationItem[]
}

export interface SalesOrderFulfillmentItem {
  company?: string | null
  sales_order: string
  item_code: string
  warehouse?: string | null
  ordered_qty: NumericLike
  actual_qty: NumericLike
  fulfillment_rate: NumericLike
}

export interface SalesOrderFulfillmentData {
  company?: string | null
  items: SalesOrderFulfillmentItem[]
}

const toQuery = (params: Record<string, unknown>): string => {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (
      value !== undefined &&
      value !== null &&
      value !== '' &&
      (typeof value === 'string' || typeof value === 'number' || typeof value === 'boolean')
    ) {
      query.append(key, String(value))
    }
  })
  return query.toString()
}

export const fetchSalesInventorySalesOrders = async (
  query: SalesInventoryListQuery,
): Promise<ApiResponse<SalesInventoryListData<SalesOrderListItem>>> => {
  const queryString = toQuery({
    order_no: query.order_no,
    keyword: query.keyword,
    company: query.company,
    customer: query.customer,
    item_code: query.item_code,
    item_name: query.item_name,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<SalesInventoryListData<SalesOrderListItem>>(`/api/sales-inventory/sales-orders?${queryString}`)
}

export const fetchSalesInventorySalesOrderDetail = async (
  name: string,
): Promise<ApiResponse<SalesOrderDetailData>> => {
  return request<SalesOrderDetailData>(`/api/sales-inventory/sales-orders/${encodeURIComponent(name)}`)
}

export const fetchSalesInventoryStockSummary = async (
  itemCode: string,
  query: Pick<StockLedgerQuery, 'company' | 'warehouse'> = {},
): Promise<ApiResponse<StockSummaryData>> => {
  const queryString = toQuery({ company: query.company, warehouse: query.warehouse })
  return request<StockSummaryData>(
    `/api/sales-inventory/items/${encodeURIComponent(itemCode)}/stock-summary?${queryString}`,
  )
}

export const fetchSalesInventoryStockLedger = async (
  itemCode: string,
  query: StockLedgerQuery,
): Promise<ApiResponse<StockLedgerData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<StockLedgerData>(`/api/sales-inventory/items/${encodeURIComponent(itemCode)}/stock-ledger?${queryString}`)
}

export const fetchSalesInventoryFinishedGoodsReport = async (
  query: FinishedGoodsReportQuery,
): Promise<ApiResponse<FinishedGoodsReportData>> => {
  const queryString = toQuery({
    no: query.no,
    style: query.style,
    warehouse: query.warehouse,
    from_date: query.from_date,
    to_date: query.to_date,
    keyword: query.keyword,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FinishedGoodsReportData>(`/api/sales-inventory/finished-goods-report?${queryString}`)
}

export const fetchSalesInventoryWarehouses = async (
  query: WarehouseListQuery,
): Promise<ApiResponse<SalesInventoryListData<WarehouseItem>>> => {
  const queryString = toQuery({
    company: query.company,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<SalesInventoryListData<WarehouseItem>>(`/api/sales-inventory/warehouses?${queryString}`)
}

export const fetchSalesInventoryCustomers = async (
  query: CustomerListQuery,
): Promise<ApiResponse<SalesInventoryListData<CustomerItem>>> => {
  const queryString = toQuery({ page: query.page ?? 1, page_size: query.page_size ?? 20 })
  return request<SalesInventoryListData<CustomerItem>>(`/api/sales-inventory/customers?${queryString}`)
}

export const fetchSalesInventoryAggregation = async (
  query: SalesInventoryAggregationQuery,
): Promise<ApiResponse<SalesInventoryAggregationData>> => {
  const queryString = toQuery({
    company: query.company,
    item_code: query.item_code,
    warehouse: query.warehouse,
  })
  return request<SalesInventoryAggregationData>(`/api/sales-inventory/aggregation?${queryString}`)
}

export const fetchSalesInventorySalesOrderFulfillment = async (
  query: Pick<SalesInventoryAggregationQuery, 'company' | 'item_code' | 'warehouse'>,
): Promise<ApiResponse<SalesOrderFulfillmentData>> => {
  const queryString = toQuery({
    company: query.company,
    item_code: query.item_code,
    warehouse: query.warehouse,
  })
  return request<SalesOrderFulfillmentData>(`/api/sales-inventory/sales-order-fulfillment?${queryString}`)
}
