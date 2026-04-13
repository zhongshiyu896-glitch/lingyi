export interface ApiResponse<T> {
  code: string
  message: string
  data: T
  trace_id?: string
}

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

const buildAuthHeaders = (headers?: HeadersInit): Headers => {
  const result = new Headers(headers)
  const storedToken =
    window.localStorage.getItem('LY_AUTH_TOKEN') || window.localStorage.getItem('token') || ''
  if (storedToken) {
    const normalized =
      storedToken.startsWith('Bearer ') || storedToken.startsWith('token ')
        ? storedToken
        : `Bearer ${storedToken}`
    result.set('Authorization', normalized)
  }
  return result
}

const handleAuthError = (code?: string): never => {
  if (code === 'AUTH_FORBIDDEN') {
    throw new Error('无权执行该操作')
  }
  window.alert('登录已失效，请重新登录')
  window.location.href = '/login'
  throw new Error('未登录或 Token 无效')
}

const request = async <T>(url: string, init?: RequestInit): Promise<ApiResponse<T>> => {
  const response = await fetch(url, {
    ...init,
    credentials: 'include',
    headers: buildAuthHeaders(init?.headers),
  })
  const payload = (await response.json()) as ApiResponse<T>
  if (response.status === 401 || payload.code === 'AUTH_UNAUTHORIZED') {
    handleAuthError('AUTH_UNAUTHORIZED')
  }
  if (response.status === 403 || payload.code === 'AUTH_FORBIDDEN') {
    handleAuthError('AUTH_FORBIDDEN')
  }
  if (!response.ok || payload.code !== '0') {
    throw new Error(payload.message || '请求失败')
  }
  return payload
}

export const createBom = (payload: BomCreatePayload): Promise<ApiResponse<{ name: string }>> =>
  request('/api/bom/', {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })

export const fetchBomList = (params: {
  item_code?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<BomListData>> => request(`/api/bom/?${toQuery(params)}`)

export const fetchBomDetail = (bomId: number): Promise<ApiResponse<BomDetailData>> =>
  request(`/api/bom/${bomId}`)

export const updateBomDraft = (
  bomId: number,
  payload: BomUpdatePayload,
): Promise<ApiResponse<{ name: string; status: string; updated_at: string }>> =>
  request(`/api/bom/${bomId}`, {
    method: 'PUT',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })

export const setDefaultBom = (bomId: number): Promise<ApiResponse<{ name: string; item_code: string; is_default: boolean }>> =>
  request(`/api/bom/${bomId}/set-default`, { method: 'POST', headers: buildAuthHeaders() })

export const activateBom = (
  bomId: number,
): Promise<ApiResponse<{ name: string; status: string; effective_date?: string | null }>> =>
  request(`/api/bom/${bomId}/activate`, { method: 'POST', headers: buildAuthHeaders() })

export const deactivateBom = (bomId: number, reason: string): Promise<ApiResponse<{ name: string; status: string }>> =>
  request(`/api/bom/${bomId}/deactivate`, {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ reason }),
  })

export const explodeBom = (
  bomId: number,
  payload: { order_qty: number; size_ratio: Record<string, number> },
): Promise<ApiResponse<BomExplodeData>> =>
  request(`/api/bom/${bomId}/explode`, {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })
