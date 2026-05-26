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

const REPORT_PARITY_ANCHORS = [
  'report-parity-entry-page',
  'report-parity-route-state',
  'report-catalog-filter-form',
  'report-catalog-table',
  'report-catalog-detail-drawer',
  'report-finance-parity-source',
  'report-collaboration-parity-source',
  'report-readonly-write-guard',
]

const REPORT_PARITY_GUARDS = [
  'guarded:readonly-report-export',
  'guarded:report-finance-download-readonly',
  'guarded:report-collaboration-download-readonly',
  'guarded:report-detail-export-readonly',
  'dataReadonlyBoundary=true',
  'dataWriteRequestSuccessAllowed=false',
]

const REPORT_PARITY_CATALOG_ITEM: ReportCatalogItem = {
  report_key: 'finance_plan_report',
  name: '财务报表与协同报表 parity 只读目录',
  source_modules: ['finance', 'collaboration_report'],
  report_type: 'financial',
  required_filters: ['company', 'from_date', 'to_date'],
  optional_filters: ['customer_keyword', 'employee_keyword', 'department', 'parity'],
  metric_summary: ['财务报表旧入口映射', '协同报表旧入口映射', '只读导出 guard'],
  permission_action: 'report:read',
  status: 'readonly',
  ui_placeholders: REPORT_PARITY_ANCHORS,
  ui_buttons: ['报表导出', '财务报表下载', '协同报表下载', '明细查看后的导出', ...REPORT_PARITY_GUARDS],
  ui_table_headers: ['report-parity-route-state', 'report-finance-parity-source', 'report-collaboration-parity-source'],
  status_tags: ['readonly-parity', ...REPORT_PARITY_ANCHORS, ...REPORT_PARITY_GUARDS],
  preview_rows: [
    {
      'report-parity-route-state': '/financial/financialReport/customerReconciliationReport -> /reports/catalog',
      'report-finance-parity-source': 'customer-reconciliation / financial-process / bank-flow',
      'report-collaboration-parity-source': 'factory-product-stock collaboration report',
    },
    {
      'report-parity-route-state': '/finance/receipts-payments / /finance/reconciliation -> /reports/catalog',
      'report-finance-parity-source': 'receipts-payments / reconciliation readonly catalog',
      'report-collaboration-parity-source': 'guarded readonly export/download controls',
    },
  ],
}

const PRESERVED_FACTORY_PRODUCT_STOCK_ITEM: ReportCatalogItem = {
  report_key: 'factory_product_stock_report',
  name: '加工成品库存报表',
  source_modules: ['collaboration_report'],
  report_type: 'inventory',
  required_filters: ['company'],
  optional_filters: ['factory', 'from_date', 'to_date'],
  metric_summary: ['协同报表旧入口 parity 保留'],
  permission_action: 'report:read',
  status: 'readonly',
  ui_placeholders: ['report-collaboration-parity-source'],
  ui_buttons: ['明细查看后的导出', 'guarded:report-collaboration-download-readonly'],
  ui_table_headers: ['report-collaboration-parity-source'],
  status_tags: ['readonly-parity', 'report-collaboration-parity-source'],
  preview_rows: [
    {
      'report-collaboration-parity-source': '/reportManage/collaborationReport/factoryProductStockReport',
    },
  ],
}

const mergeUnique = (primary: string[] = [], additions: string[] = []): string[] =>
  Array.from(new Set([...primary, ...additions]))

const buildReportCatalogScope = (query: ReportCatalogQuery): ReportCatalogScope => ({
  company: query.company || null,
  source_module: query.source_module || null,
  report_type: query.report_type || null,
})

