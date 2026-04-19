import { request, type ApiResponse } from '@/api/request'

type NumericLike = string | number

export interface FactoryStatementListQuery {
  company?: string
  supplier?: string
  statement_status?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FactoryStatementListItem {
  id: number
  statement_no: string
  company: string
  supplier: string
  from_date: string
  to_date: string
  source_count: number
  gross_amount: NumericLike
  deduction_amount: NumericLike
  net_amount: NumericLike
  rejected_rate: NumericLike
  statement_status: string
  payable_outbox_id: number | null
  payable_outbox_status: string | null
  purchase_invoice_name: string | null
  payable_error_code: string | null
  payable_error_message: string | null
  created_by: string
  created_at: string
}

export interface FactoryStatementListData {
  items: FactoryStatementListItem[]
  total: number
  page: number
  page_size: number
}

export interface FactoryStatementDetailItem {
  id: number
  line_no: number
  inspection_id: number
  inspection_no?: string | null
  subcontract_id: number
  subcontract_no: string
  company: string
  supplier: string
  item_code?: string | null
  inspected_at?: string | null
  inspected_qty: NumericLike
  rejected_qty: NumericLike
  accepted_qty: NumericLike
  subcontract_rate: NumericLike
  gross_amount: NumericLike
  deduction_amount: NumericLike
  net_amount: NumericLike
  rejected_rate: NumericLike
}

export interface FactoryStatementLogItem {
  action: string
  from_status?: string | null
  to_status?: string | null
  remark: string | null
  operator: string
  operated_at: string
}

export interface FactoryStatementPayableOutboxItem {
  id: number
  status: string
  erpnext_purchase_invoice: string | null
  erpnext_docstatus: number | null
  erpnext_status: string | null
  last_error_code: string | null
  last_error_message: string | null
  created_at: string
  updated_at: string
}

export interface FactoryStatementDetailData {
  statement_id: number
  statement_no: string
  statement_status: string
  company: string
  supplier: string
  from_date: string
  to_date: string
  source_count: number
  inspected_qty: NumericLike
  rejected_qty: NumericLike
  accepted_qty: NumericLike
  gross_amount: NumericLike
  deduction_amount: NumericLike
  net_amount: NumericLike
  rejected_rate: NumericLike
  idempotency_key: string
  created_by: string
  created_at: string
  payable_outbox_id: number | null
  payable_outbox_status: string | null
  purchase_invoice_name: string | null
  payable_error_code: string | null
  payable_error_message: string | null
  items: FactoryStatementDetailItem[]
  logs: FactoryStatementLogItem[]
  payable_outboxes: FactoryStatementPayableOutboxItem[]
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

export const fetchFactoryStatements = async (
  query: FactoryStatementListQuery,
): Promise<ApiResponse<FactoryStatementListData>> => {
  const queryString = toQuery({
    company: query.company,
    supplier: query.supplier,
    statement_status: query.statement_status,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FactoryStatementListData>(`/api/factory-statements/?${queryString}`)
}

export const fetchFactoryStatementDetail = async (
  statementId: number,
): Promise<ApiResponse<FactoryStatementDetailData>> => {
  return request<FactoryStatementDetailData>(`/api/factory-statements/${statementId}`)
}
