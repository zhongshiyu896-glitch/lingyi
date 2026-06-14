import { request, type ApiResponse } from '@/api/request'

export interface BomItemPayload {
  material_item_code: string
  color?: string
  size?: string
  qty_per_piece: number
  loss_rate: number
  uom: string
  remark?: string
}

export interface BomOperationPayload {
  process_name: string
  sequence_no: number
  is_subcontract: boolean
  wage_rate?: number
  subcontract_cost_per_piece?: number
  remark?: string
}

export interface BomCreatePayload {
  scenario_tag: string
  idempotency_key: string
  source_ref: string
  item_code: string
  version_no: string
  bom_items: BomItemPayload[]
  operations: BomOperationPayload[]
}

export interface BomUpdatePayload {
  scenario_tag: string
  idempotency_key: string
  source_ref: string
  bom_no: string
  item_code: string
  version_no: string
  bom_items: BomItemPayload[]
  operations: BomOperationPayload[]
}

export interface BomWriteMeta {
  requestId?: string
}

export interface BomWriteCarrierPayload {
  scenario_tag: string
  idempotency_key: string
  source_ref: string
  bom_no: string
  item_code: string
}

export interface BomDeactivatePayload extends BomWriteCarrierPayload {
  reason: string
}

export interface BomExplodePayload extends BomWriteCarrierPayload {
  order_qty: number
  size_ratio: Record<string, number>
}

export interface BomListItem {
  id: number
  bom_no: string
  item_code: string
  version_no: string
  is_default: boolean
  status: string
  effective_date?: string | null
}

export interface BomListData {
  items: BomListItem[]
  total: number
  page: number
  page_size: number
}

export interface BomMaterialGalleryItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  material_item_code: string
  category: string
  color?: string | null
  size?: string | null
  uom: string
  qty_per_piece: string
  loss_rate: string
  status: string
  is_default: boolean
  thumbnail_url?: string | null
}

export interface BomMaterialGalleryData {
  items: BomMaterialGalleryItem[]
  total: number
  page: number
  page_size: number
}

export interface BomFabricItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  material_item_code: string
  fabric_name: string
  color?: string | null
  specification?: string | null
  supplier_name: string
  uom: string
  qty_per_piece: string
  loss_rate: string
  status: string
  is_default: boolean
}

export interface BomFabricData {
  items: BomFabricItem[]
  total: number
  page: number
  page_size: number
}

export interface BomAccessoriesPackagingItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  material_item_code: string
  material_name: string
  category: string
  color?: string | null
  specification?: string | null
  supplier_name: string
  uom: string
  qty_per_piece: string
  loss_rate: string
  status: string
  is_default: boolean
}

export interface BomAccessoriesPackagingData {
  items: BomAccessoriesPackagingItem[]
  total: number
  page: number
  page_size: number
}

export interface BomProcessingTypeItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  process_type_code: string
  process_type_name: string
  process_name: string
  sequence_no: number
  subcontract_mode: string
  pricing_mode: string
  unit_rate: string
  status: string
  is_default: boolean
}

export interface BomProcessingTypeData {
  items: BomProcessingTypeItem[]
  total: number
  page: number
  page_size: number
}

export interface BomMaterialProcessingItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  process_no: string
  process_name: string
  processing_supplier: string
  processing_mode: string
  planned_qty: string
  completed_qty: string
  pending_qty: string
  scrap_qty: string
  uom: string
  due_date?: string | null
  status: string
  is_default: boolean
}

export interface BomMaterialProcessingData {
  items: BomMaterialProcessingItem[]
  total: number
  page: number
  page_size: number
}

export interface BomMaterialProcessingInboundItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  inbound_no: string
  process_no: string
  material_item_code: string
  processing_supplier: string
  warehouse_name: string
  inbound_qty: string
  inspected_qty: string
  pending_inspection_qty: string
  inbound_date?: string | null
  status: string
  is_default: boolean
}

export interface BomMaterialProcessingInboundData {
  items: BomMaterialProcessingInboundItem[]
  total: number
  page: number
  page_size: number
}

