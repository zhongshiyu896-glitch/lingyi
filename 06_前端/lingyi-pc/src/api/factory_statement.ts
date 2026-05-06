import { request, type ApiResponse } from '@/api/request'

type NumericLike = string | number
const FACTORY_STATEMENT_READONLY_GUARD = true

const throwReadonlyWriteError = (actionLabel: string): never => {
  throw new Error(`当前为只读对账视图，已禁用${actionLabel}写操作`)
}

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

export interface FactoryStatementExpenseReimbursementPaymentQuery {
  payment_no?: string
  reimbursement_no?: string
  statement_no?: string
  supplier?: string
  payment_status?: string
  review_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FactoryStatementExpenseReimbursementPaymentItem {
  payment_no: string
  reimbursement_no: string
  statement_no: string
  company: string
  supplier: string
  expense_type: string
  payable_amount: NumericLike
  paid_amount: NumericLike
  pending_amount: NumericLike
  payment_status: string
  review_status: string
  payment_date: string
  payable_account: string
  cost_center: string
  owner: string
  ref_no: string
}

export interface FactoryStatementExpenseReimbursementPaymentData {
  items: FactoryStatementExpenseReimbursementPaymentItem[]
  total: number
  page: number
  page_size: number
}

export interface FactoryStatementBankDepositQuery {
  deposit_no?: string
  statement_no?: string
  bank_name?: string
  account_name?: string
  deposit_status?: string
  review_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FactoryStatementBankDepositItem {
  deposit_no: string
  statement_no: string
  company: string
  bank_name: string
  account_name: string
  account_no: string
  currency: string
  deposit_amount: NumericLike
  confirmed_amount: NumericLike
  pending_amount: NumericLike
  deposit_status: string
  review_status: string
  deposit_date: string
  voucher_no: string
  owner: string
  remark: string
}

export interface FactoryStatementBankDepositData {
  items: FactoryStatementBankDepositItem[]
  total: number
  page: number
  page_size: number
}

export interface FactoryStatementBankWithdrawalQuery {
  withdrawal_no?: string
  statement_no?: string
  bank_name?: string
  account_name?: string
  withdrawal_status?: string
  review_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FactoryStatementBankWithdrawalItem {
  withdrawal_no: string
  statement_no: string
  company: string
  bank_name: string
  account_name: string
  account_no: string
  currency: string
  withdrawal_amount: NumericLike
  transferred_amount: NumericLike
  pending_amount: NumericLike
  withdrawal_status: string
  review_status: string
  withdrawal_date: string
  voucher_no: string
  owner: string
  remark: string
}

export interface FactoryStatementBankWithdrawalData {
  items: FactoryStatementBankWithdrawalItem[]
  total: number
  page: number
  page_size: number
}

export interface FactoryStatementCustomerEvaluationQuery {
  evaluation_no?: string
  statement_no?: string
  customer_name?: string
  assessor?: string
  score_level?: string
  review_status?: string
  keyword?: string
  from_date?: string
  to_date?: string
  page?: number
  page_size?: number
}

export interface FactoryStatementCustomerEvaluationItem {
  evaluation_no: string
  statement_no: string
  company: string
  customer_name: string
  customer_code: string
  assessor: string
  score: NumericLike
  score_level: string
  review_status: string
  follow_up_status: string
  evaluation_date: string
  expiry_date: string
  owner: string
  remark: string
}

export interface FactoryStatementCustomerEvaluationData {
  items: FactoryStatementCustomerEvaluationItem[]
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

export interface FactoryStatementCreatePayload {
  company: string
  supplier: string
  from_date: string
  to_date: string
  idempotency_key: string
}

export interface FactoryStatementCreateData {
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
  request_hash: string
  idempotent_replay: boolean
}

export interface FactoryStatementConfirmPayload {
  idempotency_key: string
  remark?: string
}

export interface FactoryStatementConfirmData {
  id: number
  statement_no: string
  status: string
  confirmed_by: string
  confirmed_at: string
  idempotent_replay: boolean
}

export interface FactoryStatementCancelPayload {
  idempotency_key: string
  reason?: string
}

export interface FactoryStatementCancelData {
  id: number
  statement_no: string
  status: string
  cancelled_by: string
  cancelled_at: string
  idempotent_replay: boolean
}

export interface FactoryStatementPayableDraftCreatePayload {
  idempotency_key: string
}

export interface FactoryStatementPayableDraftCreateData {
  outbox_id: number
  status: string
  idempotent_replay: boolean
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

export const fetchFactoryStatementExpenseReimbursementPayments = async (
  query: FactoryStatementExpenseReimbursementPaymentQuery,
): Promise<ApiResponse<FactoryStatementExpenseReimbursementPaymentData>> => {
  const queryString = toQuery({
    payment_no: query.payment_no,
    reimbursement_no: query.reimbursement_no,
    statement_no: query.statement_no,
    supplier: query.supplier,
    payment_status: query.payment_status,
    review_status: query.review_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FactoryStatementExpenseReimbursementPaymentData>(
    `/api/factory-statements/expense-reimbursement-payments?${queryString}`,
  )
}

export const fetchFactoryStatementBankDeposits = async (
  query: FactoryStatementBankDepositQuery,
): Promise<ApiResponse<FactoryStatementBankDepositData>> => {
  const queryString = toQuery({
    deposit_no: query.deposit_no,
    statement_no: query.statement_no,
    bank_name: query.bank_name,
    account_name: query.account_name,
    deposit_status: query.deposit_status,
    review_status: query.review_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FactoryStatementBankDepositData>(`/api/factory-statements/bank-deposits?${queryString}`)
}

export const fetchFactoryStatementBankWithdrawals = async (
  query: FactoryStatementBankWithdrawalQuery,
): Promise<ApiResponse<FactoryStatementBankWithdrawalData>> => {
  const queryString = toQuery({
    withdrawal_no: query.withdrawal_no,
    statement_no: query.statement_no,
    bank_name: query.bank_name,
    account_name: query.account_name,
    withdrawal_status: query.withdrawal_status,
    review_status: query.review_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FactoryStatementBankWithdrawalData>(`/api/factory-statements/bank-withdrawals?${queryString}`)
}

export const fetchFactoryStatementCustomerEvaluations = async (
  query: FactoryStatementCustomerEvaluationQuery,
): Promise<ApiResponse<FactoryStatementCustomerEvaluationData>> => {
  const queryString = toQuery({
    evaluation_no: query.evaluation_no,
    statement_no: query.statement_no,
    customer_name: query.customer_name,
    assessor: query.assessor,
    score_level: query.score_level,
    review_status: query.review_status,
    keyword: query.keyword,
    from_date: query.from_date,
    to_date: query.to_date,
    page: query.page ?? 1,
    page_size: query.page_size ?? 20,
  })
  return request<FactoryStatementCustomerEvaluationData>(`/api/factory-statements/customer-evaluations?${queryString}`)
}

export const fetchFactoryStatementDetail = async (
  statementId: number,
): Promise<ApiResponse<FactoryStatementDetailData>> => {
  return request<FactoryStatementDetailData>(`/api/factory-statements/${statementId}`)
}

export const createFactoryStatement = async (
  payload: FactoryStatementCreatePayload,
): Promise<ApiResponse<FactoryStatementCreateData>> =>
  FACTORY_STATEMENT_READONLY_GUARD
    ? Promise.reject(throwReadonlyWriteError('创建对账单'))
    :
  request<FactoryStatementCreateData>('/api/factory-statements/', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const confirmFactoryStatement = async (
  statementId: number,
  payload: FactoryStatementConfirmPayload,
): Promise<ApiResponse<FactoryStatementConfirmData>> =>
  FACTORY_STATEMENT_READONLY_GUARD
    ? Promise.reject(throwReadonlyWriteError('确认对账单'))
    :
  request<FactoryStatementConfirmData>(`/api/factory-statements/${statementId}/confirm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const cancelFactoryStatement = async (
  statementId: number,
  payload: FactoryStatementCancelPayload,
): Promise<ApiResponse<FactoryStatementCancelData>> =>
  FACTORY_STATEMENT_READONLY_GUARD
    ? Promise.reject(throwReadonlyWriteError('取消对账单'))
    :
  request<FactoryStatementCancelData>(`/api/factory-statements/${statementId}/cancel`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

export const createFactoryStatementPayableDraft = async (
  statementId: number,
  payload: FactoryStatementPayableDraftCreatePayload,
): Promise<ApiResponse<FactoryStatementPayableDraftCreateData>> =>
  FACTORY_STATEMENT_READONLY_GUARD
    ? Promise.reject(throwReadonlyWriteError('生成应付草稿'))
    :
  request<FactoryStatementPayableDraftCreateData>(`/api/factory-statements/${statementId}/payable-draft`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
