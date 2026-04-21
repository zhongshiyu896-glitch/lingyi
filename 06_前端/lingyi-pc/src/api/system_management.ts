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

const systemManagementApi = {
  fetchSystemConfigCatalog,
  fetchSystemDictionaryCatalog,
  fetchSystemHealthSummary,
}

export default systemManagementApi
