import { request, requestFile, type ApiResponse } from '@/api/request'

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
}

interface ReportCatalogScope {
  company?: string | null
  source_module?: string | null
  report_type?: string | null
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

const exportReportCatalogCsv = async (query: ReportCatalogQuery): Promise<void> => {
  const queryString = toQuery({
    company: query.company,
    source_module: query.source_module,
    report_type: query.report_type,
  })
  const url = queryString ? `/api/reports/catalog/export?${queryString}` : '/api/reports/catalog/export'
  const { blob, filename } = await requestFile(url, { method: 'GET' }, 'report_catalog_export.csv')
  const objectUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = objectUrl
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(objectUrl)
}

const reportApi = {
  fetchReportCatalog,
  fetchReportCatalogDetail,
  exportReportCatalogCsv,
}

export default reportApi
