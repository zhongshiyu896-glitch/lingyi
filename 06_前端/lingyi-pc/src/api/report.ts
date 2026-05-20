import { request, type ApiResponse } from '@/api/request'

interface ReportCatalogQuery {
  company?: string
  source_module?: string
  report_type?: string
}

interface ReportCatalogItem {
  report_key: string
  name: string
  source_modules: string[]
  report_type: string
  required_filters: string[]
  optional_filters: string[]
  metric_summary: string[]
  permission_action: string
  status: string
  ui_placeholders?: string[]
  ui_buttons?: string[]
  ui_table_headers?: string[]
  status_tags?: string[]
  preview_rows?: Array<Record<string, string>>
}

interface ReportCatalogScope {
  company?: string | null
  source_module?: string | null
  report_type?: string | null
}

interface ReportEmployeeTaskStatisticsQuery {
  company?: string
  department?: string
  task_status?: string
  employee_keyword?: string
  from_date?: string
  to_date?: string
}

interface ReportEmployeeTaskStatisticsItem {
  employee_id: string
  employee_name: string
  department: string
  pending_tasks: number
  in_progress_tasks: number
  completed_tasks: number
  overdue_tasks: number
  completion_rate: string
  latest_task_no: string
  latest_task_title: string
  latest_due_date: string
  updated_at: string
  status: string
}

interface ReportEmployeeTaskStatisticsScope {
  company?: string | null
  department?: string | null
  task_status?: string | null
  employee_keyword?: string | null
  from_date?: string | null
  to_date?: string | null
}

interface ReportEmployeeTaskStatisticsData {
  items: ReportEmployeeTaskStatisticsItem[]
  status_tags: string[]
  ui_buttons: string[]
  ui_table_headers: string[]
  requested_scope: ReportEmployeeTaskStatisticsScope
}

interface ReportApprovalReportQuery {
  company?: string
  approver_keyword?: string
  approval_status?: string
  from_date?: string
  to_date?: string
}

interface ReportApprovalReportItem {
  approval_no: string
  approval_type: string
  related_doc_no: string
  applicant: string
  approver: string
  department: string
  amount: string
  priority: string
  submitted_at: string
  completed_at: string
  status: string
  remark: string
}

interface ReportApprovalReportScope {
  company?: string | null
  approver_keyword?: string | null
  approval_status?: string | null
  from_date?: string | null
  to_date?: string | null
}

interface ReportApprovalReportData {
  items: ReportApprovalReportItem[]
  status_tags: string[]
  ui_buttons: string[]
  ui_table_headers: string[]
  requested_scope: ReportApprovalReportScope
}

interface ReportCatalogListData {
  items: ReportCatalogItem[]
  requested_scope: ReportCatalogScope
}

interface ReportCatalogDetailData {
  item: ReportCatalogItem
  requested_scope: ReportCatalogScope
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

const fetchReportCatalog = (query: ReportCatalogQuery): Promise<ApiResponse<ReportCatalogListData>> => {
  const queryString = toQuery({
    company: query.company,
    source_module: query.source_module,
    report_type: query.report_type,
  })
  const url = queryString ? `/api/reports/catalog?${queryString}` : '/api/reports/catalog'
  return request<ReportCatalogListData>(url)
}

const fetchReportEmployeeTaskStatistics = (
  query: ReportEmployeeTaskStatisticsQuery,
): Promise<ApiResponse<ReportEmployeeTaskStatisticsData>> => {
  const queryString = toQuery({
    company: query.company,
    department: query.department,
    task_status: query.task_status,
    employee_keyword: query.employee_keyword,
    from_date: query.from_date,
    to_date: query.to_date,
  })
  const url = queryString
    ? `/api/reports/employee-task-statistics?${queryString}`
    : '/api/reports/employee-task-statistics'
  return request<ReportEmployeeTaskStatisticsData>(url)
}

const fetchReportApprovalReports = (query: ReportApprovalReportQuery): Promise<ApiResponse<ReportApprovalReportData>> => {
  const queryString = toQuery({
    company: query.company,
    approver_keyword: query.approver_keyword,
    approval_status: query.approval_status,
    from_date: query.from_date,
    to_date: query.to_date,
  })
  const url = queryString ? `/api/reports/approval-reports?${queryString}` : '/api/reports/approval-reports'
  return request<ReportApprovalReportData>(url)
}

const fetchReportCatalogDetail = (
  reportKey: string,
  company?: string,
): Promise<ApiResponse<ReportCatalogDetailData>> => {
  const key = reportKey.trim()
  const queryString = toQuery({ company })
  const url = queryString
    ? `/api/reports/catalog/${encodeURIComponent(key)}?${queryString}`
    : `/api/reports/catalog/${encodeURIComponent(key)}`
  return request<ReportCatalogDetailData>(url)
}

const reportApi = {
  fetchReportCatalog,
  fetchReportEmployeeTaskStatistics,
  fetchReportApprovalReports,
  fetchReportCatalogDetail,
}

export default reportApi
