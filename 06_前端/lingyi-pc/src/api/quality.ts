import { request } from '@/api/request'
import type { ApiResponse } from '@/api/request'

export type NumericLike = string | number

export interface QualityInspectionItemInput {
  item_code: string
  sample_qty?: NumericLike
  accepted_qty?: NumericLike
  rejected_qty?: NumericLike
  defect_qty?: NumericLike
  result?: string
  remark?: string | null
}

export interface QualityDefectInput {
  defect_code: string
  defect_name: string
  defect_qty: NumericLike
  severity?: string
  item_line_no?: number | null
  remark?: string | null
}

export interface QualityInspectionCreatePayload {
  company: string
  source_type: string
  source_id?: string | null
  item_code: string
  supplier?: string | null
  warehouse?: string | null
  work_order?: string | null
  sales_order?: string | null
  inspection_date: string
  inspected_qty: NumericLike
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  defect_qty?: NumericLike
  result?: string
  remark?: string | null
  items?: QualityInspectionItemInput[]
  defects?: QualityDefectInput[]
}

export interface QualityInspectionUpdatePayload {
  supplier?: string | null
  warehouse?: string | null
  work_order?: string | null
  sales_order?: string | null
  inspection_date?: string | null
  inspected_qty?: NumericLike | null
  accepted_qty?: NumericLike | null
  rejected_qty?: NumericLike | null
  defect_qty?: NumericLike | null
  result?: string | null
  remark?: string | null
  items?: QualityInspectionItemInput[] | null
  defects?: QualityDefectInput[] | null
}

export interface QualityInspectionDefectCreatePayload {
  defects: QualityDefectInput[]
}

export interface QualityInspectionCancelPayload {
  reason?: string | null
}

export interface QualityInspectionListQuery {
  company?: string
  item_code?: string
  supplier?: string
  warehouse?: string
  source_type?: string
  source_id?: string
  status?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface QualityInspectionFilterQuery {
  company?: string
  item_code?: string
  supplier?: string
  warehouse?: string
  source_type?: string
  source_id?: string
  status?: string
  from_date?: string
  to_date?: string
}

export interface QualityInspectionListItem {
  id: number
  inspection_no: string
  company: string
  source_type: string
  source_id?: string | null
  item_code: string
  supplier?: string | null
  warehouse?: string | null
  inspection_date: string
  inspected_qty: NumericLike
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  defect_qty: NumericLike
  defect_rate: NumericLike
  rejected_rate: NumericLike
  result: string
  status: string
  created_by: string
  created_at: string
}

export interface QualityInspectionListData {
  items: QualityInspectionListItem[]
  total: number
  page: number
  page_size: number
}

export interface QualityInspectionItemData {
  id: number
  line_no: number
  item_code: string
  sample_qty: NumericLike
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  defect_qty: NumericLike
  result: string
  remark?: string | null
}

export interface QualityDefectData {
  id: number
  item_id?: number | null
  defect_code: string
  defect_name: string
  defect_qty: NumericLike
  severity: string
  remark?: string | null
}

export interface QualityOperationLogData {
  action: string
  operator: string
  operated_at: string
  from_status?: string | null
  to_status: string
  remark?: string | null
}

export interface QualityInspectionDetailData extends QualityInspectionListItem {
  work_order?: string | null
  sales_order?: string | null
  remark?: string | null
  confirmed_by?: string | null
  confirmed_at?: string | null
  cancelled_by?: string | null
  cancelled_at?: string | null
  source_snapshot?: Record<string, unknown> | null
  items: QualityInspectionItemData[]
  defects: QualityDefectData[]
  logs: QualityOperationLogData[]
}

export interface QualityInspectionActionData {
  id: number
  inspection_no: string
  status: string
  operator: string
  operated_at: string
}

export interface QualityStatisticsData {
  total_count: number
  total_inspected_qty: NumericLike
  total_accepted_qty: NumericLike
  total_rejected_qty: NumericLike
  total_defect_qty: NumericLike
  overall_defect_rate: NumericLike
  inspected_qty: NumericLike
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  defect_qty: NumericLike
  defect_rate: NumericLike
  rejected_rate: NumericLike
  by_result: Record<string, number>
  by_supplier: QualityStatisticsAggregateItem[]
  by_item_code: QualityStatisticsAggregateItem[]
  by_warehouse: QualityStatisticsAggregateItem[]
  by_source_type: QualityStatisticsAggregateItem[]
  top_defective_suppliers: QualityStatisticsAggregateItem[]
  top_defective_items: QualityStatisticsAggregateItem[]
}

export interface QualityStatisticsAggregateItem {
  key: string
  label: string
  count: number
  defect_rate: NumericLike
  total_count: number
  total_inspected_qty: NumericLike
  total_accepted_qty: NumericLike
  total_rejected_qty: NumericLike
  total_defect_qty: NumericLike
  overall_defect_rate: NumericLike
}

export interface QualityStatisticsTrendPoint {
  period_key: string
  inspection_count: number
  defect_rate: NumericLike
  rejected_rate: NumericLike
  period: string
  total_count: number
  total_inspected_qty: NumericLike
  total_accepted_qty: NumericLike
  total_rejected_qty: NumericLike
  total_defect_qty: NumericLike
  overall_defect_rate: NumericLike
}

export interface QualityStatisticsTrendData {
  period: 'monthly' | 'weekly'
  points: QualityStatisticsTrendPoint[]
}

export interface QualityExportRow {
  inspection_no: string
  company: string
  source_type: string
  source_id?: string | null
  item_code: string
  supplier?: string | null
  warehouse?: string | null
  inspection_date: string
  inspected_qty: NumericLike
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  defect_qty: NumericLike
  defect_rate: NumericLike
  rejected_rate: NumericLike
  result: string
  status: string
}

export interface QualityExportData {
  rows: QualityExportRow[]
  total: number
}

export type QualityExportFormat = 'csv' | 'xlsx' | 'pdf'

const buildQuery = (params: object): string => {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params as Record<string, string | number | null | undefined>)) {
    if (value === undefined || value === null || value === '') continue
    query.set(key, String(value))
  }
  const queryString = query.toString()
  return queryString ? `?${queryString}` : ''
}

