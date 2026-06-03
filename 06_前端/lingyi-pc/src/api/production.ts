import { request, type ApiResponse } from '@/api/request'

export interface ProductionPlanCreatePayload {
  sales_order: string
  sales_order_item?: string
  item_code: string
  bom_id?: number
  planned_qty: number | string
  planned_start_date?: string
  scenario_tag: string
  operation: 'create'
  idempotency_key: string
}

export interface ProductionPlanListQuery {
  sales_order?: string
  keyword?: string
  turnover_no?: string
  item_code?: string
  from_date?: string
  to_date?: string
  status?: string
  page: number
  page_size: number
}

export interface ProductionWorkOrderOutboxSummary {
  outbox_id: number
  status: string
  erpnext_work_order?: string | null
  error_code?: string | null
}

export interface ProductionPlanListItem {
  id: number
  plan_no: string
  company: string
  sales_order: string
  sales_order_item: string
  customer?: string | null
  item_code: string
  bom_id: number
  bom_version?: string | null
  planned_qty: string
  planned_start_date?: string | null
  status: string
  latest_work_order_outbox?: ProductionWorkOrderOutboxSummary | null
  created_at: string
}

export interface ProductionPlanListData {
  items: ProductionPlanListItem[]
  total: number
  page: number
  page_size: number
}

export interface LocalReadbackProductionPlanRecord {
  draft_id: number
  plan_no: string
  planned_qty: number
  plan_date: string
  status: string
  state: string
  order_no: string
  style_code: string
}

export interface LocalReadbackProductionSalesOrderRecord {
  object_id: number
  production_plan: LocalReadbackProductionPlanRecord | null
  readback_flags: {
    production_plan_readback_success: boolean
  }
}

export interface LocalReadbackProductionSalesOrderListData {
  scenario_tag: string
  total: number
  records: LocalReadbackProductionSalesOrderRecord[]
}

export interface LocalReadbackProductionPlanListData {
  scenario_tag: string
  total: number
  records: LocalReadbackProductionPlanRecord[]
}

export interface ProductionMaterialCostListQuery {
  sales_order?: string
  keyword?: string
  turnover_no?: string
  material_item_code?: string
  supplier?: string
  from_date?: string
  to_date?: string
  status?: string
  page: number
  page_size: number
}

export interface ProductionMaterialCostListItem {
  plan_id: number
  plan_no: string
  company: string
  sales_order: string
  sales_order_item: string
  item_code: string
  material_item_code: string
  supplier?: string | null
  qty_per_piece: string
  loss_rate: string
  required_qty: string
  estimated_unit_price: string
  estimated_material_cost: string
  currency: string
  status: string
  planned_start_date?: string | null
  checked_at?: string | null
}

export interface ProductionMaterialCostListData {
  items: ProductionMaterialCostListItem[]
  total: number
  page: number
  page_size: number
}

export interface ProductionSalesForecastListQuery {
  sales_order?: string
  keyword?: string
  turnover_no?: string
  item_code?: string
  customer?: string
  from_date?: string
  to_date?: string
  status?: string
  page: number
  page_size: number
}

export interface ProductionSalesForecastListItem {
  plan_id: number
  plan_no: string
  company: string
  sales_order: string
  sales_order_item: string
  customer?: string | null
  item_code: string
  forecast_qty: string
  forecast_unit_price: string
  forecast_amount: string
  currency: string
  delivery_date?: string | null
  status: string
  checked_at?: string | null
}

export interface ProductionSalesForecastListData {
  items: ProductionSalesForecastListItem[]
  total: number
  page: number
  page_size: number
}

export interface ProductionQuoteListQuery {
  quote_no?: string
  sales_order?: string
  keyword?: string
  turnover_no?: string
  item_code?: string
  customer?: string
  from_date?: string
  to_date?: string
  status?: string
  page: number
  page_size: number
}

export interface ProductionQuoteListItem {
  plan_id: number
  quote_no: string
  plan_no: string
  company: string
  sales_order: string
  sales_order_item: string
  customer?: string | null
  item_code: string
  quote_qty: string
  quote_unit_price: string
  quote_amount: string
  currency: string
  quoted_at?: string | null
  delivery_date?: string | null
  status: string
}

