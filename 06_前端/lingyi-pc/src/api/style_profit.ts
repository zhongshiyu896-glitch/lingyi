import { request, type ApiResponse } from '@/api/request'

type NumericLike = string | number

export interface StyleProfitSnapshotListItem {
  id: number
  snapshot_no: string
  company: string
  item_code: string
  sales_order?: string | null
  from_date?: string | null
  to_date?: string | null
  revenue_status: string
  revenue_amount: NumericLike
  actual_total_cost: NumericLike
  standard_total_cost: NumericLike
  profit_amount: NumericLike
  profit_rate?: NumericLike | null
  snapshot_status: string
  allocation_status: string
  include_provisional_subcontract: boolean
  formula_version: string
  unresolved_count: number
  created_at: string
}

export interface StyleProfitSnapshotListData {
  items: StyleProfitSnapshotListItem[]
  total: number
  page: number
  page_size: number
}

export interface StyleProfitSnapshotResult {
  snapshot_id: number
  snapshot_no: string
  company: string
  item_code: string
  sales_order?: string | null
  revenue_status: string
  revenue_amount: NumericLike
  actual_total_cost: NumericLike
  standard_total_cost: NumericLike
  profit_amount: NumericLike
  profit_rate?: NumericLike | null
  snapshot_status: string
  allocation_status: string
  include_provisional_subcontract: boolean
  unresolved_count: number
  request_hash: string
  idempotent_replay: boolean
}

export interface StyleProfitDetailItem {
  id: number
  line_no: number
  cost_type: string
  source_type: string
  source_name: string
  item_code?: string | null
  qty?: NumericLike | null
  unit_rate?: NumericLike | null
  amount: NumericLike
  formula_code?: string | null
  is_unresolved: boolean
  unresolved_reason?: string | null
  raw_ref?: Record<string, unknown> | null
  created_at: string
}

export interface StyleProfitSourceMapItem {
  id: number
  detail_id?: number | null
  company: string
  sales_order?: string | null
  style_item_code: string
  source_item_code?: string | null
  source_system: string
  source_doctype: string
  source_status: string
  source_name: string
  source_line_no: string
  qty?: NumericLike | null
  unit_rate?: NumericLike | null
  amount: NumericLike
  currency?: string | null
  warehouse?: string | null
  posting_date?: string | null
  include_in_profit: boolean
  mapping_status: string
  unresolved_reason?: string | null
  raw_ref?: Record<string, unknown> | null
  created_at: string
}

export interface StyleProfitSnapshotDetailData {
  snapshot: StyleProfitSnapshotResult
  details: StyleProfitDetailItem[]
  source_maps: StyleProfitSourceMapItem[]
}

export interface StyleProfitSnapshotListParams {
  company: string
  item_code: string
  sales_order?: string
  from_date?: string
  to_date?: string
  snapshot_status?: string
  page?: number
  page_size?: number
}

const toQuery = (params: Record<string, string | number | undefined>): string => {
  const query = new URLSearchParams()
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== '') {
      query.set(key, String(value))
    }
  })
  return query.toString()
}

export const fetchStyleProfitSnapshots = async (
  params: StyleProfitSnapshotListParams,
): Promise<ApiResponse<StyleProfitSnapshotListData>> => {
  const query = toQuery({
    company: params.company,
    item_code: params.item_code,
    sales_order: params.sales_order,
    from_date: params.from_date,
    to_date: params.to_date,
    snapshot_status: params.snapshot_status,
    page: params.page ?? 1,
    page_size: params.page_size ?? 20,
  })
  return request<StyleProfitSnapshotListData>(`/api/reports/style-profit/snapshots?${query}`)
}

export const fetchStyleProfitSnapshotDetail = async (
  snapshotId: number,
): Promise<ApiResponse<StyleProfitSnapshotDetailData>> => {
  return request<StyleProfitSnapshotDetailData>(`/api/reports/style-profit/snapshots/${snapshotId}`)
}
