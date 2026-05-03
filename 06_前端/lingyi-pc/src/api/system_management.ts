import { request, type ApiResponse } from '@/api/request'

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

export interface SystemConfigCatalogQuery {
  module?: string
  config_group?: string
  source?: string
  is_sensitive?: 'true' | 'false'
}

export interface SystemConfigCatalogItem {
  module: string
  config_key: string
  config_group: string
  description: string
  source: string
  is_sensitive: boolean
  updated_at: string
}

export interface SystemConfigCatalogData {
  items: SystemConfigCatalogItem[]
  total: number
}

export interface SystemDictionaryCatalogQuery {
  dict_type?: string
  status?: 'active' | 'inactive' | 'deprecated'
  source?: string
}

export interface SystemDictionaryCatalogItem {
  dict_type: string
  dict_code: string
  dict_name: string
  status: string
  source: string
  updated_at: string
}

export interface SystemDictionaryCatalogData {
  items: SystemDictionaryCatalogItem[]
  total: number
}

export interface SystemHealthSummaryItem {
  module: string
  status: 'ok' | 'warn' | 'blocked'
  check_name: string
  check_result: string
  generated_at: string
}

export interface SystemHealthSummaryData {
  items: SystemHealthSummaryItem[]
  total: number
  generated_at: string
}

export interface SystemApprovalFlowQuery {
  audit_type?: string
  status?: '启用' | '草稿' | '停用'
  keyword?: string
  start_date?: string
  end_date?: string
}

export interface SystemApprovalFlowAction {
  action_key: string
  label: string
  guarded: boolean
  disabled_reason: string
}

export interface SystemApprovalFlowNode {
  node_key: string
  node_name: string
  approver_rule: string
  status: string
}

export interface SystemApprovalFlowItem {
  flow_key: string
  title: string
  audit_type: string
  status: string
  sender: string
  created_by: string
  created_at: string
  sent_at: string
  last_modified_by: string
  last_modified_at: string
  nodes: SystemApprovalFlowNode[]
  actions: SystemApprovalFlowAction[]
}

export interface SystemApprovalFlowData {
  items: SystemApprovalFlowItem[]
  total: number
  audit_type_options: string[]
}

export interface SystemUserCatalogQuery {
  role?: string
  status?: '启用' | '停用' | '锁定'
  keyword?: string
  start_date?: string
  end_date?: string
}

export interface SystemUserCatalogAction {
  action_key: string
  label: string
  guarded: boolean
  disabled_reason: string
}

export interface SystemUserCatalogItem {
  user_id: string
  username: string
  display_name: string
  role: string
  status: string
  department: string
  last_login_at: string
  updated_at: string
  actions: SystemUserCatalogAction[]
}

export interface SystemUserCatalogData {
  items: SystemUserCatalogItem[]
  total: number
  role_options: string[]
  status_options: string[]
}

export const fetchSystemConfigCatalog = async (
  query: SystemConfigCatalogQuery,
): Promise<ApiResponse<SystemConfigCatalogData>> => {
  const queryString = toQuery({
    module: query.module,
    config_group: query.config_group,
    source: query.source,
    is_sensitive: query.is_sensitive,
  })
  const url = queryString ? `/api/system/configs/catalog?${queryString}` : '/api/system/configs/catalog'
  return request<SystemConfigCatalogData>(url)
}

export const fetchSystemDictionaryCatalog = async (
  query: SystemDictionaryCatalogQuery,
): Promise<ApiResponse<SystemDictionaryCatalogData>> => {
  const queryString = toQuery({
    dict_type: query.dict_type,
    status: query.status,
    source: query.source,
  })
  const url = queryString ? `/api/system/dictionaries/catalog?${queryString}` : '/api/system/dictionaries/catalog'
  return request<SystemDictionaryCatalogData>(url)
}

export const fetchSystemHealthSummary = async (): Promise<ApiResponse<SystemHealthSummaryData>> =>
  request<SystemHealthSummaryData>('/api/system/health/summary')

export const fetchSystemApprovalFlows = async (
  query: SystemApprovalFlowQuery,
): Promise<ApiResponse<SystemApprovalFlowData>> => {
  const queryString = toQuery({
    audit_type: query.audit_type,
    status: query.status,
    keyword: query.keyword,
    start_date: query.start_date,
    end_date: query.end_date,
  })
  const url = queryString ? `/api/system/approval-flows?${queryString}` : '/api/system/approval-flows'
  return request<SystemApprovalFlowData>(url)
}

export const fetchSystemUserCatalog = async (
  query: SystemUserCatalogQuery,
): Promise<ApiResponse<SystemUserCatalogData>> => {
  const queryString = toQuery({
    role: query.role,
    status: query.status,
    keyword: query.keyword,
    start_date: query.start_date,
    end_date: query.end_date,
  })
  const url = queryString ? `/api/system/users/catalog?${queryString}` : '/api/system/users/catalog'
  return request<SystemUserCatalogData>(url)
}

const systemManagementApi = {
  fetchSystemConfigCatalog,
  fetchSystemDictionaryCatalog,
  fetchSystemHealthSummary,
  fetchSystemApprovalFlows,
  fetchSystemUserCatalog,
}

export default systemManagementApi
