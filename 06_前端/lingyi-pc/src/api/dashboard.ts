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
  company?: string
  from_date?: string
  to_date?: string
  item_code?: string
  warehouse?: string
  keyword?: string
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

export interface DashboardHomeMetricCard {
  key: string
  label: string
  value: string
  unit?: string | null
  trend?: string | null
}

export interface DashboardHomeTodoItem {
  key: string
  title: string
  count: number
  status: 'normal' | 'warning' | 'urgent'
  action_label: string
}

export interface DashboardHomeTrendPoint {
  period: string
  forecast_sales: NumericLike
  forecast_cost: NumericLike
  forecast_profit: NumericLike
}

export interface DashboardHomeOverviewData {
  summary_title: string
  metric_cards: DashboardHomeMetricCard[]
  todo_items: DashboardHomeTodoItem[]
  warnings: string[]
  business_summary: string[]
  recent_activities: string[]
  trend_points: DashboardHomeTrendPoint[]
  primary_actions: string[]
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
  kanban?: DashboardKanbanData | null
  home_overview?: DashboardHomeOverviewData | null
}

export interface DashboardKanbanFlowNode {
  key: string
  label: string
  status: 'normal' | 'active' | 'completed'
  route?: string | null
}

export interface DashboardKanbanFlowLink {
  from_key: string
  to_key: string
}

export interface DashboardKanbanMessageRow {
  image?: string | null
  order_no: string
  customer: string
  style_no: string
  style_name: string
  ordered_qty: NumericLike
  overdue: string
  sun: string
  mon: string
  tue: string
  wed: string
  thu: string
  fri: string
  sat: string
  title: string
  sent_at: string
  status: string
  sender: string
}

export interface DashboardKanbanData {
  board_name: string
  quick_filters: string[]
  flow_nodes: DashboardKanbanFlowNode[]
  flow_links: DashboardKanbanFlowLink[]
  messages: DashboardKanbanMessageRow[]
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
    keyword: query.keyword,
  })
  return request<DashboardOverviewData>(`/api/dashboard/overview?${queryString}`)
}