export interface BomMaterialDeductionItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  deduction_no: string
  process_no: string
  material_item_code: string
  warehouse_name: string
  deduction_qty: string
  deducted_qty: string
  pending_deduction_qty: string
  deduction_date?: string | null
  status: string
  is_default: boolean
}

export interface BomMaterialDeductionData {
  items: BomMaterialDeductionItem[]
  total: number
  page: number
  page_size: number
}

export interface BomMaterialSalesOutboundItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  outbound_no: string
  sales_order_no: string
  customer_name: string
  warehouse_name: string
  material_item_code: string
  material_name: string
  color?: string | null
  size?: string | null
  batch_no: string
  planned_outbound_qty: string
  outbound_qty: string
  pending_outbound_qty: string
  outbound_date?: string | null
  status: string
  audit_status: string
  applicant_name: string
  updated_at?: string | null
  is_default: boolean
}

export interface BomMaterialSalesOutboundData {
  items: BomMaterialSalesOutboundItem[]
  total: number
  page: number
  page_size: number
}

export interface BomMaterialTypeItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  material_item_code: string
  material_type_code: string
  material_type_name: string
  material_group: string
  applicable_scene: string
  supplier_name: string
  status: string
  is_default: boolean
}

export interface BomMaterialTypeData {
  items: BomMaterialTypeItem[]
  total: number
  page: number
  page_size: number
}

export interface BomMaterialUnitItem {
  id: number
  bom_id: number
  bom_no: string
  item_code: string
  material_item_code: string
  unit_code: string
  unit_name: string
  base_unit: string
  conversion_text: string
  precision: number
  status: string
  is_default: boolean
}

export interface BomMaterialUnitData {
  items: BomMaterialUnitItem[]
  total: number
  page: number
  page_size: number
}

export interface BomPurchaseOrderItem {
  id: number
  bom_id: number
  purchase_no: string
  supplier_name: string
  item_code: string
  material_item_code: string
  material_name: string
  qty: string
  uom: string
  unit_price: string
  total_amount: string
  expected_delivery_date?: string | null
  status: string
  bom_no: string
}

export interface BomPurchaseOrderData {
  items: BomPurchaseOrderItem[]
  total: number
  page: number
  page_size: number
}

export interface BomDetailData {
  bom: {
    id: number
    bom_no: string
    item_code: string
    version_no: string
    is_default: boolean
    status: string
    effective_date?: string | null
  }
  items: Array<{
    id: number
    material_item_code: string
    color?: string | null
    size?: string | null
    qty_per_piece: string
    loss_rate: string
    uom: string
    remark?: string | null
  }>
  operations: Array<{
    id: number
    process_name: string
    sequence_no: number
    is_subcontract: boolean
    wage_rate?: string | null
    subcontract_cost_per_piece?: string | null
    remark?: string | null
  }>
}

