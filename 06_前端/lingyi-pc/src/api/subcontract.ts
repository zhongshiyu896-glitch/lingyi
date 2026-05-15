import { request, type ApiResponse } from '@/api/request'

export type NumericLike = string | number
export type SubcontractWriteOperation =
  | 'create'
  | 'issue_material'
  | 'receive'
  | 'inspect'
  | 'settlement_preview'
  | 'settlement_lock'
  | 'release'

const SUBCONTRACT_SCENARIO_PATTERN = /^Z003-SUBCONTRACT-\d{8}-\d{3}$/
const SUBCONTRACT_SCENARIO_EXTRACT_PATTERN = /Z003-SUBCONTRACT-\d{8}-\d{3}/
const SUBCONTRACT_REQUEST_ID_PATTERN = /^[A-Za-z0-9_.-]{1,64}$/

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
  production_plan_id?: number | null
  work_order?: string | null
  created_at: string
}

export interface SubcontractOrderListData {
  items: SubcontractOrderListItem[]
  total: number
  page: number
  page_size: number
}

export interface SubcontractWriteCarrierPayload {
  request_id: string
  idempotency_key: string
  scenario_tag: string
  source_ref: string
  subcontract_ref: string
  supplier_ref: string
  work_order_ref: string
  operation: SubcontractWriteOperation
  item_code: string
  quantity: NumericLike
  status_action: string
}

export interface SubcontractIssueMaterialItemInput {
  material_item_code: string
  required_qty: NumericLike
  issued_qty: NumericLike
}

export interface SubcontractCreateRequestPayload extends SubcontractWriteCarrierPayload {
  operation: 'create'
  supplier: string
  item_code: string
  company?: string | null
  bom_id: number
  planned_qty: NumericLike
  process_name: string
  sales_order?: string | null
  sales_order_item?: string | null
  production_plan_id?: number | null
  work_order?: string | null
  job_card?: string | null
}

export interface SubcontractCreateResponseData {
  name: string
  company: string
}

export interface SubcontractIssueMaterialRequestPayload extends SubcontractWriteCarrierPayload {
  operation: 'issue_material'
  warehouse: string
  materials: SubcontractIssueMaterialItemInput[]
}

export interface SubcontractIssueMaterialResponseData {
  outbox_id: number
  issue_batch_no: string
  sync_status: string
  stock_entry_name?: string | null
}

export interface SubcontractReceiveRequestPayload extends SubcontractWriteCarrierPayload {
  operation: 'receive'
  receipt_warehouse: string
  received_qty: NumericLike
  item_code: string
  color?: string | null
  size?: string | null
  batch_no?: string | null
  uom?: string | null
}

export interface SubcontractReceiveResponseData {
  outbox_id: number
  receipt_batch_no: string
  sync_status: string
  stock_entry_name?: string | null
}

export interface SubcontractInspectRequestPayload extends SubcontractWriteCarrierPayload {
  operation: 'inspect'
  receipt_batch_no: string
  inspected_qty: NumericLike
  rejected_qty: NumericLike
  deduction_amount_per_piece?: NumericLike
  remark?: string | null
}

export interface SubcontractInspectResponseData {
  inspection_no: string
  receipt_batch_no: string
  inspected_qty: NumericLike
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  rejected_rate: NumericLike
  gross_amount: NumericLike
  deduction_amount: NumericLike
  net_amount: NumericLike
  status: string
}

export interface SubcontractSettlementCandidateListItem {
  inspection_id: number
  settlement_line_key?: string | null
  subcontract_id: number
  subcontract_no: string
  company: string
  supplier: string
  item_code: string
  process_name: string
  receipt_batch_no: string
  inspected_at?: string | null
  inspected_by?: string | null
  inspected_qty: NumericLike
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  rejected_rate: NumericLike
  subcontract_rate: NumericLike
  gross_amount: NumericLike
  deduction_amount: NumericLike
  net_amount: NumericLike
  settlement_status: string
  statement_id?: number | null
  statement_no?: string | null
}

export interface SubcontractSettlementSummary {
  line_count: number
  total_qty: NumericLike
  gross_amount: NumericLike
  deduction_amount: NumericLike
  net_amount: NumericLike
}

export interface SubcontractSettlementCandidatesData {
  items: SubcontractSettlementCandidateListItem[]
  total: number
  page: number
  page_size: number
  summary: SubcontractSettlementSummary
}

export interface SubcontractSettlementPreviewRequestPayload extends SubcontractWriteCarrierPayload {
  operation: 'settlement_preview'
  inspection_ids?: number[]
  company?: string | null
  supplier?: string | null
  from_date?: string | null
  to_date?: string | null
  filter_item_code?: string | null
  process_name?: string | null
}

export interface SubcontractSettlementPreviewData {
  company?: string | null
  supplier?: string | null
  line_count: number
  total_qty: NumericLike
  gross_amount: NumericLike
  deduction_amount: NumericLike
  net_amount: NumericLike
  items: SubcontractSettlementCandidateListItem[]
}

export interface SubcontractSettlementLockRequestPayload extends SubcontractWriteCarrierPayload {
  operation: 'settlement_lock'
  statement_id?: number | null
  statement_no?: string | null
  inspection_ids: number[]
  remark?: string | null
}

export interface SubcontractSettlementLockData {
  operation_id: number
  idempotency_key: string
  idempotent_replay: boolean
  locked_count: number
  gross_amount: NumericLike
  deduction_amount: NumericLike
  net_amount: NumericLike
  locked_items: SubcontractSettlementCandidateListItem[]
}

export interface SubcontractSettlementReleaseRequestPayload extends SubcontractWriteCarrierPayload {
  operation: 'release'
  statement_id?: number | null
  statement_no?: string | null
  inspection_ids: number[]
  reason: string
}

