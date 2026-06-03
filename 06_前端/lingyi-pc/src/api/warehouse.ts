import { request, type ApiResponse } from '@/api/request'

type NumericLike = string | number

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

export interface WarehouseStockLedgerQuery {
  company?: string
  warehouse?: string
  item_code?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface WarehouseStockLedgerItem {
  company: string
  warehouse: string
  item_code: string
  posting_date: string
  voucher_type?: string | null
  voucher_no?: string | null
  actual_qty: NumericLike
  qty_after_transaction: NumericLike
  valuation_rate: NumericLike
}

export interface WarehouseStockLedgerData {
  items: WarehouseStockLedgerItem[]
  total: number
  page: number
  page_size: number
}

export interface WarehouseStockSummaryQuery {
  company?: string
  warehouse?: string
  item_code?: string
}

export interface WarehouseStockSummaryItem {
  company: string
  warehouse: string
  item_code: string
  actual_qty: NumericLike
  projected_qty: NumericLike
  reserved_qty: NumericLike
  ordered_qty: NumericLike
  reorder_level?: NumericLike | null
  safety_stock?: NumericLike | null
  threshold_missing: boolean
  is_below_reorder: boolean
  is_below_safety: boolean
}

export interface WarehouseManagementItem {
  warehouse_code: string
  warehouse_name: string
  warehouse_type: string
  manager: string
  status: 'normal' | 'warning' | 'disabled'
  capacity_qty: NumericLike
  used_qty: NumericLike
  utilization_rate: NumericLike
}

export interface WarehouseMaterialInventoryItem {
  material_code: string
  material_name: string
  material_category: string
  warehouse: string
  location: string
  qty: NumericLike
  amount: NumericLike
  status: 'normal' | 'warning' | 'disabled'
}

export interface WarehouseStockSummaryData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  items: WarehouseStockSummaryItem[]
  warehouse_management?: WarehouseManagementItem[]
  material_inventory?: WarehouseMaterialInventoryItem[]
}

export interface WarehouseOtherInboundQuery {
  company?: string
  warehouse?: string
  item_code?: string
  status?: 'pending' | 'received' | 'closed' | ''
}

export interface WarehouseOtherInboundItem {
  inbound_no: string
  supplier: string
  material_code: string
  material_name: string
  warehouse: string
  location: string
  qty: NumericLike
  amount: NumericLike
  inbound_date: string
  source_doc_no: string
  operator: string
  status: 'pending' | 'received' | 'closed'
}

export interface WarehouseOtherInboundData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  status?: string | null
  items: WarehouseOtherInboundItem[]
}

export interface WarehousePurchaseReturnOutboundQuery {
  company?: string
  warehouse?: string
  item_code?: string
  status?: 'pending' | 'returned' | 'closed' | ''
}

export interface WarehousePurchaseReturnOutboundItem {
  outbound_no: string
  supplier: string
  material_code: string
  material_name: string
  warehouse: string
  location: string
  qty: NumericLike
  amount: NumericLike
  outbound_date: string
  source_doc_no: string
  operator: string
  status: 'pending' | 'returned' | 'closed'
}

export interface WarehousePurchaseReturnOutboundData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  status?: string | null
  items: WarehousePurchaseReturnOutboundItem[]
}

export interface WarehouseFactoryReturnMaterialReportQuery {
  company?: string
  warehouse?: string
  item_code?: string
  status?: 'pending' | 'confirmed' | 'closed' | ''
}

export interface WarehouseFactoryReturnMaterialReportItem {
  report_no: string
  factory_name: string
  material_code: string
  material_name: string
  warehouse: string
  location: string
  planned_return_qty: NumericLike
  returned_qty: NumericLike
  pending_qty: NumericLike
  report_date: string
  source_doc_no: string
  operator: string
  status: 'pending' | 'confirmed' | 'closed'
}

export interface WarehouseFactoryReturnMaterialReportData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  status?: string | null
  items: WarehouseFactoryReturnMaterialReportItem[]
}

export interface WarehouseSemiFinishedOutboundQuery {
  company?: string
  warehouse?: string
  item_code?: string
  status?: 'pending' | 'confirmed' | 'closed' | ''
}

export interface WarehouseSemiFinishedOutboundItem {
  outbound_no: string
  source_doc_no: string
  semi_finished_code: string
  semi_finished_name: string
  warehouse: string
  location: string
  qty: NumericLike
  amount: NumericLike
  outbound_date: string
  destination: string
  operator: string
  status: 'pending' | 'confirmed' | 'closed'
}