export interface ProductionQuoteListData {
  items: ProductionQuoteListItem[]
  total: number
  page: number
  page_size: number
}

export interface ProductionFollowupTemplateListQuery {
  template_no?: string
  template_name?: string
  template_type?: string
  item_code?: string
  keyword?: string
  from_date?: string
  to_date?: string
  status?: string
  page: number
  page_size: number
}

export interface ProductionFollowupTemplateListItem {
  template_id: number
  template_no: string
  template_name: string
  template_type: string
  trigger_node: string
  followup_role: string
  followup_frequency: string
  sla_hours: number
  item_code: string
  company: string
  status: string
  updated_at: string
}

export interface ProductionFollowupTemplateListData {
  items: ProductionFollowupTemplateListItem[]
  total: number
  page: number
  page_size: number
}

export interface ProductionOrderIOQuantityListQuery {
  sales_order?: string
  keyword?: string
  turnover_no?: string
  item_code?: string
  customer?: string
  from_date?: string
  to_date?: string
  status?: string
  io_status?: string
  page: number
  page_size: number
}

export interface ProductionOrderIOQuantityListItem {
  plan_id: number
  plan_no: string
  company: string
  sales_order: string
  sales_order_item: string
  customer?: string | null
  item_code: string
  ordered_qty: string
  inbound_qty: string
  outbound_qty: string
  pending_inbound_qty: string
  pending_outbound_qty: string
  inbound_progress: string
  outbound_progress: string
  io_status: string
  status: string
  planned_start_date?: string | null
  updated_at?: string | null
}

export interface ProductionOrderIOQuantityListData {
  items: ProductionOrderIOQuantityListItem[]
  total: number
  page: number
  page_size: number
}

export interface ProductionSalespersonPerformanceListQuery {
  salesperson?: string
  keyword?: string
  item_code?: string
  customer?: string
  status?: string
  performance_status?: string
  from_date?: string
  to_date?: string
  page: number
  page_size: number
}

export interface ProductionSalespersonPerformanceListItem {
  plan_id: number
  plan_no: string
  company: string
  salesperson: string
  sales_order: string
  sales_order_item: string
  customer?: string | null
  item_code: string
  ordered_qty: string
  completed_qty: string
  completion_rate: string
  settled_amount: string
  pending_amount: string
  currency: string
  performance_status: string
  status: string
  updated_at?: string | null
}

export interface ProductionSalespersonPerformanceListData {
  items: ProductionSalespersonPerformanceListItem[]
  total: number
  page: number
  page_size: number
}

export interface ProductionPlanMaterialSnapshotItem {
  bom_item_id?: number | null
  material_item_code: string
  warehouse?: string | null
  qty_per_piece: string
  loss_rate: string
  required_qty: string
  available_qty: string
  shortage_qty: string
  checked_at?: string | null
}

export interface ProductionJobCardLinkItem {
  job_card: string
  operation?: string | null
  operation_sequence?: number | null
  company?: string | null
  item_code?: string | null
  expected_qty: string
  completed_qty: string
  erpnext_status?: string | null
  synced_at?: string | null
}

export interface ProductionPlanDetailData {
  id: number
  plan_no: string
  company: string
  sales_order: string
  sales_order_item: string
  customer?: string | null
  item_code: string
  bom_id: number
  bom_version?: string | null
  planned_qty: string
  planned_start_date?: string | null
  status: string
  work_order?: string | null
  erpnext_docstatus?: number | null
  erpnext_status?: string | null
  sync_status?: string | null
  last_synced_at?: string | null
  latest_work_order_outbox?: ProductionWorkOrderOutboxSummary | null
  write_entry_frozen: boolean
  write_entry_frozen_reason?: string | null
  material_snapshots: ProductionPlanMaterialSnapshotItem[]
  job_cards: ProductionJobCardLinkItem[]
  created_at: string
  updated_at: string
}

