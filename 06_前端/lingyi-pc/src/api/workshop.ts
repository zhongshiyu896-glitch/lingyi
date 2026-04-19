export interface ApiResponse<T> {
  code: string
  message: string
  data: T
}

// Internal worker run-once API is intentionally not exposed to business UI.

export interface WorkshopTicketRegisterPayload {
  ticket_key: string
  job_card: string
  item_code?: string
  employee: string
  process_name: string
  color?: string
  size?: string
  qty: number
  work_date: string
  source: string
  source_ref?: string
}

export interface WorkshopTicketReversalPayload {
  ticket_key: string
  job_card: string
  item_code?: string
  employee: string
  process_name: string
  color?: string
  size?: string
  qty: number
  work_date: string
  original_ticket_id?: number
  reason: string
}

export interface WorkshopTicketData {
  ticket_no: string
  ticket_id: number
  unit_wage: string | number
  wage_amount: string | number
  sync_status: string
  sync_outbox_id?: number | null
  net_qty?: string | number
}

export interface WorkshopTicketRow {
  id: number
  ticket_no: string
  ticket_key: string
  job_card: string
  work_order?: string | null
  bom_id?: number | null
  item_code: string
  employee: string
  process_name: string
  color?: string | null
  size?: string | null
  operation_type: string
  qty: string | number
  unit_wage: string | number
  wage_amount: string | number
  work_date: string
  source: string
  source_ref?: string | null
  sync_status: string
  created_by: string
  created_at: string
}

export interface WorkshopTicketListData {
  items: WorkshopTicketRow[]
  total: number
  page: number
  page_size: number
}

export interface WorkshopDailyWageRow {
  employee: string
  work_date: string
  process_name: string
  item_code?: string | null
  register_qty: string | number
  reversal_qty: string | number
  net_qty: string | number
  wage_amount: string | number
}

export interface WorkshopDailyWageData {
  items: WorkshopDailyWageRow[]
  total: number
  total_amount: string | number
  page: number
  page_size: number
}

export interface WorkshopJobCardSummaryData {
  job_card: string
  register_qty: string | number
  reversal_qty: string | number
  net_qty: string | number
  local_completed_qty: string | number
  sync_status: string
  outbox_status: string
  last_sync_at?: string | null
  last_error_code?: string | null
  last_error_message?: string | null
}

export interface WorkshopWageRateRow {
  id: number
  item_code?: string | null
  company?: string | null
  is_global: boolean
  process_name: string
  wage_rate: string | number
  effective_from: string
  effective_to?: string | null
  status: string
  created_by: string
  created_at: string
  updated_at: string
}

export interface WorkshopWageRateListData {
  items: WorkshopWageRateRow[]
  total: number
  page: number
  page_size: number
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

const buildAuthHeaders = (headers?: HeadersInit): Headers => {
  return new Headers(headers)
}

const handleAuthError = (code?: string): never => {
  if (code === 'AUTH_FORBIDDEN') {
    throw new Error('无权执行该操作')
  }
  window.alert('登录已失效，请重新登录')
  window.location.href = '/login'
  throw new Error('未登录或会话无效')
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

export const registerWorkshopTicket = (
  payload: WorkshopTicketRegisterPayload,
): Promise<ApiResponse<WorkshopTicketData>> =>
  request('/api/workshop/tickets/register', {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })

export const reverseWorkshopTicket = (
  payload: WorkshopTicketReversalPayload,
): Promise<ApiResponse<WorkshopTicketData>> =>
  request('/api/workshop/tickets/reversal', {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })

export const batchWorkshopTickets = (
  tickets: Array<WorkshopTicketRegisterPayload & { operation_type?: 'register' | 'reversal'; reason?: string }>,
): Promise<
  ApiResponse<{
    success_count: number
    failed_count: number
    success_items: WorkshopTicketData[]
    failed_items: Array<{ row_index: number; index?: number; code: string; error_code?: string; message: string; ticket_key: string }>
  }>
> =>
  request('/api/workshop/tickets/batch', {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ tickets }),
  })

export const fetchWorkshopTickets = (params: {
  employee?: string
  job_card?: string
  item_code?: string
  process_name?: string
  operation_type?: string
  work_date?: string
  from_date?: string
  to_date?: string
  page: number
  page_size: number
}): Promise<ApiResponse<WorkshopTicketListData>> =>
  request(`/api/workshop/tickets?${toQuery(params)}`)

export const fetchWorkshopDailyWages = (params: {
  employee?: string
  from_date?: string
  to_date?: string
  process_name?: string
  item_code?: string
  page: number
  page_size: number
}): Promise<ApiResponse<WorkshopDailyWageData>> =>
  request(`/api/workshop/daily-wages?${toQuery(params)}`)

export const fetchWorkshopJobCardSummary = (
  jobCard: string,
): Promise<ApiResponse<WorkshopJobCardSummaryData>> =>
  request(`/api/workshop/job-cards/${encodeURIComponent(jobCard)}/summary`)

export const retryWorkshopJobCardSync = (
  jobCard: string,
): Promise<
  ApiResponse<{
    job_card: string
    local_completed_qty: string | number
    sync_status: string
    sync_outbox_id?: number | null
  }>
> =>
  request(`/api/workshop/job-cards/${encodeURIComponent(jobCard)}/sync`, {
    method: 'POST',
    headers: buildAuthHeaders(),
  })

export const fetchWorkshopWageRates = (params: {
  item_code?: string
  company?: string
  is_global?: boolean
  process_name?: string
  status?: string
  page: number
  page_size: number
}): Promise<ApiResponse<WorkshopWageRateListData>> =>
  request(`/api/workshop/wage-rates?${toQuery(params)}`)

export const createWorkshopWageRate = (payload: {
  item_code?: string
  company?: string
  process_name: string
  wage_rate: number
  effective_from: string
  effective_to?: string | null
}): Promise<ApiResponse<{ id: number; status: string }>> =>
  request('/api/workshop/wage-rates', {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify(payload),
  })

export const deactivateWorkshopWageRate = (
  id: number,
  reason: string,
): Promise<ApiResponse<{ id: number; status: string }>> =>
  request(`/api/workshop/wage-rates/${id}/deactivate`, {
    method: 'POST',
    headers: buildAuthHeaders({ 'Content-Type': 'application/json' }),
    body: JSON.stringify({ reason }),
  })
