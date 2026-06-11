import {
  fetchSalesInventoryCustomers,
  fetchSalesInventoryReferenceDrafts,
  fetchSalesInventorySuppliers,
  type CustomerItem,
  type SalesInventoryReferenceDraftData,
  type SupplierItem,
} from '@/api/sales_inventory'

export type SalesInventoryReferenceTab = 'customers' | 'suppliers'
export type SalesInventoryReferenceStatus = 'active' | 'inactive'
export type SalesInventoryReferenceSourceValidationState = 'verified' | 'fallback' | 'missing'

export interface SalesInventoryReferenceRow {
  code: string
  name: string
  company: string
  status: SalesInventoryReferenceStatus
  source: 'erpnext' | 'local-draft'
  parityScope: string
  referenceType: SalesInventoryReferenceTab
  draftId?: number | null
  scenarioTag?: string | null
  createdAt?: string | null
  disabledReason?: string | null
  sourceValidationState: SalesInventoryReferenceSourceValidationState
  readonlySourceTag: string
  missingSourcePrompt: string
}

export interface SalesInventoryReferenceQuery {
  keyword: string
  status: string
  source: string
}

export interface SalesInventoryReferenceLoadResult {
  rows: SalesInventoryReferenceRow[]
  usingFallback: boolean
}

const normalizeParityScope = (parity: string, tab: SalesInventoryReferenceTab): string => {
  if (parity === 'system-catalog') return 'system-catalog'
  return tab === 'customers' ? 'customer-reference-draft' : 'supplier-reference-draft'
}

const normalizeCustomerRow = (item: CustomerItem, parity: string): SalesInventoryReferenceRow => ({
  code: item.name,
  name: item.customer_name?.trim() || item.name,
  company: 'ERPNext',
  status: item.disabled ? 'inactive' : 'active',
  source: 'erpnext',
  parityScope: normalizeParityScope(parity, 'customers'),
  referenceType: 'customers',
  disabledReason: item.disabled ? 'ERPNext 已停用' : '',
  sourceValidationState: 'verified',
  readonlySourceTag: 'ERPNext客户已校验',
  missingSourcePrompt: '',
})

const normalizeSupplierRow = (item: SupplierItem, parity: string): SalesInventoryReferenceRow => ({
  code: item.name,
  name: item.supplier_name?.trim() || item.name,
  company: 'LOCAL',
  status: item.disabled ? 'inactive' : 'active',
  source: 'local-draft',
  parityScope: normalizeParityScope(parity, 'suppliers'),
  referenceType: 'suppliers',
  disabledReason: item.disabled ? '本地草稿已停用' : '',
  sourceValidationState: 'fallback',
  readonlySourceTag: '供应商本地草稿',
  missingSourcePrompt: '',
})

const normalizeDraftRow = (
  item: SalesInventoryReferenceDraftData,
  tab: SalesInventoryReferenceTab,
  parity: string,
): SalesInventoryReferenceRow => ({
  code: item.reference_no,
  name: item.reference_name,
  company: item.company,
  status: item.status,
  source: 'local-draft',
  parityScope: normalizeParityScope(parity, tab),
  referenceType: tab,
  draftId: item.id,
  scenarioTag: item.scenario_tag,
  createdAt: item.created_at,
  disabledReason: item.status === 'inactive' ? item.deactivate_reason || '本地草稿已停用' : '',
  sourceValidationState: 'fallback',
  readonlySourceTag: tab === 'customers' ? '客户本地草稿' : '供应商本地草稿',
  missingSourcePrompt: item.status === 'inactive' ? item.deactivate_reason || '' : '',
})

const mergeRows = (
  baseRows: SalesInventoryReferenceRow[],
  draftRows: SalesInventoryReferenceRow[],
): SalesInventoryReferenceRow[] => {
  const merged = new Map<string, SalesInventoryReferenceRow>()
  draftRows.forEach((row) => {
    merged.set(`${row.referenceType}:${row.code}:${row.source}:${row.draftId || 0}`, row)
  })
  baseRows.forEach((row) => {
    const hasActiveDraft = draftRows.some(
      (draft) => draft.referenceType === row.referenceType && draft.code === row.code && draft.status === 'active',
    )
    if (!hasActiveDraft) {
      merged.set(`${row.referenceType}:${row.code}:${row.source}:0`, row)
    }
  })
  return Array.from(merged.values())
}

const loadCustomerRows = async (parity: string): Promise<SalesInventoryReferenceLoadResult> => {
  let usingFallback = false
  const [customerResponse, draftResponse] = await Promise.all([
    fetchSalesInventoryCustomers({ page: 1, page_size: 100 }).catch(() => {
      usingFallback = true
      return null
    }),
    fetchSalesInventoryReferenceDrafts('customer', { page: 1, page_size: 100 }),
  ])
  const baseRows = (customerResponse?.data.items || []).map((item) => normalizeCustomerRow(item, parity))
  const draftRows = draftResponse.data.items.map((item) => normalizeDraftRow(item, 'customers', parity))
  return {
    rows: mergeRows(baseRows, draftRows),
    usingFallback,
  }
}

const loadSupplierRows = async (parity: string): Promise<SalesInventoryReferenceLoadResult> => {
  let usingFallback = false
  const [supplierResponse, draftResponse] = await Promise.all([
    fetchSalesInventorySuppliers({ page: 1, page_size: 100 }).catch(() => {
      usingFallback = true
      return null
    }),
    fetchSalesInventoryReferenceDrafts('supplier', { page: 1, page_size: 100 }),
  ])
  const baseRows = (supplierResponse?.data.items || []).map((item) => normalizeSupplierRow(item, parity))
  const draftRows = draftResponse.data.items.map((item) => normalizeDraftRow(item, 'suppliers', parity))
  return {
    rows: mergeRows(baseRows, draftRows),
    usingFallback,
  }
}

export const resolveReferenceTab = (tab: unknown, parity: unknown): SalesInventoryReferenceTab => {
  const normalizedTab = String(Array.isArray(tab) ? tab[0] || '' : tab || '').trim().toLowerCase()
  const normalizedParity = String(Array.isArray(parity) ? parity[0] || '' : parity || '').trim().toLowerCase()
  if (normalizedTab === 'suppliers' || normalizedParity === 'supplier-reference-draft') return 'suppliers'
  return 'customers'
}

export const loadSalesInventoryReferenceRows = async (
  tab: SalesInventoryReferenceTab,
  parity: string,
): Promise<SalesInventoryReferenceLoadResult> => {
  if (tab === 'suppliers') return loadSupplierRows(parity)
  return loadCustomerRows(parity)
}

export const filterReferenceRows = (
  rows: SalesInventoryReferenceRow[],
  query: SalesInventoryReferenceQuery,
): SalesInventoryReferenceRow[] => {
  const keyword = query.keyword.trim().toLowerCase()
  return rows.filter((row) => {
    if (query.status && row.status !== query.status) return false
    if (query.source && row.source !== query.source) return false
    if (!keyword) return true
    return (
      row.code.toLowerCase().includes(keyword) ||
      row.name.toLowerCase().includes(keyword) ||
      row.company.toLowerCase().includes(keyword)
    )
  })
}
