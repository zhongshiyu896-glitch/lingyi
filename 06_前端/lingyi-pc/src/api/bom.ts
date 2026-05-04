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
  item_code: string
  version_no: string
  bom_items: BomItemPayload[]
  operations: BomOperationPayload[]
}

export interface BomUpdatePayload {
  version_no: string
  bom_items: BomItemPayload[]
  operations: BomOperationPayload[]
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

export const createBom = (payload: BomCreatePayload): Promise<ApiResponse<{ name: string }>> =>
  request('/api/bom/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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
): Promise<ApiResponse<{ name: string; status: string; updated_at: string }>> =>
  request(`/api/bom/${bomId}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const setDefaultBom = (bomId: number): Promise<ApiResponse<{ name: string; item_code: string; is_default: boolean }>> =>
  request(`/api/bom/${bomId}/set-default`, { method: 'POST' })

export const activateBom = (
  bomId: number,
): Promise<ApiResponse<{ name: string; status: string; effective_date?: string | null }>> =>
  request(`/api/bom/${bomId}/activate`, { method: 'POST' })

export const deactivateBom = (bomId: number, reason: string): Promise<ApiResponse<{ name: string; status: string }>> =>
  request(`/api/bom/${bomId}/deactivate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ reason }),
  })

export const explodeBom = (
  bomId: number,
  payload: { order_qty: number; size_ratio: Record<string, number> },
): Promise<ApiResponse<BomExplodeData>> =>
  request(`/api/bom/${bomId}/explode`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
