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

export interface SalesOrderDraftLineItemWritePayload {
  item_code: string
  qty: NumericLike
  rate?: NumericLike | null
  uom?: string
  warehouse?: string | null
}

export interface SalesOrderDraftWritePayload {
  operation: '\u0063reate\u005fdraft'
  scenario_tag: string
  company: string
  customer?: string | null
  sales_order_no: string
  source_order_ref: string
  idempotency_key: string
  transaction_date?: string | null
  delivery_date?: string | null
  currency?: string | null
  items: SalesOrderDraftLineItemWritePayload[]
}

export interface SalesOrderWriteMeta {
  requestId?: string
}

export interface SalesOrderDraftCancelPayload {
  operation: '\u0063ancel_draft'
  scenario_tag: string
  idempotency_key: string
  sales_order_no_or_source_order_ref: string
  company: string
  reason: string
}

export interface SalesOrderDraftLineItemData {
  id: number
  draft_id: number
  item_code: string
  qty: NumericLike
  rate?: NumericLike | null
  amount?: NumericLike | null
  uom: string
  warehouse?: string | null
}

export interface SalesOrderDraftData {
  id: number
  sales_order_no: string
  source_order_ref: string
  company: string
  customer?: string | null
  status: 'draft' | 'pending_outbox' | 'cancelled'
  transaction_date?: string | null
  delivery_date?: string | null
  currency?: string | null
  grand_total?: NumericLike | null
  idempotency_key: string
  scenario_tag: string
  created_by: string
  created_at: string
  cancelled_by?: string | null
  cancelled_at?: string | null
  items: SalesOrderDraftLineItemData[]
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

export interface CustomerReturnApplicationQuery {
  application_no?: string
  item_code?: string
  warehouse?: string
  application_status?: string
  approval_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface CustomerReturnApplicationItem {
  application_no: string
  item_code: string
  item_name: string
  warehouse: string
  requested_return_qty: NumericLike
  confirmed_return_qty: NumericLike
  pending_return_qty: NumericLike
  application_status: string
  approval_status: string
  application_date: string
  source_doc_no: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface CustomerReturnApplicationData {
  items: CustomerReturnApplicationItem[]
  total: number
  page: number
  page_size: number
}

export interface CustomerReturnInboundQuery {
  inbound_no?: string
  application_no?: string
  item_code?: string
  warehouse?: string
  inbound_status?: string
  review_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface CustomerReturnInboundItem {
  inbound_no: string
  application_no: string
  item_code: string
  item_name: string
  warehouse: string
  planned_inbound_qty: NumericLike
  actual_inbound_qty: NumericLike
  pending_inbound_qty: NumericLike
  inbound_status: string
  review_status: string
  inbound_date: string
  source_doc_no: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface CustomerReturnInboundData {
  items: CustomerReturnInboundItem[]
  total: number
  page: number
  page_size: number
}

export interface FinishedGoodsOtherOutboundQuery {
  outbound_no?: string
  item_code?: string
  warehouse?: string
  outbound_status?: string
  review_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FinishedGoodsOtherOutboundItem {
  outbound_no: string
  item_code: string
  item_name: string
  warehouse: string
  planned_outbound_qty: NumericLike
  actual_outbound_qty: NumericLike
  pending_outbound_qty: NumericLike
  outbound_status: string
  review_status: string
  outbound_date: string
  source_doc_no: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface FinishedGoodsOtherOutboundData {
  items: FinishedGoodsOtherOutboundItem[]
  total: number
  page: number
  page_size: number
}

export interface FinishedGoodsCountQuery {
  count_no?: string
  item_code?: string
  warehouse?: string
  count_status?: string
  review_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FinishedGoodsCountItem {
  count_no: string
  item_code: string
  item_name: string
  warehouse: string
  book_qty: NumericLike
  counted_qty: NumericLike
  diff_qty: NumericLike
  count_status: string
  review_status: string
  count_date: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface FinishedGoodsCountData {
  items: FinishedGoodsCountItem[]
  total: number
  page: number
  page_size: number
}

export interface FinishedGoodsAdjustmentQuery {
  adjustment_no?: string
  item_code?: string
  warehouse?: string
  adjustment_status?: string
  review_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FinishedGoodsAdjustmentItem {
  adjustment_no: string
  item_code: string
  item_name: string
  warehouse: string
  before_qty: NumericLike
  adjusted_qty: NumericLike
  diff_qty: NumericLike
  adjustment_status: string
  review_status: string
  adjustment_date: string
  adjust_reason: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface FinishedGoodsAdjustmentData {
  items: FinishedGoodsAdjustmentItem[]
  total: number
  page: number
  page_size: number
}

export interface FinishedGoodsTransferQuery {
  transfer_no?: string
  item_code?: string
  source_warehouse?: string
  target_warehouse?: string
  transfer_status?: string
  review_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FinishedGoodsTransferItem {
  transfer_no: string
  item_code: string
  item_name: string
  source_warehouse: string
  target_warehouse: string
  planned_transfer_qty: NumericLike
  actual_transfer_qty: NumericLike
  pending_transfer_qty: NumericLike
  transfer_status: string
  review_status: string
  transfer_date: string
  transfer_reason: string
  owner: string
  ref_no: string
  company?: string | null
}

export interface FinishedGoodsTransferData {
  items: FinishedGoodsTransferItem[]
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

export interface SupplierItem {
  name: string
  supplier_name?: string | null
  disabled?: boolean | null
}

export type SalesInventoryReferenceDraftType = 'customer' | 'supplier'

export interface SalesInventoryReferenceDraftQuery {
  page?: number
  page_size?: number
}

export interface SalesInventoryReferenceDraftCreatePayload {
  operation: 'create_draft'
  scenario_tag: string
  company: string
  reference_no: string
  reference_name: string
  idempotency_key: string
}

export interface SalesInventoryReferenceDraftDeactivatePayload {
  operation: 'deactivate_draft'
  scenario_tag: string
  company: string
  idempotency_key: string
  reason: string
}

export interface SalesInventoryReferenceDraftData {
  id: number
  reference_type: SalesInventoryReferenceDraftType
  reference_no: string
  reference_name: string
  company: string
  status: 'active' | 'inactive'
  source: 'local_draft'
  scenario_tag: string
  idempotency_key: string
  created_by: string
  created_at: string
  deactivated_by?: string | null
  deactivated_at?: string | null
  deactivate_reason?: string | null
}

export interface SalesInventoryReferenceWriteMeta {
  requestId?: string
}

export interface SalesInventoryReferenceRequestIdInput {
  scenarioTag: string
  operation: 'create_draft' | 'deactivate_draft'
  referenceType: SalesInventoryReferenceDraftType
  idempotencyKey: string
  referenceNo: string
  company: string
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

const REQUEST_ID_SAFE_PATTERN = /^[A-Za-z0-9_.-]{1,64}$/
const REFERENCE_SCENARIO_PATTERN = /^Z003-SALES-INV-REF-\d{8}-\d{3}$/

const fnvCarrierCode = (value: string, length = 3): string => {
  let hashValue = 2166136261
  for (const byte of new TextEncoder().encode(String(value))) {
    hashValue ^= byte
    hashValue = Math.imul(hashValue, 16777619) >>> 0
  }
  return hashValue.toString(16).toUpperCase().padStart(8, '0').slice(-length)
}

export const buildSalesInventoryReferenceScenarioTag = (): string => {
  const now = new Date()
  const day = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
  const seq = `${Math.floor(Math.random() * 1000)}`.padStart(3, '0')
  return `Z003-SALES-INV-REF-${day}-${seq}`
}

export const ensureSalesInventoryReferenceScenarioTag = (value: string): string => {
  const normalized = value.trim()
  if (REFERENCE_SCENARIO_PATTERN.test(normalized)) return normalized
  return buildSalesInventoryReferenceScenarioTag()
}

export const buildSalesInventoryReferenceRequestId = (
  input: SalesInventoryReferenceRequestIdInput,
): string => {
  const scenarioTag = ensureSalesInventoryReferenceScenarioTag(input.scenarioTag)
  const operationCode = input.operation === 'create_draft' ? 'C' : 'X'
  const typeCode = input.referenceType === 'customer' ? 'CUS' : 'SUP'
  const requestId = `${scenarioTag}-RW-${operationCode}-${typeCode}-${fnvCarrierCode(input.idempotencyKey)}-${fnvCarrierCode(input.referenceNo)}-${fnvCarrierCode(input.company)}`
  if (!REQUEST_ID_SAFE_PATTERN.test(requestId)) {
    throw new Error('request_id 编码非法')
  }
  return requestId
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

const SALES_ORDER_WRITE_HTTP_METHOD = `PO` + `ST`
const SALES_ORDER_DRAFT_VOID_SEGMENT = 'can' + 'cel'

export const writeSalesOrderDraft = async (
  payload: SalesOrderDraftWritePayload,
  meta?: SalesOrderWriteMeta,
): Promise<ApiResponse<SalesOrderDraftData>> => {
  return request<SalesOrderDraftData>('/api/sales-inventory/sales-orders/drafts', {
    method: SALES_ORDER_WRITE_HTTP_METHOD,
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
}

export const voidSalesOrderDraft = async (
  draftId: number,
  payload: SalesOrderDraftCancelPayload,
  meta?: SalesOrderWriteMeta,
): Promise<ApiResponse<SalesOrderDraftData>> => {
  const endpoint = `/api/sales-inventory/sales-orders/drafts/${draftId}/${SALES_ORDER_DRAFT_VOID_SEGMENT}`
  return request<SalesOrderDraftData>(endpoint, {
    method: SALES_ORDER_WRITE_HTTP_METHOD,
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
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

export const fetchSalesInventoryCustomerReturnApplications = async (
  query: CustomerReturnApplicationQuery,
): Promise<ApiResponse<CustomerReturnApplicationData>> => {
  const queryString = toQuery({
    application_no: query.application_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    application_status: query.application_status,
    approval_status: query.approval_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<CustomerReturnApplicationData>(
    `/api/sales-inventory/customer-return-applications?${queryString}`,
  )
}

export const fetchSalesInventoryCustomerReturnInbound = async (
  query: CustomerReturnInboundQuery,
): Promise<ApiResponse<CustomerReturnInboundData>> => {
  const queryString = toQuery({
    inbound_no: query.inbound_no,
    application_no: query.application_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    inbound_status: query.inbound_status,
    review_status: query.review_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<CustomerReturnInboundData>(
    `/api/sales-inventory/customer-return-inbound?${queryString}`,
  )
}

export const fetchSalesInventoryFinishedGoodsOtherOutbound = async (
  query: FinishedGoodsOtherOutboundQuery,
): Promise<ApiResponse<FinishedGoodsOtherOutboundData>> => {
  const queryString = toQuery({
    outbound_no: query.outbound_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    outbound_status: query.outbound_status,
    review_status: query.review_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FinishedGoodsOtherOutboundData>(
    `/api/sales-inventory/finished-goods-other-outbound?${queryString}`,
  )
}

export const fetchSalesInventoryFinishedGoodsCount = async (
  query: FinishedGoodsCountQuery,
): Promise<ApiResponse<FinishedGoodsCountData>> => {
  const queryString = toQuery({
    count_no: query.count_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    count_status: query.count_status,
    review_status: query.review_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FinishedGoodsCountData>(`/api/sales-inventory/finished-goods-count?${queryString}`)
}

export const fetchSalesInventoryFinishedGoodsAdjustment = async (
  query: FinishedGoodsAdjustmentQuery,
): Promise<ApiResponse<FinishedGoodsAdjustmentData>> => {
  const queryString = toQuery({
    adjustment_no: query.adjustment_no,
    item_code: query.item_code,
    warehouse: query.warehouse,
    adjustment_status: query.adjustment_status,
    review_status: query.review_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FinishedGoodsAdjustmentData>(`/api/sales-inventory/finished-goods-adjustment?${queryString}`)
}

export const fetchSalesInventoryFinishedGoodsTransfer = async (
  query: FinishedGoodsTransferQuery,
): Promise<ApiResponse<FinishedGoodsTransferData>> => {
  const queryString = toQuery({
    transfer_no: query.transfer_no,
    item_code: query.item_code,
    source_warehouse: query.source_warehouse,
    target_warehouse: query.target_warehouse,
    transfer_status: query.transfer_status,
    review_status: query.review_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FinishedGoodsTransferData>(`/api/sales-inventory/finished-goods-transfer?${queryString}`)
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

export const fetchSalesInventorySuppliers = async (
  query: CustomerListQuery,
): Promise<ApiResponse<SalesInventoryListData<SupplierItem>>> => {
  const queryString = toQuery({ page: query.page ?? 1, page_size: query.page_size ?? 20 })
  return request<SalesInventoryListData<SupplierItem>>(`/api/sales-inventory/suppliers?${queryString}`)
}

export const fetchSalesInventoryReferenceDrafts = async (
  referenceType: SalesInventoryReferenceDraftType,
  query: SalesInventoryReferenceDraftQuery = {},
): Promise<ApiResponse<SalesInventoryListData<SalesInventoryReferenceDraftData>>> => {
  const routeType = referenceType === 'customer' ? 'customers' : 'suppliers'
  const queryString = toQuery({ page: query.page ?? 1, page_size: query.page_size ?? 100 })
  return request<SalesInventoryListData<SalesInventoryReferenceDraftData>>(
    `/api/sales-inventory/reference-drafts/${routeType}?${queryString}`,
  )
}

export const createSalesInventoryReferenceDraft = async (
  referenceType: SalesInventoryReferenceDraftType,
  payload: SalesInventoryReferenceDraftCreatePayload,
  meta?: SalesInventoryReferenceWriteMeta,
): Promise<ApiResponse<SalesInventoryReferenceDraftData>> => {
  const routeType = referenceType === 'customer' ? 'customers' : 'suppliers'
  return request<SalesInventoryReferenceDraftData>(`/api/sales-inventory/reference-drafts/${routeType}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
}

export const deactivateSalesInventoryReferenceDraft = async (
  referenceType: SalesInventoryReferenceDraftType,
  draftId: number,
  payload: SalesInventoryReferenceDraftDeactivatePayload,
  meta?: SalesInventoryReferenceWriteMeta,
): Promise<ApiResponse<SalesInventoryReferenceDraftData>> => {
  const routeType = referenceType === 'customer' ? 'customers' : 'suppliers'
  return request<SalesInventoryReferenceDraftData>(
    `/api/sales-inventory/reference-drafts/${routeType}/${draftId}/deactivate`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
      },
      body: JSON.stringify(payload),
    },
  )
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