export interface ProductionMaterialCheckPayload {
  warehouse: string
  idempotency_key: string
  scenario_tag: string
  operation: 'material_check'
  plan_id: number
  sales_order: string
  sales_order_item: string
  item_code: string
  bom_id: number
  request_id: string
}

export interface ProductionMaterialCheckData {
  plan_id: number
  snapshot_count: number
  items: ProductionPlanMaterialSnapshotItem[]
}

export interface ProductionCreateWorkOrderPayload {
  fg_warehouse: string
  wip_warehouse: string
  start_date: string
  idempotency_key: string
  scenario_tag: string
  operation: 'create_work_order'
  plan_id: number
  sales_order: string
  sales_order_item: string
  item_code: string
  bom_id: number
  request_id: string
}

export interface ProductionCreateWorkOrderData {
  plan_id: number
  outbox_id: number
  event_key: string
  sync_status: string
  work_order?: string | null
}

export interface ProductionSyncJobCardsData {
  work_order: string
  plan_id: number
  synced_count: number
  items: ProductionJobCardLinkItem[]
}

export interface ProductionSyncJobCardsPayload {
  idempotency_key: string
  scenario_tag: string
  operation: 'sync_job_cards'
  plan_id: number
  plan_no_or_work_order: string
  company: string
  item_code: string
  source_ref: string
  request_id: string
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

export const createProductionPlan = async (
  payload: ProductionPlanCreatePayload,
  requestId?: string,
): Promise<ApiResponse<{ plan_id: number; plan_no: string; status: string; company: string }>> =>
  request<{ plan_id: number; plan_no: string; status: string; company: string }>('/api/production/plans', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(requestId ? { 'X-Request-ID': requestId } : {}),
    },
    body: JSON.stringify(payload),
  })

export const fetchProductionPlans = async (
  params: ProductionPlanListQuery,
): Promise<ApiResponse<ProductionPlanListData>> => {
  const query = toQuery({
    sales_order: params.sales_order,
    keyword: params.keyword,
    turnover_no: params.turnover_no,
    item_code: params.item_code,
    from_date: params.from_date,
    to_date: params.to_date,
    status: params.status,
    page: params.page,
    page_size: params.page_size,
  })
  return request<ProductionPlanListData>(`/api/production/plans?${query}`)
}

export const fetchProductionMaterialCostDetails = async (
  params: ProductionMaterialCostListQuery,
): Promise<ApiResponse<ProductionMaterialCostListData>> => {
  const query = toQuery({
    sales_order: params.sales_order,
    keyword: params.keyword,
    turnover_no: params.turnover_no,
    material_item_code: params.material_item_code,
    supplier: params.supplier,
    from_date: params.from_date,
    to_date: params.to_date,
    status: params.status,
    page: params.page,
    page_size: params.page_size,
  })
  return request<ProductionMaterialCostListData>(`/api/production/material-cost-details?${query}`)
}

export const fetchProductionSalesForecastDetails = async (
  params: ProductionSalesForecastListQuery,
): Promise<ApiResponse<ProductionSalesForecastListData>> => {
  const query = toQuery({
    sales_order: params.sales_order,
    keyword: params.keyword,
    turnover_no: params.turnover_no,
    item_code: params.item_code,
    customer: params.customer,
    from_date: params.from_date,
    to_date: params.to_date,
    status: params.status,
    page: params.page,
    page_size: params.page_size,
  })
  return request<ProductionSalesForecastListData>(`/api/production/sales-forecast-details?${query}`)
}

export const fetchProductionQuotes = async (
  params: ProductionQuoteListQuery,
): Promise<ApiResponse<ProductionQuoteListData>> => {
  const query = toQuery({
    quote_no: params.quote_no,
    sales_order: params.sales_order,
    keyword: params.keyword,
    turnover_no: params.turnover_no,
    item_code: params.item_code,
    customer: params.customer,
    from_date: params.from_date,
    to_date: params.to_date,
    status: params.status,
    page: params.page,
    page_size: params.page_size,
  })
  return request<ProductionQuoteListData>(`/api/production/quotes?${query}`)
}

