import { request, requestFile } from '@/api/request'

export type NumericLike = string | number
export type QualityWriteOperation = 'create' | 'update' | 'confirm' | 'cancel' | 'defects'

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
  request_id: string
  idempotency_key: string
  scenario_tag: string
  source_ref: string
  inspection_ref: string
  source_doc?: string | null
  operation: 'create'
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
  request_id: string
  idempotency_key: string
  scenario_tag: string
  source_ref: string
  inspection_ref: string
  source_type: string
  source_doc?: string | null
  item_code: string
  operation: 'update'
  result: string
  supplier?: string | null
  warehouse?: string | null
  work_order?: string | null
  sales_order?: string | null
  inspection_date?: string | null
  inspected_qty?: NumericLike | null
  accepted_qty?: NumericLike | null
  rejected_qty?: NumericLike | null
  defect_qty?: NumericLike | null
  remark?: string | null
  items?: QualityInspectionItemInput[] | null
  defects?: QualityDefectInput[] | null
}

export interface QualityInspectionDefectCreatePayload {
  request_id: string
  idempotency_key: string
  scenario_tag: string
  source_ref: string
  inspection_ref: string
  source_type: string
  source_doc?: string | null
  item_code: string
  operation: 'defects'
  result: string
  defects: QualityDefectInput[]
}

export interface QualityInspectionConfirmPayload {
  request_id: string
  idempotency_key: string
  scenario_tag: string
  source_ref: string
  inspection_ref: string
  source_type: string
  source_doc?: string | null
  item_code: string
  operation: 'confirm'
  result: string
  remark?: string | null
}

