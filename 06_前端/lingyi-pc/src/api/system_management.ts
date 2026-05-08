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

export interface SystemOrganizationFrameworkQuery {
  org_level?: string
  status?: '生效' | '待生效' | '停用'
  keyword?: string
  effective_start_date?: string
  effective_end_date?: string
}

export interface SystemOrganizationFrameworkAction {
  action_key: string
  label: string
  guarded: boolean
  disabled_reason: string
}

export interface SystemOrganizationFrameworkItem {
  org_code: string
  org_name: string
  parent_org_name: string
  manager_name: string
  org_level: string
  headcount_planned: number
  headcount_on_duty: number
  status: string
  effective_date: string
  updated_at: string
  remark: string
  actions: SystemOrganizationFrameworkAction[]
}

export interface SystemOrganizationFrameworkData {
  items: SystemOrganizationFrameworkItem[]
  total: number
  org_level_options: string[]
  status_tags: string[]
  ui_buttons: string[]
  ui_table_headers: string[]
}

export interface SystemIntegrationPlatformQuery {
  platform_type?: string
  status?: '运行中' | '告警' | '停用'
  endpoint_mode?: string
  keyword?: string
  updated_start_date?: string
  updated_end_date?: string
}

export interface SystemIntegrationPlatformAction {
  action_key: string
  label: string
  guarded: boolean
  disabled_reason: string
}

export interface SystemIntegrationPlatformItem {
  platform_code: string
  platform_name: string
  platform_type: string
  endpoint_mode: string
  connector: string
  webhook_url_masked: string
  sync_direction: string
  status: string
  last_sync_at: string
  retry_policy: string
  updated_at: string
  remark: string
  actions: SystemIntegrationPlatformAction[]
}

export interface SystemIntegrationPlatformData {
  items: SystemIntegrationPlatformItem[]
  total: number
  platform_type_options: string[]
  endpoint_mode_options: string[]
  status_tags: string[]
  ui_buttons: string[]
  ui_table_headers: string[]
}

export interface SystemAnnouncementQuery {
  category?: string
  status?: '已发布' | '草稿' | '已撤回'
  target_scope?: string
  keyword?: string
  published_start_date?: string
  published_end_date?: string
}

export interface SystemAnnouncementAction {
  action_key: string
  label: string
  guarded: boolean
  disabled_reason: string
}

export interface SystemAnnouncementItem {
  announcement_code: string
  title: string
  category: string
  target_scope: string
  publish_status: string
  published_at: string
  expires_at: string
  priority: string
  owner: string
  updated_at: string
  remark: string
  actions: SystemAnnouncementAction[]
}

export interface SystemAnnouncementData {
  items: SystemAnnouncementItem[]
  total: number
  category_options: string[]
  status_tags: string[]
  ui_buttons: string[]
  ui_table_headers: string[]
}

export interface SystemOperationLogQuery {
  module?: string
  operation_type?: string
  result_status?: '成功' | '失败' | '部分成功'
  operator?: string
  keyword?: string
  operated_start_date?: string
  operated_end_date?: string
}

export interface SystemOperationLogAction {
  action_key: string
  label: string
  guarded: boolean
  disabled_reason: string
}

export interface SystemOperationLogItem {
  log_id: string
  module: string
  operation_type: string
  operation_name: string
  info: string
  operator: string
  result_status: string
  operated_at: string
  client_ip: string
  trace_id: string
  remark: string
  actions: SystemOperationLogAction[]
}

export interface SystemOperationLogData {
  items: SystemOperationLogItem[]
  total: number
  module_options: string[]
  operation_type_options: string[]
  status_tags: string[]
  ui_buttons: string[]
  ui_table_headers: string[]
}

export interface SystemDocumentCodeQuery {
  document_type?: string
  status?: '启用' | '停用' | '草稿'
  keyword?: string
  updated_start_date?: string
  updated_end_date?: string
}

export interface SystemDocumentCodeAction {
  action_key: string
  label: string
  guarded: boolean
  disabled_reason: string
}

export interface SystemDocumentCodeItem {
  document_code_id: string
  document_name: string
  document_type: string
  prefix: string
  serial_rule: string
  current_sequence: number
  status: string
  reset_cycle: string
  owner: string
  updated_at: string
  remark: string
  actions: SystemDocumentCodeAction[]
}

export interface SystemDocumentCodeData {
  items: SystemDocumentCodeItem[]
  total: number
  document_type_options: string[]
  status_tags: string[]
  ui_buttons: string[]
  ui_table_headers: string[]
}

export interface SystemMessageNotificationSettingsQuery {
  channel?: string
  status?: '启用' | '停用' | '草稿'
  target_scope?: string
  keyword?: string
  updated_start_date?: string
  updated_end_date?: string
}

export interface SystemMessageNotificationSettingAction {
  action_key: string
  label: string
  guarded: boolean
  disabled_reason: string
}

export interface SystemMessageNotificationSettingItem {
  setting_code: string
  setting_name: string
  channel: string
  target_scope: string
  digest_mode: string
  trigger_events: string
  status: string
  owner: string
  updated_at: string
  remark: string
  actions: SystemMessageNotificationSettingAction[]
}

export interface SystemMessageNotificationSettingsData {
  items: SystemMessageNotificationSettingItem[]
  total: number
  channel_options: string[]
  status_tags: string[]
  ui_buttons: string[]
  ui_table_headers: string[]
}

