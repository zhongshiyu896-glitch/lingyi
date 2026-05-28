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
  'z042-report-parity-source-trace',
  'z042-report-export-guard-matrix',
  'z042-report-fallback-explanation',
  'z043-report-export-eligibility',
  'z043-report-source-grouping',
  'z043-report-disabled-download-reason',
  'z043-report-final-route-link',
  'z044-report-source-readback-group',
  'z044-report-export-lock-reason',
  'z044-report-disabled-download-readback',
  'z044-report-final-route-readback',
  'z044-report-parity-entry-audit',
  'z044-report-readonly-write-guard',
  'z044-report-catalog-eligibility-table',
  'z044-report-write-success-blocker',
  'z045-report-source-lock-readback',
  'z045-report-download-denial-reason',
  'z045-report-final-route-audit',
  'z045-report-catalog-readonly-index',
  'z045-report-export-safety-badge',
  'z045-report-guarded-download-matrix',
  'z045-report-network-write-blocker',
  'z045-report-write-success-blocker',
]

const REPORT_PARITY_GUARDS = [
  'guarded:readonly-report-export',
  'guarded:report-finance-download-readonly',
  'guarded:report-collaboration-download-readonly',
  'guarded:report-detail-export-readonly',
  'guarded:z042-report-export-guard-matrix',
  'guarded:z043-report-export-eligibility-readonly',
  'guarded:z043-report-disabled-download-reason',
  'guarded:z044-report-export-lock-readonly',
  'guarded:z044-report-download-readback-readonly',
  'guarded:z044-report-write-success-blocker',
  'guarded:z045-report-export-denied-readonly',
  'guarded:z045-report-finance-download-denied',
  'guarded:z045-report-collaboration-download-denied',
  'guarded:z045-report-detail-export-denied',
  'guarded:z045-report-write-success-blocker',
  'dataReadonlyBoundary=true',
  'dataWriteRequestSuccessAllowed=false',
  'dataRealWriteActionAdded=false',
]