export interface WarehouseSemiFinishedOutboundData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  status?: string | null
  items: WarehouseSemiFinishedOutboundItem[]
}

export interface WarehouseAlertsQuery {
  company?: string
  warehouse?: string
  item_code?: string
  alert_type?: 'low_stock' | 'below_safety' | 'overstock' | 'stale_stock' | ''
}

export interface WarehouseAlertItem {
  company: string
  warehouse: string
  item_code: string
  alert_type: string
  current_qty: NumericLike
  threshold_qty?: NumericLike | null
  gap_qty?: NumericLike | null
  last_movement_date?: string | null
  severity: string
}

export interface WarehouseAlertsData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  alert_type?: string | null
  items: WarehouseAlertItem[]
}

export interface WarehouseBatchListQuery {
  company?: string
  warehouse?: string
  item_code?: string
  batch_no?: string
  page?: number
  page_size?: number
}

export interface WarehouseBatchItem {
  company: string
  batch_no: string
  item_code: string
  warehouse: string
  manufacturing_date?: string | null
  expiry_date?: string | null
  disabled: boolean
  qty: NumericLike
}

export interface WarehouseBatchListData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  batch_no?: string | null
  total: number
  items: WarehouseBatchItem[]
}

export interface WarehouseSerialNumberListQuery {
  company?: string
  warehouse?: string
  item_code?: string
  batch_no?: string
  serial_no?: string
  page?: number
  page_size?: number
}

export interface WarehouseSerialNumberItem {
  company: string
  serial_no: string
  item_code: string
  warehouse: string
  batch_no?: string | null
  status?: string | null
  delivery_document_no?: string | null
  purchase_document_no?: string | null
}

export interface WarehouseSerialNumberListData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  batch_no?: string | null
  serial_no?: string | null
  total: number
  items: WarehouseSerialNumberItem[]
}

export interface WarehouseTraceabilityQuery {
  company?: string
  warehouse?: string
  item_code?: string
  batch_no?: string
  serial_no?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface WarehouseTraceabilityItem {
  company: string
  warehouse: string
  item_code: string
  posting_date: string
  voucher_type?: string | null
  voucher_no?: string | null
  actual_qty: NumericLike
  qty_after_transaction: NumericLike
  batch_no?: string | null
  serial_no?: string | null
}

export interface WarehouseTraceabilityData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  batch_no?: string | null
  serial_no?: string | null
  total: number
  page: number
  page_size: number
  items: WarehouseTraceabilityItem[]
}

export interface WarehouseFinishedGoodsInboundCandidatesQuery {
  company: string
  item_code?: string
}

export interface WarehouseFinishedGoodsInboundCandidateItem {
  source_id: string
  source_label: string
  item_code: string
  qty: NumericLike
  uom: string
  disabled: boolean
  disabled_reason?: string | null
}

export interface WarehouseFinishedGoodsInboundCandidatesData {
  company?: string | null
  show_completed_forced: boolean
  disabled_entry_label: string
  disabled_entry_reason: string
  allocation_contract: string
  items: WarehouseFinishedGoodsInboundCandidateItem[]
}

export interface WarehouseStockEntryDraftItemPayload {
  item_code: string
  qty: NumericLike
  uom: string
  batch_no?: string | null
  serial_no?: string | null
  source_warehouse?: string | null
  target_warehouse?: string | null
}

export interface WarehouseStockEntryDraftCreatePayload {
  company: string
  purpose: 'Material Issue' | 'Material Receipt' | 'Material Transfer'
  source_type: string
  source_id: string
  source_ref: string
  warehouse: string
  item_code: string
  operation: 'create_stock_entry_draft'
  quantity: NumericLike
  business_date: string
  status_action: 'create'
  scenario_tag: string
  finished_goods_source_id?: string | null
  source_warehouse?: string | null
  target_warehouse?: string | null
  items: WarehouseStockEntryDraftItemPayload[]
  idempotency_key: string
}

export interface WarehouseStockEntryDraftCancelPayload {
  reason: string
  idempotency_key: string
  source_ref: string
  warehouse: string
  item_code: string
  operation: 'cancel_stock_entry_draft'
  quantity: NumericLike
  business_date: string
  status_action: 'cancel'
  scenario_tag: string
}

export interface WarehouseWriteMeta {
  requestId?: string
}

export interface WarehouseStockEntryRequestIdInput {
  scenarioTag: string
  operation: 'create_stock_entry_draft' | 'cancel_stock_entry_draft'
  idempotencyKey: string
  sourceRef: string
  warehouse: string
  itemCode: string
  quantity: NumericLike
  businessDate: string
  statusAction: 'create' | 'cancel'
}