export interface QualityInspectionCancelPayload {
  request_id: string
  idempotency_key: string
  scenario_tag: string
  source_ref: string
  inspection_ref: string
  source_type: string
  source_doc?: string | null
  item_code: string
  operation: 'cancel'
  result: string
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

export interface QualityOutboxStatusData {
  inspection_id: number
  status: string
  attempts: number
  max_attempts: number
  next_retry_at?: string | null
  last_error_code?: string | null
  last_error_message?: string | null
  stock_entry_name?: string | null
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
const QUALITY_SCENARIO_PATTERN = /^Z003-QUALITY-INSPECTION-\d{8}-\d{3}$/
const QUALITY_SCENARIO_EXTRACT_PATTERN = /Z003-QUALITY-INSPECTION-\d{8}-\d{3}/
const QUALITY_REQUEST_ID_PATTERN = /^[A-Za-z0-9_.-]{1,64}$/

const buildQuery = (params: object): string => {
  const query = new URLSearchParams()
  for (const [key, value] of Object.entries(params as Record<string, string | number | null | undefined>)) {
    if (value === undefined || value === null || value === '') continue
    query.set(key, String(value))
  }
  const queryString = query.toString()
  return queryString ? `?${queryString}` : ''
}

const fnvCarrierCode = (value: string): string => {
  const normalized = value.trim()
  let hashValue = 2166136261
  for (let index = 0; index < normalized.length; index += 1) {
    hashValue ^= normalized.charCodeAt(index)
    hashValue = Math.imul(hashValue, 16777619) >>> 0
  }
  return hashValue.toString(16).toUpperCase().padStart(8, '0').slice(-3)
}

const qualityOperationCode = (operation: QualityWriteOperation): 'C' | 'U' | 'F' | 'X' | 'D' => {
  if (operation === 'create') return 'C'
  if (operation === 'update') return 'U'
  if (operation === 'confirm') return 'F'
  if (operation === 'cancel') return 'X'
  return 'D'
}

export const buildQualityInspectionScenarioTag = (): string => {
  const now = new Date()
  const day = `${now.getFullYear()}${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}`
  const seq = String(Math.floor(Math.random() * 1000)).padStart(3, '0')
  return `Z003-QUALITY-INSPECTION-${day}-${seq}`
}

export const extractQualityInspectionScenarioTag = (value: string): string | null => {
  const matched = value.trim().match(QUALITY_SCENARIO_EXTRACT_PATTERN)
  return matched ? matched[0] : null
}

export const ensureQualityInspectionScenarioTag = (value: string): string => {
  const normalized = value.trim()
  if (QUALITY_SCENARIO_PATTERN.test(normalized)) {
    return normalized
  }
  return buildQualityInspectionScenarioTag()
}

export const buildQualityInspectionRequestId = ({
  scenarioTag,
  operation,
  idempotencyKey,
  sourceRef,
  inspectionRef,
  itemCode,
  result,
}: {
  scenarioTag: string
  operation: QualityWriteOperation
  idempotencyKey: string
  sourceRef: string
  inspectionRef: string
  itemCode: string
  result: string
}): string => {
  const normalizedScenarioTag = ensureQualityInspectionScenarioTag(scenarioTag)
  const requestId = `${normalizedScenarioTag}-QI-${qualityOperationCode(operation)}-${fnvCarrierCode(idempotencyKey)}-${fnvCarrierCode(sourceRef)}-${fnvCarrierCode(inspectionRef)}-${fnvCarrierCode(itemCode)}-${fnvCarrierCode(result)}`
  if (!QUALITY_REQUEST_ID_PATTERN.test(requestId)) {
    throw new Error('request_id 编码非法')
  }
  return requestId
}

export const fetchQualityInspections = (query: QualityInspectionListQuery = {}) =>
  request<QualityInspectionListData>(`/api/quality/inspections${buildQuery(query)}`)

export const fetchQualityInspectionDetail = (inspectionId: number) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}`)

export const fetchQualityInspectionOutboxStatus = (inspectionId: number) =>
  request<QualityOutboxStatusData>(`/api/quality/inspections/${inspectionId}/outbox-status`)

export const createQualityInspection = (payload: QualityInspectionCreatePayload) =>
  request<QualityInspectionDetailData>('/api/quality/inspections', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })

export const updateQualityInspection = (inspectionId: number, payload: QualityInspectionUpdatePayload) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })

export const updateDraftInspection = (inspectionId: number, payload: QualityInspectionUpdatePayload) =>
  updateQualityInspection(inspectionId, payload)

export const addDefectRecord = (inspectionId: number, payload: QualityInspectionDefectCreatePayload) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}/defects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })

export const confirmQualityInspection = (inspectionId: number, payload: QualityInspectionConfirmPayload) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
    body: JSON.stringify(payload),
  })

export const cancelQualityInspection = (inspectionId: number, payload: QualityInspectionCancelPayload) =>
  request<QualityInspectionDetailData>(`/api/quality/inspections/${inspectionId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-Request-ID': payload.request_id },
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

const blobToDataUrl = (blob: Blob): Promise<string> =>
  new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      if (typeof reader.result !== 'string') {
        reject(new Error('导出失败'))
        return
      }
      resolve(reader.result)
    }
    reader.onerror = () => reject(new Error('导出失败'))
    reader.readAsDataURL(blob)
  })

const triggerDownload = async (blob: Blob, filename: string): Promise<void> => {
  const dataUrl = await blobToDataUrl(blob)
  const link = document.createElement('a')
  link.href = dataUrl
  link.download = filename
  link.style.display = 'none'
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

export const exportQualityInspectionsFile = async (
  format: QualityExportFormat,
  query: QualityInspectionFilterQuery = {},
  inspectionId?: number,
): Promise<void> => {
  const suffix = format === 'xlsx' ? 'xlsx' : format === 'pdf' ? 'pdf' : 'csv'
  const fallback = inspectionId ? `quality_export_${inspectionId}.${suffix}` : `quality_export.${suffix}`
  const { blob, filename } = await requestFile(
    `/api/quality/export${buildQuery({ ...query, format, inspection_id: inspectionId })}`,
    { method: 'GET' },
    fallback,
  )
  await triggerDownload(blob, filename)
}
