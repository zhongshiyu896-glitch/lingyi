import { request, type ApiResponse } from '@/api/request'

type NumericLike = string | number

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

export interface DashboardOverviewQuery {
  company: string
  from_date?: string
  to_date?: string
  item_code?: string
  warehouse?: string
}

export interface DashboardSourceStatus {
  module: string
  status: string
}

export interface DashboardQualityOverview {
  inspection_count: number
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  defect_count: number
  pass_rate: NumericLike
}

export interface DashboardSalesInventoryOverview {
  item_count: number
  total_actual_qty: NumericLike
  below_safety_count: number
  below_reorder_count: number
}

export interface DashboardWarehouseOverview {
  alert_count: number
  critical_alert_count: number
  warning_alert_count: number
}

export interface DashboardOverviewData {
  company: string
  from_date?: string | null
  to_date?: string | null
  generated_at: string
  quality: DashboardQualityOverview
  sales_inventory: DashboardSalesInventoryOverview
  warehouse: DashboardWarehouseOverview
  source_status: DashboardSourceStatus[]
}

export const fetchDashboardOverview = async (
  query: DashboardOverviewQuery,
): Promise<ApiResponse<DashboardOverviewData>> => {
  const queryString = toQuery({
    company: query.company,
    from_date: query.from_date,
    to_date: query.to_date,
    item_code: query.item_code,
    warehouse: query.warehouse,
  })
  return request<DashboardOverviewData>(`/api/dashboard/overview?${queryString}`)
}