const WAREHOUSE_STOCK_ENTRY_SCENARIO_PATTERN = /^Z003-WAREHOUSE-\d{8}-\d{3}$/
const REQUEST_ID_SAFE_PATTERN = /^[A-Za-z0-9_.-]{1,64}$/

const fnvCarrierCode = (value: string, length = 3): string => {
  let hashValue = 2166136261
  const normalized = value.trim()
  const bytes = new TextEncoder().encode(normalized)
  for (const byte of bytes) {
    hashValue ^= byte
    hashValue = Math.imul(hashValue, 16777619) >>> 0
  }
  return hashValue.toString(16).toUpperCase().padStart(8, '0').slice(-length)
}

const normalizeWarehouseOperationCode = (operation: 'create_stock_entry_draft' | 'cancel_stock_entry_draft'): 'C' | 'X' => (
  operation === 'create_stock_entry_draft' ? 'C' : 'X'
)

const normalizeWarehouseStatusActionCode = (statusAction: 'create' | 'cancel'): 'C' | 'X' => (
  statusAction === 'create' ? 'C' : 'X'
)

export const buildWarehouseScenarioTag = (): string => {
  const now = new Date()
  const day = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
  const seq = `${Math.floor(Math.random() * 1000)}`.padStart(3, '0')
  return `Z003-WAREHOUSE-${day}-${seq}`
}

export const ensureWarehouseScenarioTag = (value: string): string => {
  const normalized = value.trim()
  if (WAREHOUSE_STOCK_ENTRY_SCENARIO_PATTERN.test(normalized)) return normalized
  return buildWarehouseScenarioTag()
}

export const buildWarehouseStockEntryRequestId = (input: WarehouseStockEntryRequestIdInput): string => {
  const scenarioTag = ensureWarehouseScenarioTag(input.scenarioTag)
  const operationCode = normalizeWarehouseOperationCode(input.operation)
  const statusActionCode = normalizeWarehouseStatusActionCode(input.statusAction)
  const requestId = `${scenarioTag}-RW-${operationCode}-${fnvCarrierCode(input.idempotencyKey)}-${fnvCarrierCode(input.sourceRef)}-${fnvCarrierCode(input.warehouse)}-${fnvCarrierCode(input.itemCode)}-${fnvCarrierCode(String(input.quantity))}-${fnvCarrierCode(input.businessDate)}-${fnvCarrierCode(statusActionCode)}`
  if (!REQUEST_ID_SAFE_PATTERN.test(requestId)) {
    throw new Error('request_id 编码非法')
  }
  return requestId
}

export interface WarehouseInventoryCountItemCreatePayload {
  item_code: string
  batch_no?: string | null
  serial_no?: string | null
  system_qty: NumericLike
  counted_qty: NumericLike
  variance_reason?: string | null
}

export interface WarehouseInventoryCountCreatePayload {
  company: string
  warehouse: string
  count_date: string
  idempotency_key: string
  source_ref: string
  items: WarehouseInventoryCountItemCreatePayload[]
  remark?: string | null
}

export interface WarehouseInventoryCountVarianceReviewItemPayload {
  item_id: number
  review_status: 'accepted' | 'rejected'
  variance_reason?: string | null
}

export interface WarehouseInventoryCountVarianceReviewPayload {
  items: WarehouseInventoryCountVarianceReviewItemPayload[]
}

export interface WarehouseInventoryCountCancelPayload {
  reason: string
}

export interface WarehouseInventoryCountItemData {
  id: number
  count_id: number
  item_code: string
  batch_no?: string | null
  serial_no?: string | null
  system_qty: NumericLike
  counted_qty: NumericLike
  variance_qty: NumericLike
  variance_reason?: string | null
  review_status: 'pending' | 'accepted' | 'rejected'
}

export interface WarehouseInventoryCountVarianceStatsData {
  total_items: number
  variance_items: number
  pending_review_items: number
  accepted_items: number
  rejected_items: number
}

export interface WarehouseInventoryCountData {
  id: number
  company: string
  warehouse: string
  status: 'draft' | 'counted' | 'variance_review' | 'confirmed' | 'cancelled'
  count_no: string
  count_date: string
  created_by: string
  created_at: string
  submitted_by?: string | null
  submitted_at?: string | null
  reviewed_by?: string | null
  reviewed_at?: string | null
  cancelled_by?: string | null
  cancelled_at?: string | null
  cancel_reason?: string | null
  remark?: string | null
  items: WarehouseInventoryCountItemData[]
  variance_stats: WarehouseInventoryCountVarianceStatsData
}