export const fetchProductionFollowupTemplates = async (
  params: ProductionFollowupTemplateListQuery,
): Promise<ApiResponse<ProductionFollowupTemplateListData>> => {
  const query = toQuery({
    template_no: params.template_no,
    template_name: params.template_name,
    template_type: params.template_type,
    item_code: params.item_code,
    keyword: params.keyword,
    from_date: params.from_date,
    to_date: params.to_date,
    status: params.status,
    page: params.page,
    page_size: params.page_size,
  })
  return request<ProductionFollowupTemplateListData>(`/api/production/followup-templates?${query}`)
}

export const fetchProductionOrderIOQuantities = async (
  params: ProductionOrderIOQuantityListQuery,
): Promise<ApiResponse<ProductionOrderIOQuantityListData>> => {
  const query = toQuery({
    sales_order: params.sales_order,
    keyword: params.keyword,
    turnover_no: params.turnover_no,
    item_code: params.item_code,
    customer: params.customer,
    from_date: params.from_date,
    to_date: params.to_date,
    status: params.status,
    io_status: params.io_status,
    page: params.page,
    page_size: params.page_size,
  })
  return request<ProductionOrderIOQuantityListData>(`/api/production/order-io-quantities?${query}`)
}

export const fetchProductionSalespersonPerformance = async (
  params: ProductionSalespersonPerformanceListQuery,
): Promise<ApiResponse<ProductionSalespersonPerformanceListData>> => {
  const query = toQuery({
    salesperson: params.salesperson,
    keyword: params.keyword,
    item_code: params.item_code,
    customer: params.customer,
    status: params.status,
    performance_status: params.performance_status,
    from_date: params.from_date,
    to_date: params.to_date,
    page: params.page,
    page_size: params.page_size,
  })
  return request<ProductionSalespersonPerformanceListData>(`/api/production/salesperson-performance?${query}`)
}

export const fetchProductionPlanDetail = async (
  planId: number,
): Promise<ApiResponse<ProductionPlanDetailData>> =>
  request<ProductionPlanDetailData>(`/api/production/plans/${planId}`)

export const fetchLocalReadbackSalesOrders = async (
  scenarioTag: string,
): Promise<ApiResponse<LocalReadbackProductionSalesOrderListData>> => {
  const query = toQuery({ scenario_tag: scenarioTag })
  return request<LocalReadbackProductionSalesOrderListData>(`/api/local-dev/sales-orders?${query}`)
}

export const fetchLocalReadbackProductionPlans = async (
  scenarioTag: string,
): Promise<ApiResponse<LocalReadbackProductionPlanListData>> => {
  const query = toQuery({ scenario_tag: scenarioTag })
  return request<LocalReadbackProductionPlanListData>(`/api/local-dev/production-plans?${query}`)
}

export const checkProductionMaterials = async (
  planId: number,
  payload: ProductionMaterialCheckPayload,
  requestId?: string,
): Promise<ApiResponse<ProductionMaterialCheckData>> =>
  request<ProductionMaterialCheckData>(`/api/production/plans/${planId}/material-check`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(requestId ? { 'X-Request-ID': requestId } : {}),
    },
    body: JSON.stringify(payload),
  })

export const createProductionWorkOrder = async (
  planId: number,
  payload: ProductionCreateWorkOrderPayload,
  requestId?: string,
): Promise<ApiResponse<ProductionCreateWorkOrderData>> =>
  request<ProductionCreateWorkOrderData>(`/api/production/plans/${planId}/create-work-order`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(requestId ? { 'X-Request-ID': requestId } : {}),
    },
    body: JSON.stringify(payload),
  })

export const syncProductionJobCards = async (
  workOrder: string,
  payload: ProductionSyncJobCardsPayload,
  requestId?: string,
): Promise<ApiResponse<ProductionSyncJobCardsData>> =>
  request<ProductionSyncJobCardsData>(`/api/production/work-orders/${encodeURIComponent(workOrder)}/sync-job-cards`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(requestId ? { 'X-Request-ID': requestId } : {}),
    },
    body: JSON.stringify(payload),
  })