export interface SubcontractSettlementReleaseData {
  operation_id: number
  idempotency_key: string
  idempotent_replay: boolean
  released_count: number
  released_items: SubcontractSettlementCandidateListItem[]
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

const fnvCarrierCode = (value: string): string => {
  const normalized = value.trim()
  let hashValue = 2166136261
  for (let index = 0; index < normalized.length; index += 1) {
    hashValue ^= normalized.charCodeAt(index)
    hashValue = Math.imul(hashValue, 16777619) >>> 0
  }
  return hashValue.toString(16).toUpperCase().padStart(8, '0').slice(-3)
}

const subcontractOperationCode = (operation: SubcontractWriteOperation): 'CR' | 'IM' | 'RV' | 'IN' | 'SP' | 'SL' | 'RL' => {
  if (operation === 'create') return 'CR'
  if (operation === 'issue_material') return 'IM'
  if (operation === 'receive') return 'RV'
  if (operation === 'inspect') return 'IN'
  if (operation === 'settlement_preview') return 'SP'
  if (operation === 'settlement_lock') return 'SL'
  return 'RL'
}

export const buildSubcontractScenarioTag = (): string => {
  const now = new Date()
  const day = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
  const seq = String(Math.floor(Math.random() * 1000)).padStart(3, '0')
  return `Z003-SUBCONTRACT-${day}-${seq}`
}

export const extractSubcontractScenarioTag = (value: string): string | null => {
  const matched = value.trim().match(SUBCONTRACT_SCENARIO_EXTRACT_PATTERN)
  return matched ? matched[0] : null
}

export const ensureSubcontractScenarioTag = (value: string): string => {
  const normalized = value.trim()
  if (SUBCONTRACT_SCENARIO_PATTERN.test(normalized)) {
    return normalized
  }
  return buildSubcontractScenarioTag()
}

export const buildSubcontractRequestId = ({
  scenarioTag,
  operation,
  idempotencyKey,
  sourceRef,
  subcontractRef,
  supplierRef,
  workOrderRef,
  itemCode,
  statusAction,
}: {
  scenarioTag: string
  operation: SubcontractWriteOperation
  idempotencyKey: string
  sourceRef: string
  subcontractRef: string
  supplierRef: string
  workOrderRef: string
  itemCode: string
  statusAction: string
}): string => {
  const normalizedScenarioTag = ensureSubcontractScenarioTag(scenarioTag)
  const requestId = `${normalizedScenarioTag}-SC-${subcontractOperationCode(operation)}-${fnvCarrierCode(idempotencyKey)}-${fnvCarrierCode(sourceRef)}-${fnvCarrierCode(subcontractRef)}-${fnvCarrierCode(supplierRef)}-${fnvCarrierCode(workOrderRef)}-${fnvCarrierCode(itemCode)}-${fnvCarrierCode(statusAction)}`
  if (!SUBCONTRACT_REQUEST_ID_PATTERN.test(requestId)) {
    throw new Error('request_id 编码非法')
  }
  return requestId
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

export const fetchSubcontractSettlementCandidates = async (params: {
  company?: string
  supplier?: string
  item_code?: string
  process_name?: string
  status?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
} = {}): Promise<ApiResponse<SubcontractSettlementCandidatesData>> => {
  const query = toQuery({
    company: params.company,
    supplier: params.supplier,
    item_code: params.item_code,
    process_name: params.process_name,
    status: params.status,
    from_date: params.from_date,
    to_date: params.to_date,
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  })
  return request<SubcontractSettlementCandidatesData>(`/api/subcontract/settlement-candidates${query ? `?${query}` : ''}`)
}

export const createSubcontractOrder = async (
  payload: SubcontractCreateRequestPayload,
): Promise<ApiResponse<SubcontractCreateResponseData>> => {
  return request<SubcontractCreateResponseData>('/api/subcontract/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })
}

export const issueSubcontractMaterial = async (
  orderId: number,
  payload: SubcontractIssueMaterialRequestPayload,
): Promise<ApiResponse<SubcontractIssueMaterialResponseData>> => {
  return request<SubcontractIssueMaterialResponseData>(`/api/subcontract/${orderId}/issue-material`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })
}

export const receiveSubcontractOrder = async (
  orderId: number,
  payload: SubcontractReceiveRequestPayload,
): Promise<ApiResponse<SubcontractReceiveResponseData>> => {
  return request<SubcontractReceiveResponseData>(`/api/subcontract/${orderId}/receive`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })
}

export const inspectSubcontractOrder = async (
  orderId: number,
  payload: SubcontractInspectRequestPayload,
): Promise<ApiResponse<SubcontractInspectResponseData>> => {
  return request<SubcontractInspectResponseData>(`/api/subcontract/${orderId}/inspect`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })
}

export const previewSubcontractSettlement = async (
  payload: SubcontractSettlementPreviewRequestPayload,
): Promise<ApiResponse<SubcontractSettlementPreviewData>> => {
  return request<SubcontractSettlementPreviewData>('/api/subcontract/settlement-preview', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })
}

export const lockSubcontractSettlement = async (
  payload: SubcontractSettlementLockRequestPayload,
): Promise<ApiResponse<SubcontractSettlementLockData>> => {
  return request<SubcontractSettlementLockData>('/api/subcontract/settlement-locks', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })
}

export const releaseSubcontractSettlement = async (
  payload: SubcontractSettlementReleaseRequestPayload,
): Promise<ApiResponse<SubcontractSettlementReleaseData>> => {
  return request<SubcontractSettlementReleaseData>('/api/subcontract/settlement-locks/release', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })
}