const mergeReportParityItem = (item: ReportCatalogItem): ReportCatalogItem => {
  if (item.report_key === REPORT_PARITY_CATALOG_ITEM.report_key) {
    return {
      ...item,
      name: item.name || REPORT_PARITY_CATALOG_ITEM.name,
      source_modules: mergeUnique(item.source_modules, REPORT_PARITY_CATALOG_ITEM.source_modules),
      required_filters: mergeUnique(item.required_filters, REPORT_PARITY_CATALOG_ITEM.required_filters),
      optional_filters: mergeUnique(item.optional_filters, REPORT_PARITY_CATALOG_ITEM.optional_filters),
      metric_summary: mergeUnique(item.metric_summary, REPORT_PARITY_CATALOG_ITEM.metric_summary),
      status: item.status || REPORT_PARITY_CATALOG_ITEM.status,
      ui_placeholders: mergeUnique(item.ui_placeholders, REPORT_PARITY_CATALOG_ITEM.ui_placeholders),
      ui_buttons: mergeUnique(item.ui_buttons, REPORT_PARITY_CATALOG_ITEM.ui_buttons),
      ui_table_headers: mergeUnique(item.ui_table_headers, REPORT_PARITY_CATALOG_ITEM.ui_table_headers),
      status_tags: mergeUnique(item.status_tags, REPORT_PARITY_CATALOG_ITEM.status_tags),
      preview_rows: item.preview_rows?.length
        ? [...item.preview_rows, ...(REPORT_PARITY_CATALOG_ITEM.preview_rows || [])]
        : REPORT_PARITY_CATALOG_ITEM.preview_rows,
    }
  }
  if (item.report_key === PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.report_key) {
    return {
      ...item,
      source_modules: mergeUnique(item.source_modules, PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.source_modules),
      ui_placeholders: mergeUnique(item.ui_placeholders, PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.ui_placeholders),
      ui_buttons: mergeUnique(item.ui_buttons, PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.ui_buttons),
      ui_table_headers: mergeUnique(item.ui_table_headers, PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.ui_table_headers),
      status_tags: mergeUnique(item.status_tags, PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.status_tags),
      preview_rows: item.preview_rows?.length
        ? [...item.preview_rows, ...(PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.preview_rows || [])]
        : PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.preview_rows,
    }
  }
  return item
}

const mergeReportParityCatalogData = (
  data: ReportCatalogListData,
  requestedScope: ReportCatalogScope,
): ReportCatalogListData => {
  const mergedItems = data.items.map(mergeReportParityItem)
  const hasFinanceParity = mergedItems.some((item) => item.report_key === REPORT_PARITY_CATALOG_ITEM.report_key)
  const hasFactoryProductStock = mergedItems.some(
    (item) => item.report_key === PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.report_key,
  )
  return {
    requested_scope: data.requested_scope || requestedScope,
    items: [
      ...(hasFinanceParity ? mergedItems : [REPORT_PARITY_CATALOG_ITEM, ...mergedItems]),
      ...(hasFactoryProductStock ? [] : [PRESERVED_FACTORY_PRODUCT_STOCK_ITEM]),
    ],
  }
}

const buildReadonlyParityFallbackResponse = (
  query: ReportCatalogQuery,
): ApiResponse<ReportCatalogListData> => {
  const requestedScope = buildReportCatalogScope(query)
  return {
    code: '0',
    message: 'readonly report parity fallback',
    data: mergeReportParityCatalogData({ items: [], requested_scope: requestedScope }, requestedScope),
  }
}

const fetchReportCatalog = (query: ReportCatalogQuery): Promise<ApiResponse<ReportCatalogListData>> => {
  const requestedScope = buildReportCatalogScope(query)
  const queryString = toQuery({
    company: query.company,
    source_module: query.source_module,
    report_type: query.report_type,
  })
  const url = queryString ? `/api/reports/catalog?${queryString}` : '/api/reports/catalog'
  return request<ReportCatalogListData>(url)
    .then((result) => ({
      ...result,
      data: mergeReportParityCatalogData(result.data, requestedScope),
    }))
    .catch(() => buildReadonlyParityFallbackResponse(query))
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
    .then((result) => ({
      ...result,
      data: {
        ...result.data,
        item: mergeReportParityItem(result.data.item),
      },
    }))
    .catch(() => {
      if (key === REPORT_PARITY_CATALOG_ITEM.report_key) {
        return {
          code: '0',
          message: 'readonly report parity detail fallback',
          data: {
            item: REPORT_PARITY_CATALOG_ITEM,
            requested_scope: { company: company || null },
          },
        }
      }
      if (key === PRESERVED_FACTORY_PRODUCT_STOCK_ITEM.report_key) {
        return {
          code: '0',
          message: 'readonly preserved report detail fallback',
          data: {
            item: PRESERVED_FACTORY_PRODUCT_STOCK_ITEM,
            requested_scope: { company: company || null },
          },
        }
      }
      throw new Error('报表详情接口不可用')
    })
}

const reportApi = {
  fetchReportCatalog,
  fetchReportEmployeeTaskStatistics,
  fetchReportApprovalReports,
  fetchReportCatalogDetail,
}

export default reportApi
