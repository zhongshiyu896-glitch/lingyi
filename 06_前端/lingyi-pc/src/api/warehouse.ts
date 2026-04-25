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

export interface WarehouseStockSummaryData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  items: WarehouseStockSummaryItem[]
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
  finished_goods_source_id?: string | null
  source_warehouse?: string | null
  target_warehouse?: string | null
  items: WarehouseStockEntryDraftItemPayload[]
  idempotency_key: string
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
): Promise<ApiResponse<WarehouseStockEntryDraftData>> => {
  return request<WarehouseStockEntryDraftData>('/api/warehouse/stock-entry-drafts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
  reason: string,
): Promise<ApiResponse<WarehouseStockEntryDraftData>> => {
  return request<WarehouseStockEntryDraftData>(`/api/warehouse/stock-entry-drafts/${draftId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })
}

export const fetchWarehouseStockEntryOutboxStatus = async (
  draftId: number,
): Promise<ApiResponse<WarehouseStockEntryOutboxStatusData>> => {
  return request<WarehouseStockEntryOutboxStatusData>(`/api/warehouse/stock-entry-drafts/${draftId}/outbox-status`)
}
