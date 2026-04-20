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

export interface WarehouseStockLedgerQuery {
  company?: string
  warehouse?: string
  item_code?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface WarehouseStockLedgerItem {
  company: string
  warehouse: string
  item_code: string
  posting_date: string
  voucher_type?: string | null
  voucher_no?: string | null
  actual_qty: NumericLike
  qty_after_transaction: NumericLike
  valuation_rate: NumericLike
}

export interface WarehouseStockLedgerData {
  items: WarehouseStockLedgerItem[]
  total: number
  page: number
  page_size: number
}

export interface WarehouseStockSummaryQuery {
  company?: string
  warehouse?: string
  item_code?: string
}

export interface WarehouseStockSummaryItem {
  company: string
  warehouse: string
  item_code: string
  actual_qty: NumericLike
  projected_qty: NumericLike
  reserved_qty: NumericLike
  ordered_qty: NumericLike
  reorder_level?: NumericLike | null
  safety_stock?: NumericLike | null
  threshold_missing: boolean
  is_below_reorder: boolean
  is_below_safety: boolean
}

export interface WarehouseStockSummaryData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  items: WarehouseStockSummaryItem[]
}

export interface WarehouseAlertsQuery {
  company?: string
  warehouse?: string
  item_code?: string
  alert_type?: 'low_stock' | 'below_safety' | 'overstock' | 'stale_stock' | ''
}

export interface WarehouseAlertItem {
  company: string
  warehouse: string
  item_code: string
  alert_type: string
  current_qty: NumericLike
  threshold_qty?: NumericLike | null
  gap_qty?: NumericLike | null
  last_movement_date?: string | null
  severity: string
}

export interface WarehouseAlertsData {
  company?: string | null
  warehouse?: string | null
  item_code?: string | null
  alert_type?: string | null
  items: WarehouseAlertItem[]
}

export const fetchWarehouseStockLedger = async (
  query: WarehouseStockLedgerQuery,
): Promise<ApiResponse<WarehouseStockLedgerData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<WarehouseStockLedgerData>(`/api/warehouse/stock-ledger?${queryString}`)
}

export const fetchWarehouseStockSummary = async (
  query: WarehouseStockSummaryQuery,
): Promise<ApiResponse<WarehouseStockSummaryData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
  })
  return request<WarehouseStockSummaryData>(`/api/warehouse/stock-summary?${queryString}`)
}

export const fetchWarehouseAlerts = async (
  query: WarehouseAlertsQuery,
): Promise<ApiResponse<WarehouseAlertsData>> => {
  const queryString = toQuery({
    company: query.company,
    warehouse: query.warehouse,
    item_code: query.item_code,
    alert_type: query.alert_type,
  })
  return request<WarehouseAlertsData>(`/api/warehouse/alerts?${queryString}`)
}
