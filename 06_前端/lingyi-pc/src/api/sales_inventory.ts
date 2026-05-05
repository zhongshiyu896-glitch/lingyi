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

export interface MaterialTransferQuery {
  item_code?: string
  keyword?: string
  source_warehouse?: string
  target_warehouse?: string
  status?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface MaterialTransferItem {
  transfer_no: string
  material_code: string
  material_name: string
  source_warehouse: string
  target_warehouse: string
  transfer_qty: NumericLike
  inbound_qty: NumericLike
  diff_qty: NumericLike
  operator: string
  status: string
  transfer_date: string
  warehouse?: string | null
  company?: string | null
}

export interface MaterialTransferData {
  items: MaterialTransferItem[]
  total: number
  page: number
  page_size: number
}

export interface MaterialCountQuery {
  item_code?: string
  keyword?: string
  warehouse?: string
  count_status?: string
  review_status?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface MaterialCountItem {
  count_no: string
  material_code: string
  material_name: string
  warehouse: string
  book_qty: NumericLike
  counted_qty: NumericLike
  diff_qty: NumericLike
  count_status: string
  review_status: string
  count_date: string
  owner: string
  company?: string | null
}

export interface MaterialCountData {
  items: MaterialCountItem[]
  total: number
  page: number
  page_size: number
}

export interface MaterialInventoryReportQuery {
  report_no?: string
  item_code?: string
  warehouse?: string
  business_type?: string
  status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface MaterialInventoryReportItem {
  report_no: string
  material_code: string
  material_name: string
  warehouse: string
  business_type: string
  in_qty: NumericLike
  out_qty: NumericLike
  balance_qty: NumericLike
  status: string
  biz_date: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface MaterialInventoryReportData {
  items: MaterialInventoryReportItem[]
  total: number
  page: number
  page_size: number
}

export interface InventoryMaterialRetentionReportQuery {
  report_no?: string
  item_code?: string
  warehouse?: string
  retention_level?: string
  status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface InventoryMaterialRetentionReportItem {
  report_no: string
  material_code: string
  material_name: string
  warehouse: string
  retention_level: string
  retention_days: NumericLike
  current_qty: NumericLike
  stagnant_qty: NumericLike
  turnover_days: NumericLike
  status: string
  biz_date: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface InventoryMaterialRetentionReportData {
  items: InventoryMaterialRetentionReportItem[]
  total: number
  page: number
  page_size: number
}

export interface SemiFinishedInventoryQuery {
  record_no?: string
  item_code?: string
  warehouse?: string
  process_stage?: string
  status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface SemiFinishedInventoryItem {
  record_no: string
  material_code: string
  material_name: string
  warehouse: string
  process_stage: string
  opening_qty: NumericLike
  in_qty: NumericLike
  out_qty: NumericLike
  closing_qty: NumericLike
  status: string
  biz_date: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface SemiFinishedInventoryData {
  items: SemiFinishedInventoryItem[]
  total: number
  page: number
  page_size: number
}

export interface FinishedGoodsReservedInboundQuery {
  reservation_no?: string
  item_code?: string
  warehouse?: string
  reserve_status?: string
  inbound_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FinishedGoodsReservedInboundItem {
  reservation_no: string
  item_code: string
  item_name: string
  warehouse: string
  reserve_qty: NumericLike
  inbound_qty: NumericLike
  pending_inbound_qty: NumericLike
  reserve_status: string
  inbound_status: string
  reserved_date: string
  expected_inbound_date: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface FinishedGoodsReservedInboundData {
  items: FinishedGoodsReservedInboundItem[]
  total: number
  page: number
  page_size: number
}

export interface FinishedGoodsShippingNoticeQuery {
  notice_no?: string
  item_code?: string
  warehouse?: string
  notice_status?: string
  logistics_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FinishedGoodsShippingNoticeItem {
  notice_no: string
  item_code: string
  item_name: string
  warehouse: string
  planned_ship_qty: NumericLike
  shipped_qty: NumericLike
  pending_ship_qty: NumericLike
  notice_status: string
  logistics_status: string
  notice_date: string
  expected_delivery_date: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface FinishedGoodsShippingNoticeData {
  items: FinishedGoodsShippingNoticeItem[]
  total: number
  page: number
  page_size: number
}

export interface FinishedGoodsOtherInboundQuery {
  inbound_no?: string
  item_code?: string
  warehouse?: string
  inbound_status?: string
  settlement_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FinishedGoodsOtherInboundItem {
  inbound_no: string
  item_code: string
  item_name: string
  warehouse: string
  planned_inbound_qty: NumericLike
  actual_inbound_qty: NumericLike
  pending_inbound_qty: NumericLike
  inbound_status: string
  settlement_status: string
  inbound_date: string
  source_doc_no: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface FinishedGoodsOtherInboundData {
  items: FinishedGoodsOtherInboundItem[]
  total: number
  page: number
  page_size: number
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

export interface SalesOrderFulfillmentQuery {
  company?: string
  item_code?: string
  warehouse?: string
  item_name?: string
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

export const fetchSalesInventoryMaterialTransfers = async (
  query: MaterialTransferQuery,
): Promise<ApiResponse<MaterialTransferData>> => {
  const queryString = toQuery({
    item_code: query.item_code,
    keyword: query.keyword,
    source_warehouse: query.source_warehouse,
    target_warehouse: query.target_warehouse,
    status: query.status,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<MaterialTransferData>(`/api/sales-inventory/material-transfers?${queryString}`)
}

export const fetchSalesInventoryMaterialCounts = async (
  query: MaterialCountQuery,
): Promise<ApiResponse<MaterialCountData>> => {
  const queryString = toQuery({
    item_code: query.item_code,
    keyword: query.keyword,
    warehouse: query.warehouse,
    count_status: query.count_status,
    review_status: query.review_status,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<MaterialCountData>(`/api/sales-inventory/material-counts?${queryString}`)
}

export const fetchSalesInventoryMaterialInventoryReport = async (
  query: MaterialInventoryReportQuery,
): Promise<ApiResponse<MaterialInventoryReportData>> => {
  const queryString = toQuery({
    report_no: query.report_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    business_type: query.business_type,
    status: query.status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<MaterialInventoryReportData>(`/api/sales-inventory/material-inventory-report?${queryString}`)
}

export const fetchSalesInventoryInventoryMaterialRetentionReport = async (
  query: InventoryMaterialRetentionReportQuery,
): Promise<ApiResponse<InventoryMaterialRetentionReportData>> => {
  const queryString = toQuery({
    report_no: query.report_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    retention_level: query.retention_level,
    status: query.status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<InventoryMaterialRetentionReportData>(
    `/api/sales-inventory/inventory-material-retention-report?${queryString}`,
  )
}

export const fetchSalesInventorySemiFinishedInventory = async (
  query: SemiFinishedInventoryQuery,
): Promise<ApiResponse<SemiFinishedInventoryData>> => {
  const queryString = toQuery({
    record_no: query.record_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    process_stage: query.process_stage,
    status: query.status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<SemiFinishedInventoryData>(`/api/sales-inventory/semi-finished-inventory?${queryString}`)
}

export const fetchSalesInventoryFinishedGoodsReservedInbound = async (
  query: FinishedGoodsReservedInboundQuery,
): Promise<ApiResponse<FinishedGoodsReservedInboundData>> => {
  const queryString = toQuery({
    reservation_no: query.reservation_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    reserve_status: query.reserve_status,
    inbound_status: query.inbound_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FinishedGoodsReservedInboundData>(
    `/api/sales-inventory/finished-goods-reserved-inbound?${queryString}`,
  )
}

export const fetchSalesInventoryFinishedGoodsShippingNotices = async (
  query: FinishedGoodsShippingNoticeQuery,
): Promise<ApiResponse<FinishedGoodsShippingNoticeData>> => {
  const queryString = toQuery({
    notice_no: query.notice_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    notice_status: query.notice_status,
    logistics_status: query.logistics_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FinishedGoodsShippingNoticeData>(
    `/api/sales-inventory/finished-goods-shipping-notices?${queryString}`,
  )
}

export const fetchSalesInventoryFinishedGoodsOtherInbound = async (
  query: FinishedGoodsOtherInboundQuery,
): Promise<ApiResponse<FinishedGoodsOtherInboundData>> => {
  const queryString = toQuery({
    inbound_no: query.inbound_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    inbound_status: query.inbound_status,
    settlement_status: query.settlement_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FinishedGoodsOtherInboundData>(
    `/api/sales-inventory/finished-goods-other-inbound?${queryString}`,
  )
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
  query: SalesOrderFulfillmentQuery,
): Promise<ApiResponse<SalesOrderFulfillmentData>> => {
  const queryString = toQuery({
    company: query.company,
    item_code: query.item_code,
    warehouse: query.warehouse,
    item_name: query.item_name,
  })
  return request<SalesOrderFulfillmentData>(`/api/sales-inventory/sales-order-fulfillment?${queryString}`)
}
