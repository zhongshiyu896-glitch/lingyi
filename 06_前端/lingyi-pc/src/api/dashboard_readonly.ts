import { request } from '@/api/request'
import { fetchDashboardOverview, type DashboardOverviewData, type DashboardOverviewQuery } from '@/api/dashboard'

export interface DashboardHealthSummaryItem {
  module: string
  status: 'ok' | 'warn' | 'blocked'
  check_name: string
  check_result: string
  generated_at: string
}

export interface DashboardHealthSummaryData {
  items: DashboardHealthSummaryItem[]
  total: number
  generated_at: string
}

export interface DashboardWorkbenchReadonlyData {
  overview: DashboardOverviewData
  healthSummary: DashboardHealthSummaryData
}

export const fetchDashboardWorkbenchReadonly = async (
  query: DashboardOverviewQuery,
): Promise<DashboardWorkbenchReadonlyData> => {
  const [overviewResponse, healthSummaryResponse] = await Promise.all([
    fetchDashboardOverview(query),
    request<DashboardHealthSummaryData>('/api/system/health/summary'),
  ])

  return {
    overview: overviewResponse.data,
    healthSummary: healthSummaryResponse.data,
  }
}
