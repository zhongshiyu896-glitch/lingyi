import { request, type ApiResponse } from '@/api/request'

export interface ProductionPlanCreatePayload {
  sales_order: string
  sales_order_item?: string
  item_code: string
  bom_id?: number
  planned_qty: number | string
  planned_start_date?: string
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
): Promise<ApiResponse<{ plan_id: number; plan_no: string; status: string; company: string }>> =>
  request<{ plan_id: number; plan_no: string; status: string; company: string }>('/api/production/plans', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
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

export const fetchProductionPlanDetail = async (
  planId: number,
): Promise<ApiResponse<ProductionPlanDetailData>> =>
  request<ProductionPlanDetailData>(`/api/production/plans/${planId}`)

export const checkProductionMaterials = async (
  planId: number,
  payload: ProductionMaterialCheckPayload,
): Promise<ApiResponse<ProductionMaterialCheckData>> =>
  request<ProductionMaterialCheckData>(`/api/production/plans/${planId}/material-check`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const createProductionWorkOrder = async (
  planId: number,
  payload: ProductionCreateWorkOrderPayload,
): Promise<ApiResponse<ProductionCreateWorkOrderData>> =>
  request<ProductionCreateWorkOrderData>(`/api/production/plans/${planId}/create-work-order`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const syncProductionJobCards = async (
  workOrder: string,
): Promise<ApiResponse<ProductionSyncJobCardsData>> =>
  request<ProductionSyncJobCardsData>(`/api/production/work-orders/${encodeURIComponent(workOrder)}/sync-job-cards`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
  })
