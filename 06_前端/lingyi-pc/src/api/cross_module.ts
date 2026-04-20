import { request, type ApiResponse } from '@/api/request'

type NumericLike = string | number

export interface CrossModuleQuery {
  company?: string
}

export interface CrossModuleWorkOrderData {
  work_order_id: string
  company?: string | null
  production_item?: string | null
}

export interface CrossModuleStockEntryData {
  voucher_no: string
  voucher_type?: string | null
  company?: string | null
  item_code?: string | null
  warehouse?: string | null
  posting_date?: string | null
  posting_time?: string | null
  actual_qty: NumericLike
}

export interface CrossModuleQualityInspectionData {
  inspection_id: number
  inspection_no: string
  company: string
  source_type: string
  item_code: string
  warehouse?: string | null
  work_order?: string | null
  sales_order?: string | null
  inspection_date: string
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  defect_qty: NumericLike
  status: string
  result: string
}

export interface CrossModuleWorkOrderTrailSummary {
  material_issue_qty: NumericLike
  output_qty: NumericLike
  accepted_qty: NumericLike
  rejected_qty: NumericLike
  defect_qty: NumericLike
  stock_entry_count: number
  quality_inspection_count: number
}

export interface CrossModuleWorkOrderTrailData {
  work_order: CrossModuleWorkOrderData
  stock_entries: CrossModuleStockEntryData[]
  quality_inspections: CrossModuleQualityInspectionData[]
  summary: CrossModuleWorkOrderTrailSummary
}

export interface CrossModuleSalesOrderData {
  sales_order_id: string
  company?: string | null
  customer?: string | null
  transaction_date?: string | null
  delivery_date?: string | null
  status?: string | null
}

export interface CrossModuleDeliveryNoteData {
  delivery_note: string
  company?: string | null
  item_code?: string | null
  warehouse?: string | null
  posting_date?: string | null
  posting_time?: string | null
  delivered_qty: NumericLike
}

export interface CrossModuleSalesOrderTrailSummary {
  ordered_qty: NumericLike
  delivered_qty: NumericLike
  quality_inspection_count: number
  defect_qty: NumericLike
}

export interface CrossModuleSalesOrderTrailData {
  sales_order: CrossModuleSalesOrderData
  delivery_notes: CrossModuleDeliveryNoteData[]
  quality_inspections: CrossModuleQualityInspectionData[]
  summary: CrossModuleSalesOrderTrailSummary
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

export const fetchWorkOrderTrail = async (
  workOrderId: string,
  query: CrossModuleQuery = {},
): Promise<ApiResponse<CrossModuleWorkOrderTrailData>> => {
  const queryString = toQuery({ company: query.company })
  return request<CrossModuleWorkOrderTrailData>(
    `/api/cross-module/work-order-trail/${encodeURIComponent(workOrderId)}?${queryString}`,
  )
}

export const fetchSalesOrderTrail = async (
  salesOrderId: string,
  query: CrossModuleQuery = {},
): Promise<ApiResponse<CrossModuleSalesOrderTrailData>> => {
  const queryString = toQuery({ company: query.company })
  return request<CrossModuleSalesOrderTrailData>(
    `/api/cross-module/sales-order-trail/${encodeURIComponent(salesOrderId)}?${queryString}`,
  )
}
