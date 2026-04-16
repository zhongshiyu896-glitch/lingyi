import { request } from '@/api/request'

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

export interface QualityInspectionConfirmPayload {
  remark?: string | null
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
  inspected_qty: NumericLike
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  defect_qty: NumericLike
  defect_rate: NumericLike
  rejected_rate: NumericLike
  by_result: Record<string, number>
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

export const updateQualityInspection = (inspectionId: number, payload: QualityInspectionUpdatePayload) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const confirmQualityInspection = (inspectionId: number, payload: QualityInspectionConfirmPayload) =>
  request<QualityInspectionActionData>(`/api/quality/inspections/${inspectionId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const cancelQualityInspection = (inspectionId: number, payload: QualityInspectionCancelPayload) =>
  request<QualityInspectionActionData>(`/api/quality/inspections/${inspectionId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const fetchQualityStatistics = (query: QualityInspectionFilterQuery = {}) =>
  request<QualityStatisticsData>(`/api/quality/statistics${buildQuery(query)}`)

export const exportQualityInspections = (query: QualityInspectionFilterQuery = {}) =>
  request<QualityExportData>(`/api/quality/export${buildQuery(query)}`)
