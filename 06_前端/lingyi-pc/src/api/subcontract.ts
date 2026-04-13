import { request, type ApiResponse } from '@/api/request'

export interface SubcontractOrderPayload {
  supplier: string
  item_code: string
  bom_id: number
  planned_qty: number
  process_name: string
}

export interface SubcontractOrderListItem {
  id: number
  subcontract_no: string
  supplier: string
  item_code: string
  company?: string | null
  bom_id: number
  process_name: string
  planned_qty: string
  subcontract_rate: string
  issued_qty: string
  received_qty: string
  inspected_qty: string
  rejected_qty: string
  accepted_qty: string
  gross_amount: string
  deduction_amount: string
  net_amount: string
  status: string
  resource_scope_status: string
  latest_issue_outbox_id?: number | null
  latest_issue_sync_status?: string | null
  latest_issue_stock_entry_name?: string | null
  latest_issue_idempotency_key?: string | null
  latest_issue_error_code?: string | null
  latest_receipt_outbox_id?: number | null
  latest_receipt_sync_status?: string | null
  latest_receipt_stock_entry_name?: string | null
  latest_receipt_idempotency_key?: string | null
  latest_receipt_error_code?: string | null
  created_at: string
}

export interface SubcontractOrderListData {
  items: SubcontractOrderListItem[]
  total: number
  page: number
  page_size: number
}

export interface SubcontractReceiptDetailItem {
  receipt_batch_no: string
  receipt_warehouse?: string | null
  item_code?: string | null
  color?: string | null
  size?: string | null
  batch_no?: string | null
  uom?: string | null
  received_qty: string
  sync_status: string
  stock_entry_name?: string | null
  inspect_status?: string | null
  idempotency_key?: string | null
  received_by?: string | null
  received_at?: string | null
}

export interface SubcontractInspectionDetailItem {
  inspection_no: string
  receipt_batch_no: string
  inspected_qty: string
  accepted_qty: string
  rejected_qty: string
  rejected_rate: string
  subcontract_rate: string
  gross_amount: string
  deduction_amount_per_piece: string
  deduction_amount: string
  net_amount: string
  inspected_by?: string | null
  inspected_at?: string | null
  remark?: string | null
}

export interface SubcontractOrderDetailData extends SubcontractOrderListItem {
  scope_error_code?: string | null
  settlement_status?: string | null
  latest_issue_outbox_id?: number | null
  latest_issue_sync_status?: string | null
  latest_issue_stock_entry_name?: string | null
  latest_issue_idempotency_key?: string | null
  latest_receipt_outbox_id?: number | null
  latest_receipt_sync_status?: string | null
  latest_receipt_stock_entry_name?: string | null
  latest_receipt_idempotency_key?: string | null
  receipts: SubcontractReceiptDetailItem[]
  inspections: SubcontractInspectionDetailItem[]
  updated_at?: string | null
}

const toQuery = (params: Record<string, string | number | undefined>): string => {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      query.append(key, String(value))
    }
  })
  return query.toString()
}

export const createSubcontractOrder = async (
  payload: SubcontractOrderPayload,
): Promise<ApiResponse<{ name: string; company: string }>> => {
  return request<{ name: string; company: string }>('/api/subcontract/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export const fetchSubcontractOrders = async (params: {
  supplier?: string
  status?: string
  from_date?: string
  to_date?: string
  page: number
  page_size: number
}): Promise<ApiResponse<SubcontractOrderListData>> => {
  const query = toQuery(params)
  return request<SubcontractOrderListData>(`/api/subcontract/?${query}`)
}

export const fetchSubcontractOrderDetail = async (orderId: number): Promise<ApiResponse<SubcontractOrderDetailData>> => {
  return request<SubcontractOrderDetailData>(`/api/subcontract/${orderId}`)
}

export const issueSubcontractMaterial = async (
  orderId: number,
  payload: {
    idempotency_key: string
    warehouse: string
    materials?: Array<{ material_item_code: string; required_qty: number; issued_qty: number }>
  },
): Promise<ApiResponse<{ outbox_id: number; issue_batch_no: string; sync_status: string; stock_entry_name: string | null }>> => {
  return request<{
    outbox_id: number
    issue_batch_no: string
    sync_status: string
    stock_entry_name: string | null
  }>(`/api/subcontract/${orderId}/issue-material`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export const retrySubcontractStockSync = async (
  orderId: number,
  payload: {
    outbox_id: number
    stock_action: 'issue' | 'receipt'
    idempotency_key: string
    reason?: string
  },
): Promise<ApiResponse<{ outbox_id: number; stock_action: string; status: string; next_retry_at?: string | null }>> => {
  return request<{
    outbox_id: number
    stock_action: string
    status: string
    next_retry_at?: string | null
  }>(`/api/subcontract/${orderId}/stock-sync/retry`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export const receiveSubcontract = async (
  orderId: number,
  payload: {
    idempotency_key: string
    receipt_warehouse: string
    received_qty: number | string
    color?: string
    size?: string
    batch_no?: string
    uom?: string
  },
): Promise<ApiResponse<{ outbox_id: number; receipt_batch_no: string; sync_status: string; stock_entry_name: string | null }>> => {
  return request<{
    outbox_id: number
    receipt_batch_no: string
    sync_status: string
    stock_entry_name: string | null
  }>(`/api/subcontract/${orderId}/receive`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export const inspectSubcontract = async (
  orderId: number,
  payload: {
    receipt_batch_no: string
    idempotency_key: string
    inspected_qty: number | string
    rejected_qty: number | string
    deduction_amount_per_piece?: number | string
    remark?: string
  },
): Promise<
  ApiResponse<{
    inspection_no: string
    receipt_batch_no: string
    inspected_qty: string
    accepted_qty: string
    rejected_qty: string
    rejected_rate: string
    gross_amount: string
    deduction_amount: string
    net_amount: string
    status: string
  }>
> => {
  return request<{
    inspection_no: string
    receipt_batch_no: string
    inspected_qty: string
    accepted_qty: string
    rejected_qty: string
    rejected_rate: string
    gross_amount: string
    deduction_amount: string
    net_amount: string
    status: string
  }>(`/api/subcontract/${orderId}/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}