export interface BomExplodeData {
  material_requirements: Array<{
    material_item_code: string
    color?: string | null
    size?: string | null
    uom: string
    qty: string
  }>
  operation_costs: Array<{
    process_name: string
    is_subcontract: boolean
    unit_cost: string
    total_cost: string
  }>
  total_material_qty: string
  total_operation_cost: string
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

export const createBom = (payload: BomCreatePayload, meta?: BomWriteMeta): Promise<ApiResponse<{ name: string }>> =>
  request('/api/bom/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })

export const fetchBomList = (params: {
  item_code?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomListData>> => request(`/api/bom/?${toQuery(params)}`)

export const fetchBomMaterialGallery = (params: {
  item_code?: string
  material_item_code?: string
  color?: string
  size?: string
  category?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomMaterialGalleryData>> =>
  request(`/api/bom/material-gallery?${toQuery(params)}`)

export const fetchBomFabrics = (params: {
  item_code?: string
  material_item_code?: string
  fabric_name?: string
  color?: string
  specification?: string
  supplier_name?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomFabricData>> => request(`/api/bom/fabrics?${toQuery(params)}`)

export const fetchBomAccessoriesPackaging = (params: {
  item_code?: string
  material_item_code?: string
  material_name?: string
  category?: string
  supplier_name?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomAccessoriesPackagingData>> =>
  request(`/api/bom/accessories-packaging?${toQuery(params)}`)

export const fetchBomProcessingTypes = (params: {
  item_code?: string
  process_type_name?: string
  process_name?: string
  subcontract_mode?: string
  pricing_mode?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomProcessingTypeData>> =>
  request(`/api/bom/processing-types?${toQuery(params)}`)

export const fetchBomMaterialProcessing = (params: {
  item_code?: string
  process_no?: string
  process_name?: string
  processing_supplier?: string
  processing_mode?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomMaterialProcessingData>> =>
  request(`/api/bom/material-processing?${toQuery(params)}`)

export const fetchBomMaterialProcessingInbound = (params: {
  item_code?: string
  inbound_no?: string
  material_item_code?: string
  processing_supplier?: string
  warehouse_name?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomMaterialProcessingInboundData>> =>
  request(`/api/bom/material-processing-inbound?${toQuery(params)}`)

export const fetchBomMaterialDeduction = (params: {
  item_code?: string
  deduction_no?: string
  material_item_code?: string
  warehouse_name?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomMaterialDeductionData>> =>
  request(`/api/bom/material-deduction?${toQuery(params)}`)

export const fetchBomMaterialSalesOutbound = (params: {
  item_code?: string
  outbound_no?: string
  sales_order_no?: string
  customer_name?: string
  warehouse_name?: string
  material_item_code?: string
  status?: string
  audit_status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomMaterialSalesOutboundData>> =>
  request(`/api/bom/material-sales-outbound?${toQuery(params)}`)

export const fetchBomMaterialTypes = (params: {
  item_code?: string
  material_item_code?: string
  material_type_name?: string
  material_group?: string
  applicable_scene?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomMaterialTypeData>> =>
  request(`/api/bom/material-types?${toQuery(params)}`)

export const fetchBomMaterialUnits = (params: {
  item_code?: string
  material_item_code?: string
  unit_name?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomMaterialUnitData>> =>
  request(`/api/bom/material-units?${toQuery(params)}`)

export const fetchBomPurchaseOrders = (params: {
  purchase_no?: string
  supplier_name?: string
  material_keyword?: string
  status?: string
  delivery_date_from?: string
  delivery_date_to?: string
  min_qty?: number
  max_qty?: number
  min_amount?: number
  max_amount?: number
  page: number
  page_size: number
}): Promise<ApiResponse<BomPurchaseOrderData>> =>
  request(`/api/bom/purchase-orders?${toQuery(params)}`)

export const fetchBomDetail = (bomId: number): Promise<ApiResponse<BomDetailData>> =>
  request(`/api/bom/${bomId}`)

export const updateBomDraft = (
  bomId: number,
  payload: BomUpdatePayload,
  meta?: BomWriteMeta,
): Promise<ApiResponse<{ name: string; status: string; updated_at: string }>> =>
  request(`/api/bom/${bomId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })

export const setDefaultBom = (
  bomId: number,
  payload: BomWriteCarrierPayload,
  meta?: BomWriteMeta,
): Promise<ApiResponse<{ name: string; item_code: string; is_default: boolean }>> =>
  request(`/api/bom/${bomId}/set-default`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })

export const activateBom = (
  bomId: number,
  payload: BomWriteCarrierPayload,
  meta?: BomWriteMeta,
): Promise<ApiResponse<{ name: string; status: string; effective_date?: string | null }>> =>
  request(`/api/bom/${bomId}/activate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })

export const deactivateBom = (
  bomId: number,
  payload: BomDeactivatePayload,
  meta?: BomWriteMeta,
): Promise<ApiResponse<{ name: string; status: string }>> =>
  request(`/api/bom/${bomId}/deactivate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })

export const explodeBom = (
  bomId: number,
  payload: BomExplodePayload,
  meta?: BomWriteMeta,
): Promise<ApiResponse<BomExplodeData>> =>
  request(`/api/bom/${bomId}/explode`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(meta?.requestId ? { 'X-Request-ID': meta.requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