export const fetchQualityInspections = (query: QualityInspectionListQuery = {}) =>
  request<QualityInspectionListData>(`/api/quality/inspections${buildQuery(query)}`)

export const fetchQualityInspectionDetail = (inspectionId: number) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}`)

export const createQualityInspection = (payload: QualityInspectionCreatePayload) =>
  request<QualityInspectionDetailData>('/api/quality/inspections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const updateDraftInspection = (inspectionId: number, payload: QualityInspectionUpdatePayload) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const addDefectRecord = (inspectionId: number, payload: QualityInspectionDefectCreatePayload) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}/defects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const confirmQualityInspection = (inspectionId: number, remark?: string | null) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ remark: remark || null }),
  })

export const cancelQualityInspection = (inspectionId: number, payload: QualityInspectionCancelPayload = {}) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const fetchQualityStatistics = (query: QualityInspectionFilterQuery = {}) =>
  request<QualityStatisticsData>(`/api/quality/statistics${buildQuery(query)}`)

export const fetchQualityStatisticsTrend = (
  period: 'monthly' | 'weekly',
  query: QualityInspectionFilterQuery = {},
) =>
  request<QualityStatisticsTrendData>(
    `/api/quality/statistics/trend${buildQuery({ period, ...query })}`,
  )

export const exportQualityInspections = (query: QualityInspectionFilterQuery = {}) =>
  request<QualityExportData>(`/api/quality/export${buildQuery(query)}`)

const parseFilename = (disposition: string | null, fallback: string): string => {
  if (!disposition) return fallback
  const utf8Match = disposition.match(/filename\\*=UTF-8''([^;]+)/i)
  if (utf8Match?.[1]) {
    try {
      return decodeURIComponent(utf8Match[1])
    } catch {
      return utf8Match[1]
    }
  }
  const simpleMatch = disposition.match(/filename=\"?([^\";]+)\"?/i)
  return simpleMatch?.[1] || fallback
}

export const exportQualityInspectionsFile = async (
  format: QualityExportFormat,
  query: QualityInspectionFilterQuery = {},
  inspectionId?: number,
): Promise<void> => {
  const suffix = format === 'xlsx' ? 'xlsx' : format === 'pdf' ? 'pdf' : 'csv'
  const response = await fetch(
    `/api/quality/export${buildQuery({ ...query, format, inspection_id: inspectionId })}`,
    {
      method: 'GET',
      credentials: 'include',
    },
  )

  if (!response.ok) {
    let message = '导出失败'
    try {
      const payload = (await response.json()) as ApiResponse<unknown>
      message = payload?.message || message
    } catch {}
    throw new Error(message)
  }

  const blob = await response.blob()
  const fallback = inspectionId ? `quality_export_${inspectionId}.${suffix}` : `quality_export.${suffix}`
  const filename = parseFilename(response.headers.get('content-disposition'), fallback)
  const href = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = href
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(href)
}