export interface WarehouseInventoryCountListData {
  total: number
  items: WarehouseInventoryCountData[]
}

export interface WarehouseStockEntryOutboxStatusData {
  draft_id: number
  event_id: number
  event_type: string
  status: 'in_pending' | 'processing' | 'succeeded' | 'failed' | 'dead' | 'cancelled'
  retry_count: number
  external_ref?: string | null
  error_message?: string | null
  created_at: string
  processed_at?: string | null
}

export interface WarehouseStockEntryDraftItemData {
  id: number
  draft_id: number
  item_code: string
  qty: NumericLike
  uom: string
  batch_no?: string | null
  serial_no?: string | null
  source_warehouse?: string | null
  target_warehouse?: string | null
}

export interface WarehouseStockEntryDraftData {
  id: number
  company: string
  purpose: string
  source_type: string
  source_id: string
  source_warehouse?: string | null
  target_warehouse?: string | null
  status: 'draft' | 'pending_outbox' | 'cancelled'
  created_by: string
  created_at: string
  cancelled_by?: string | null
  cancelled_at?: string | null
  cancel_reason?: string | null
  idempotency_key: string
  event_key: string
  allocation_mode?: 'strict_alloc' | 'zero_placeholder_fallback' | null
  strict_failure_reason?: string | null
  show_completed_forced?: boolean | null
  items: WarehouseStockEntryDraftItemData[]
  outbox?: WarehouseStockEntryOutboxStatusData | null
}

export const fetchWarehouseStockLedger = async (
  query: WarehouseStockLedgerQuery,
): Promise<ApiResponse<WarehouseStockLedgerData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<WarehouseStockLedgerData>(`/api/warehouse/stock-ledger?${queryString}`)
}

export const fetchWarehouseStockSummary = async (
  query: WarehouseStockSummaryQuery,
): Promise<ApiResponse<WarehouseStockSummaryData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
  })
  return request<WarehouseStockSummaryData>(`/api/warehouse/stock-summary?${queryString}`)
}

export const fetchWarehouseAlerts = async (
  query: WarehouseAlertsQuery,
): Promise<ApiResponse<WarehouseAlertsData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    alert_type: query.alert_type,
  })
  return request<WarehouseAlertsData>(`/api/warehouse/alerts?${queryString}`)
}

export const fetchWarehouseBatches = async (
  query: WarehouseBatchListQuery,
): Promise<ApiResponse<WarehouseBatchListData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    batch_no: query.batch_no,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<WarehouseBatchListData>(`/api/warehouse/batches?${queryString}`)
}

export const fetchWarehouseSerialNumbers = async (
  query: WarehouseSerialNumberListQuery,
): Promise<ApiResponse<WarehouseSerialNumberListData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    batch_no: query.batch_no,
    serial_no: query.serial_no,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<WarehouseSerialNumberListData>(`/api/warehouse/serial-numbers?${queryString}`)
}

export const fetchWarehouseTraceability = async (
  query: WarehouseTraceabilityQuery,
): Promise<ApiResponse<WarehouseTraceabilityData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    batch_no: query.batch_no,
    serial_no: query.serial_no,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<WarehouseTraceabilityData>(`/api/warehouse/traceability?${queryString}`)
}

export const fetchWarehouseOtherInbound = async (
  query: WarehouseOtherInboundQuery,
): Promise<ApiResponse<WarehouseOtherInboundData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    status: query.status,
  })
  return request<WarehouseOtherInboundData>(`/api/warehouse/other-inbound?${queryString}`)
}

export const fetchWarehousePurchaseReturnOutbound = async (
  query: WarehousePurchaseReturnOutboundQuery,
): Promise<ApiResponse<WarehousePurchaseReturnOutboundData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    status: query.status,
  })
  return request<WarehousePurchaseReturnOutboundData>(`/api/warehouse/purchase-return-outbound?${queryString}`)
}

export const fetchWarehouseFactoryReturnMaterialReport = async (
  query: WarehouseFactoryReturnMaterialReportQuery,
): Promise<ApiResponse<WarehouseFactoryReturnMaterialReportData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    status: query.status,
  })
  return request<WarehouseFactoryReturnMaterialReportData>(
    `/api/warehouse/factory-return-material-report?${queryString}`,
  )
}

export const fetchWarehouseSemiFinishedOutbound = async (
  query: WarehouseSemiFinishedOutboundQuery,
): Promise<ApiResponse<WarehouseSemiFinishedOutboundData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    status: query.status,
  })
  return request<WarehouseSemiFinishedOutboundData>(`/api/warehouse/semi-finished-outbound?${queryString}`)
}