const REPORT_PARITY_CATALOG_ITEM: ReportCatalogItem = {
  report_key: 'finance_plan_report',
  name: '财务报表与协同报表 parity 只读目录',
  source_modules: ['finance', 'collaboration_report'],
  report_type: 'financial',
  required_filters: ['company', 'from_date', 'to_date'],
  optional_filters: ['customer_keyword', 'employee_keyword', 'department', 'parity'],
  metric_summary: [
    '财务报表旧入口映射',
    '协同报表旧入口映射',
    'Z042 parity source trace',
    '导出 guard matrix',
    'readonly fallback explanation',
    'Z043 source 分组',
    'Z043 导出资格原因',
    'Z043 禁用下载说明',
    'Z043 catalog final route 关联',
    'Z044 报表来源分组 readback',
    'Z044 导出锁定原因',
    'Z044 下载禁用 readback',
    'Z044 final catalog route 关联',
    'Z045 来源分组锁定 readback',
    'Z045 下载禁用原因可见',
    'Z045 导出锁定提示',
    'Z045 final catalog route readback',
  ],
  permission_action: 'report:read',
  status: 'readonly',
  ui_placeholders: REPORT_PARITY_ANCHORS,
  ui_buttons: [
    '报表导出',
    '财务下载',
    '协同下载',
    '明细导出',
    '财务报表下载',
    '协同报表下载',
    '明细查看后的导出',
    'Z044 导出锁定原因',
    'Z044 下载禁用 readback',
    'Z045 来源分组锁定',
    'Z045 下载禁用原因',
    'Z045 导出锁定提示',
    ...REPORT_PARITY_GUARDS,
  ],
  ui_table_headers: [
    'report-parity-route-state',
    'z042-report-parity-source-trace',
    'z042-report-export-guard-matrix',
    'z042-report-fallback-explanation',
    'z043-report-source-grouping',
    'z043-report-export-eligibility',
    'z043-report-disabled-download-reason',
    'z043-report-final-route-link',
    'z044-report-source-readback-group',
    'z044-report-export-lock-reason',
    'z044-report-disabled-download-readback',
    'z044-report-final-route-readback',
    'z044-report-parity-entry-audit',
    'z044-report-readonly-write-guard',
    'z044-report-catalog-eligibility-table',
    'z044-report-write-success-blocker',
    'z045-report-source-lock-readback',
    'z045-report-download-denial-reason',
    'z045-report-final-route-audit',
    'z045-report-catalog-readonly-index',
    'z045-report-export-safety-badge',
    'z045-report-guarded-download-matrix',
    'z045-report-network-write-blocker',
    'z045-report-write-success-blocker',
  ],
  status_tags: ['readonly-parity', ...REPORT_PARITY_ANCHORS, ...REPORT_PARITY_GUARDS],
  preview_rows: [
    {
      'report-parity-route-state': '/financial/financialReport/customerReconciliationReport -> /reports/catalog',
      'z042-report-parity-source-trace': 'finance parity source: customer-reconciliation / financial-process / bank-flow',
      'z042-report-export-guard-matrix': '报表导出 / 财务下载 / 协同下载 / 明细导出 = guarded readonly',
      'z042-report-fallback-explanation': 'auth 401 或接口不可用仅进入 readonly fallback，不代表权限通过或写成功',
      'z043-report-source-grouping': 'source grouping: finance parity entries = customer reconciliation / process / bank flow',
      'z043-report-export-eligibility': '导出资格原因：readonly catalog only，未授予真实写成功链路',
      'z043-report-disabled-download-reason': '禁用下载说明：报表导出、财务下载、明细导出保持 guarded/readonly',
      'z043-report-final-route-link': '/reports/catalog?z043_final_route=/reports/catalog',
      'z044-report-source-readback-group': '来源分组 readback：finance parity = customer reconciliation / process / bank flow',
      'z044-report-export-lock-reason': '导出锁定原因：report:export 未授权且本地边界只允许 readonly readback',
      'z044-report-disabled-download-readback': '下载禁用 readback：财务下载、协同下载、明细导出保持 disabled/guarded',
      'z044-report-final-route-readback': '/reports/catalog?z044_final_route_readback=/reports/catalog',
      'z044-report-parity-entry-audit': 'parity route audit：4 条旧入口均回到 /reports/catalog',
      'z044-report-readonly-write-guard': 'dataReadonlyBoundary=true; dataWriteRequestSuccessAllowed=false',
      'z044-report-catalog-eligibility-table': 'catalog eligibility：仅展示 readback，不授予导出成功状态',
      'z044-report-write-success-blocker': 'write success blocker：报表导出/下载/明细导出不会形成真实写成功',
      'z045-report-source-lock-readback': '来源分组锁定：finance parity entries = customer reconciliation / financial process / bank flow',
      'z045-report-download-denial-reason': '下载禁用原因：report:export 未授权，财务下载与明细导出保持 disabled/guarded',
      'z045-report-final-route-audit': '/financial/financialReport/customerReconciliationReport -> /reports/catalog',
      'z045-report-catalog-readonly-index': 'readonly catalog index：目录页只展示来源分组与锁定原因，不生成下载任务',
      'z045-report-export-safety-badge': '导出锁定提示：导出按钮仅保留可见 readback，不触发真实写请求',
      'z045-report-guarded-download-matrix': '报表导出 / 财务下载 / 协同下载 / 明细导出 = guarded readonly',
      'z045-report-network-write-blocker': 'network write blocker：write_requests_observed_count=0 expected',
      'z045-report-write-success-blocker': 'write success blocker：dataWriteRequestSuccessAllowed=false; dataRealWriteActionAdded=false',
    },
    {
      'report-parity-route-state': '/reportManage/collaborationReport/factoryProductStockReport -> /reports/catalog',
      'z042-report-parity-source-trace': 'collaboration parity source: factory product stock report',
      'z042-report-export-guard-matrix': 'download/export controls keep dataWriteRequestSuccessAllowed=false',
      'z042-report-fallback-explanation': 'final catalog route remains /reports/catalog with read-only source trace context',
      'z043-report-source-grouping': 'source grouping: collaboration parity entry = factory product stock report',
      'z043-report-export-eligibility': '导出资格原因：协同下载仅展示资格说明，不触发写请求',
      'z043-report-disabled-download-reason': '禁用下载说明：协同下载与明细导出只记录 guard trace',
      'z043-report-final-route-link': '/reports/catalog final route preserved for finance/collaboration parity',
      'z044-report-source-readback-group': '来源分组 readback：collaboration parity = factory product stock report',
      'z044-report-export-lock-reason': '导出锁定原因：协同报表下载只读锁定，等待后续授权',
      'z044-report-disabled-download-readback': '下载禁用 readback：协同下载和明细导出仅保留可见 guard 说明',
      'z044-report-final-route-readback': '/reports/catalog final route readback preserved',
      'z044-report-parity-entry-audit': 'parity route audit：factoryProductStockReport -> /reports/catalog',
      'z044-report-readonly-write-guard': 'dataRealWriteActionAdded=false; guarded readonly only',
      'z044-report-catalog-eligibility-table': 'catalog eligibility：协同来源可见，下载成功不可见也不可写',
      'z044-report-write-success-blocker': 'write success blocker：auth fallback 不等于权限通过或写成功',
      'z045-report-source-lock-readback': '来源分组锁定：collaboration parity entry = factory product stock report',
      'z045-report-download-denial-reason': '下载禁用原因：协同下载未获远端/生产授权，保持 readonly readback',
      'z045-report-final-route-audit': '/reportManage/collaborationReport/factoryProductStockReport -> /reports/catalog',
      'z045-report-catalog-readonly-index': 'readonly catalog index：协同报表来源可见，下载成功状态不可见也不可写',
      'z045-report-export-safety-badge': '导出锁定提示：协同报表下载与明细导出仅展示禁用原因',
      'z045-report-guarded-download-matrix': '财务下载 / 协同下载 / 明细导出 all guarded readonly',
      'z045-report-network-write-blocker': 'network write blocker：auth 401 仅作为 readonly fallback risk',
      'z045-report-write-success-blocker': 'write success blocker：guarded_readonly_not_write_success=true',
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
