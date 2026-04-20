import { request, requestFile, type ApiResponse } from '@/api/request'

export interface PermissionActionCatalogEntry {
  action: string
  category: string
  is_high_risk: boolean
  ui_exposed: boolean
  description: string
}

export interface PermissionActionCatalogModule {
  module: string
  actions: PermissionActionCatalogEntry[]
}

export interface PermissionActionCatalogData {
  modules: PermissionActionCatalogModule[]
}

export interface PermissionRoleMatrixEntry {
  role: string
  actions: string[]
  modules: string[]
  high_risk_actions: string[]
  ui_hidden_actions: string[]
}

export interface PermissionRoleMatrixData {
  roles: PermissionRoleMatrixEntry[]
}

export interface PermissionSecurityAuditQuery {
  from_date?: string
  to_date?: string
  module?: string
  action?: string
  request_id?: string
  resource_type?: string
  resource_id?: string
  event_type?: string
  user_id?: string
  page?: number
  page_size?: number
  limit?: number
}

export interface PermissionOperationAuditQuery {
  from_date?: string
  to_date?: string
  module?: string
  action?: string
  request_id?: string
  resource_type?: string
  resource_id?: number
  operator?: string
  result?: 'success' | 'failed'
  error_code?: string
  page?: number
  page_size?: number
  limit?: number
}

export interface PermissionSecurityAuditItem {
  id: number
  event_type: string
  module: string
  action?: string | null
  resource_type?: string | null
  resource_id?: string | null
  resource_no?: string | null
  user_id?: string | null
  permission_source?: string | null
  deny_reason: string
  request_method: string
  request_path: string
  request_id: string
  created_at: string
}

export interface PermissionOperationAuditItem {
  id: number
  module: string
  action: string
  operator: string
  resource_type: string
  resource_id?: number | null
  resource_no?: string | null
  result: string
  error_code?: string | null
  request_id?: string | null
  created_at: string
  has_before_data: boolean
  has_after_data: boolean
  before_keys: string[]
  after_keys: string[]
}

export interface PermissionSecurityAuditData {
  items: PermissionSecurityAuditItem[]
  total: number
  page: number
  page_size: number
}

export interface PermissionOperationAuditData {
  items: PermissionOperationAuditItem[]
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

const fetchPermissionActionCatalog = (): Promise<ApiResponse<PermissionActionCatalogData>> => {
  return request<PermissionActionCatalogData>('/api/permissions/actions/catalog')
}

const fetchPermissionRolesMatrix = (): Promise<ApiResponse<PermissionRoleMatrixData>> => {
  return request<PermissionRoleMatrixData>('/api/permissions/roles/matrix')
}

const fetchPermissionSecurityAudit = (
  query: PermissionSecurityAuditQuery,
): Promise<ApiResponse<PermissionSecurityAuditData>> => {
  const queryString = toQuery({ ...query })
  const url = queryString ? `/api/permissions/audit/security?${queryString}` : '/api/permissions/audit/security'
  return request<PermissionSecurityAuditData>(url)
}

const fetchPermissionOperationAudit = (
  query: PermissionOperationAuditQuery,
): Promise<ApiResponse<PermissionOperationAuditData>> => {
  const queryString = toQuery({ ...query })
  const url = queryString ? `/api/permissions/audit/operations?${queryString}` : '/api/permissions/audit/operations'
  return request<PermissionOperationAuditData>(url)
}

const downloadBlobFile = (blob: Blob, filename: string): void => {
  const objectUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(objectUrl)
}

const exportPermissionSecurityAuditCsv = async (query: PermissionSecurityAuditQuery): Promise<void> => {
  const queryString = toQuery({ ...query })
  const url = queryString
    ? `/api/permissions/audit/security/export?${queryString}`
    : '/api/permissions/audit/security/export'
  const { blob, filename } = await requestFile(url, { method: 'GET' }, 'permission_security_audit_export.csv')
  downloadBlobFile(blob, filename)
}

const exportPermissionOperationAuditCsv = async (query: PermissionOperationAuditQuery): Promise<void> => {
  const queryString = toQuery({ ...query })
  const url = queryString
    ? `/api/permissions/audit/operations/export?${queryString}`
    : '/api/permissions/audit/operations/export'
  const { blob, filename } = await requestFile(url, { method: 'GET' }, 'permission_operation_audit_export.csv')
  downloadBlobFile(blob, filename)
}

const permissionGovernanceApi = {
  fetchPermissionActionCatalog,
  fetchPermissionRolesMatrix,
  fetchPermissionSecurityAudit,
  fetchPermissionOperationAudit,
  exportPermissionSecurityAuditCsv,
  exportPermissionOperationAuditCsv,
}

export default permissionGovernanceApi