export const fetchWarehouseFinishedGoodsInboundCandidates = async (
  query: WarehouseFinishedGoodsInboundCandidatesQuery,
): Promise<ApiResponse<WarehouseFinishedGoodsInboundCandidatesData>> => {
  const queryString = toQuery({
    company: query.company,
    item_code: query.item_code,
  })
  return request<WarehouseFinishedGoodsInboundCandidatesData>(
    `/api/warehouse/finished-goods-inbound-candidates?${queryString}`,
  )
}

export const createWarehouseStockEntryDraft = async (
  payload: WarehouseStockEntryDraftCreatePayload,
  meta?: WarehouseWriteMeta,
): Promise<ApiResponse<WarehouseStockEntryDraftData>> => {
  return request<WarehouseStockEntryDraftData>('/api/warehouse/stock-entry-drafts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
}

export const fetchWarehouseStockEntryDraft = async (
  draftId: number,
): Promise<ApiResponse<WarehouseStockEntryDraftData>> => {
  return request<WarehouseStockEntryDraftData>(`/api/warehouse/stock-entry-drafts/${draftId}`)
}

export const cancelWarehouseStockEntryDraft = async (
  draftId: number,
  payload: WarehouseStockEntryDraftCancelPayload,
  meta?: WarehouseWriteMeta,
): Promise<ApiResponse<WarehouseStockEntryDraftData>> => {
  return request<WarehouseStockEntryDraftData>(`/api/warehouse/stock-entry-drafts/${draftId}/cancel`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
}

export const fetchWarehouseStockEntryOutboxStatus = async (
  draftId: number,
): Promise<ApiResponse<WarehouseStockEntryOutboxStatusData>> => {
  return request<WarehouseStockEntryOutboxStatusData>(`/api/warehouse/stock-entry-drafts/${draftId}/outbox-status`)
}

export interface WarehouseInventoryCountListQuery {
  company?: string
  warehouse?: string
  status?: 'draft' | 'counted' | 'variance_review' | 'confirmed' | 'cancelled' | ''
  from_date?: string
  to_date?: string
  item_code?: string
}

export const createWarehouseInventoryCount = async (
  payload: WarehouseInventoryCountCreatePayload,
  meta?: WarehouseWriteMeta,
): Promise<ApiResponse<WarehouseInventoryCountData>> => {
  return request<WarehouseInventoryCountData>('/api/warehouse/inventory-counts', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
}

export const submitWarehouseInventoryCount = async (
  countId: number,
  meta?: WarehouseWriteMeta,
): Promise<ApiResponse<WarehouseInventoryCountData>> => {
  return request<WarehouseInventoryCountData>(`/api/warehouse/inventory-counts/${countId}/submit`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify({}),
  })
}

export const varianceReviewWarehouseInventoryCount = async (
  countId: number,
  payload: WarehouseInventoryCountVarianceReviewPayload,
  meta?: WarehouseWriteMeta,
): Promise<ApiResponse<WarehouseInventoryCountData>> => {
  return request<WarehouseInventoryCountData>(`/api/warehouse/inventory-counts/${countId}/variance-review`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
}

export const confirmWarehouseInventoryCount = async (
  countId: number,
  meta?: WarehouseWriteMeta,
): Promise<ApiResponse<WarehouseInventoryCountData>> => {
  return request<WarehouseInventoryCountData>(`/api/warehouse/inventory-counts/${countId}/confirm`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify({}),
  })
}

export const cancelWarehouseInventoryCount = async (
  countId: number,
  payload: WarehouseInventoryCountCancelPayload,
  meta?: WarehouseWriteMeta,
): Promise<ApiResponse<WarehouseInventoryCountData>> => {
  return request<WarehouseInventoryCountData>(`/api/warehouse/inventory-counts/${countId}/cancel`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
}

export const fetchWarehouseInventoryCount = async (
  countId: number,
): Promise<ApiResponse<WarehouseInventoryCountData>> => {
  return request<WarehouseInventoryCountData>(`/api/warehouse/inventory-counts/${countId}`)
}

export const fetchWarehouseInventoryCounts = async (
  query: WarehouseInventoryCountListQuery,
): Promise<ApiResponse<WarehouseInventoryCountListData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    status: query.status,
    from_date: query.from_date,
    to_date: query.to_date,
    item_code: query.item_code,
  })
  return request<WarehouseInventoryCountListData>(`/api/warehouse/inventory-counts?${queryString}`)
}
