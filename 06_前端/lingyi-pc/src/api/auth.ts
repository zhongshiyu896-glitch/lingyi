export interface ApiResponse<T> {
  code: string
  message: string
  data: T
}

export interface CurrentUserData {
  username: string
  roles: string[]
  is_service_account: boolean
  source: string
}

export interface ActionPermissionData {
  username?: string
  module?: string
  actions: string[]
  status?: string | null
  button_permissions: {
    create: boolean
    update: boolean
    publish: boolean
    deactivate: boolean
    set_default: boolean
    read: boolean
    plan_create?: boolean
    material_check?: boolean
    work_order_create?: boolean
    ticket_register?: boolean
    ticket_reversal?: boolean
    ticket_batch?: boolean
    wage_read?: boolean
    wage_rate_read?: boolean
    wage_rate_read_all?: boolean
    wage_rate_manage?: boolean
    wage_rate_manage_all?: boolean
    job_card_sync?: boolean
    issue_material?: boolean
    receive?: boolean
    inspect?: boolean
    cancel?: boolean
    stock_sync_retry?: boolean
    stock_sync_worker?: boolean
    work_order_worker?: boolean
    job_card_sync_worker?: boolean
  }
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

const request = async <T>(url: string, init?: RequestInit): Promise<ApiResponse<T>> => {
  const response = await fetch(url, {
    ...init,
    credentials: 'include',
    headers: buildAuthHeaders(init?.headers),
  })
  const payload = (await response.json()) as ApiResponse<T>
  if (response.status === 401 || payload.code === 'AUTH_UNAUTHORIZED') {
    window.alert('登录已失效，请重新登录')
    window.location.href = '/login'
    throw new Error('未登录或 Token 无效')
  }
  if (response.status === 403 || payload.code === 'AUTH_FORBIDDEN') {
    throw new Error('无权执行该操作')
  }
  if (!response.ok || payload.code !== '0') {
    throw new Error(payload.message || '请求失败')
  }
  return payload
}

export const fetchCurrentUser = (): Promise<ApiResponse<CurrentUserData>> => request('/api/auth/me')

export const fetchModuleActions = (params: {
  module?: string
  resource_type?: string
  resource_id?: number
}): Promise<ApiResponse<ActionPermissionData>> => {
  const query = new URLSearchParams()
  if (params.module) query.set('module', params.module)
  if (params.resource_type) query.set('resource_type', params.resource_type)
  if (params.resource_id) query.set('resource_id', String(params.resource_id))
  return request(`/api/auth/actions?${query.toString()}`)
}

export const fetchBomActions = (bomId: number): Promise<ApiResponse<ActionPermissionData>> =>
  request(`/api/auth/actions/bom/${bomId}`)