export interface SystemPreferenceSettingsQuery {
  preference_scope?: string
  status?: '启用' | '停用' | '草稿'
  keyword?: string
  updated_start_date?: string
  updated_end_date?: string
}

export interface SystemPreferenceSettingAction {
  action_key: string
  label: string
  guarded: boolean
  disabled_reason: string
}

export interface SystemPreferenceSettingItem {
  setting_code: string
  setting_name: string
  preference_scope: string
  value_type: string
  current_value_masked: string
  effective_level: string
  status: string
  owner: string
  updated_at: string
  remark: string
  actions: SystemPreferenceSettingAction[]
}

export interface SystemPreferenceSettingsData {
  items: SystemPreferenceSettingItem[]
  total: number
  preference_scope_options: string[]
  status_tags: string[]
  ui_buttons: string[]
  ui_table_headers: string[]
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

export const fetchSystemOrganizationFrameworks = async (
  query: SystemOrganizationFrameworkQuery,
): Promise<ApiResponse<SystemOrganizationFrameworkData>> => {
  const queryString = toQuery({
    org_level: query.org_level,
    status: query.status,
    keyword: query.keyword,
    effective_start_date: query.effective_start_date,
    effective_end_date: query.effective_end_date,
  })
  const url = queryString ? `/api/system/organization-frameworks?${queryString}` : '/api/system/organization-frameworks'
  return request<SystemOrganizationFrameworkData>(url)
}

export const fetchSystemIntegrationPlatforms = async (
  query: SystemIntegrationPlatformQuery,
): Promise<ApiResponse<SystemIntegrationPlatformData>> => {
  const queryString = toQuery({
    platform_type: query.platform_type,
    status: query.status,
    endpoint_mode: query.endpoint_mode,
    keyword: query.keyword,
    updated_start_date: query.updated_start_date,
    updated_end_date: query.updated_end_date,
  })
  const url = queryString ? `/api/system/integration-platforms?${queryString}` : '/api/system/integration-platforms'
  return request<SystemIntegrationPlatformData>(url)
}

export const fetchSystemAnnouncements = async (
  query: SystemAnnouncementQuery,
): Promise<ApiResponse<SystemAnnouncementData>> => {
  const queryString = toQuery({
    category: query.category,
    status: query.status,
    target_scope: query.target_scope,
    keyword: query.keyword,
    published_start_date: query.published_start_date,
    published_end_date: query.published_end_date,
  })
  const url = queryString ? `/api/system/system-announcements?${queryString}` : '/api/system/system-announcements'
  return request<SystemAnnouncementData>(url)
}

export const fetchSystemOperationLogs = async (
  query: SystemOperationLogQuery,
): Promise<ApiResponse<SystemOperationLogData>> => {
  const queryString = toQuery({
    module: query.module,
    operation_type: query.operation_type,
    result_status: query.result_status,
    operator: query.operator,
    keyword: query.keyword,
    operated_start_date: query.operated_start_date,
    operated_end_date: query.operated_end_date,
  })
  const url = queryString ? `/api/system/operation-logs?${queryString}` : '/api/system/operation-logs'
  return request<SystemOperationLogData>(url)
}

export const fetchSystemDocumentCodes = async (
  query: SystemDocumentCodeQuery,
): Promise<ApiResponse<SystemDocumentCodeData>> => {
  const queryString = toQuery({
    document_type: query.document_type,
    status: query.status,
    keyword: query.keyword,
    updated_start_date: query.updated_start_date,
    updated_end_date: query.updated_end_date,
  })
  const url = queryString ? `/api/system/document-codes?${queryString}` : '/api/system/document-codes'
  return request<SystemDocumentCodeData>(url)
}

export const fetchSystemMessageNotificationSettings = async (
  query: SystemMessageNotificationSettingsQuery,
): Promise<ApiResponse<SystemMessageNotificationSettingsData>> => {
  const queryString = toQuery({
    channel: query.channel,
    status: query.status,
    target_scope: query.target_scope,
    keyword: query.keyword,
    updated_start_date: query.updated_start_date,
    updated_end_date: query.updated_end_date,
  })
  const url = queryString
    ? `/api/system/message-notification-settings?${queryString}`
    : '/api/system/message-notification-settings'
  return request<SystemMessageNotificationSettingsData>(url)
}

export const fetchSystemPreferenceSettings = async (
  query: SystemPreferenceSettingsQuery,
): Promise<ApiResponse<SystemPreferenceSettingsData>> => {
  const queryString = toQuery({
    preference_scope: query.preference_scope,
    status: query.status,
    keyword: query.keyword,
    updated_start_date: query.updated_start_date,
    updated_end_date: query.updated_end_date,
  })
  const url = queryString ? `/api/system/preference-settings?${queryString}` : '/api/system/preference-settings'
  return request<SystemPreferenceSettingsData>(url)
}

const systemManagementApi = {
  fetchSystemConfigCatalog,
  fetchSystemDictionaryCatalog,
  fetchSystemHealthSummary,
  fetchSystemApprovalFlows,
  fetchSystemUserCatalog,
  fetchSystemOrganizationFrameworks,
  fetchSystemIntegrationPlatforms,
  fetchSystemAnnouncements,
  fetchSystemOperationLogs,
  fetchSystemDocumentCodes,
  fetchSystemMessageNotificationSettings,
  fetchSystemPreferenceSettings,
}

export default systemManagementApi
