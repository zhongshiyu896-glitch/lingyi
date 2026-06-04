import { fetchSalesInventoryCustomers, type CustomerItem } from '@/api/sales_inventory'

export type SalesInventoryReferenceTab = 'customers' | 'suppliers'
export type SalesInventoryReferenceStatus = 'active' | 'inactive'

export interface SalesInventoryReferenceRow {
  code: string
  name: string
  status: SalesInventoryReferenceStatus
  source: 'erpnext' | 'local-fallback'
  parityScope: string
  referenceType: SalesInventoryReferenceTab
}

export interface SalesInventoryReferenceQuery {
  keyword: string
  status: string
  source: string
}

interface SalesInventoryReferenceLoadResult {
  rows: SalesInventoryReferenceRow[]
  usingFallback: boolean
}

const CUSTOMER_FALLBACK_ROWS: SalesInventoryReferenceRow[] = [
  {
    code: 'CUST-REF-001',
    name: '华东直营客户',
    status: 'active',
    source: 'local-fallback',
    parityScope: 'sales-inventory-references',
    referenceType: 'customers',
  },
  {
    code: 'CUST-REF-002',
    name: '华南分销客户',
    status: 'active',
    source: 'local-fallback',
    parityScope: 'foundation-customer',
    referenceType: 'customers',
  },
  {
    code: 'CUST-REF-003',
    name: '停用样例客户',
    status: 'inactive',
    source: 'local-fallback',
    parityScope: 'foundation-customer',
    referenceType: 'customers',
  },
]

const SUPPLIER_FALLBACK_ROWS: SalesInventoryReferenceRow[] = [
  {
    code: 'SUP-REF-001',
    name: '华东面料供应商',
    status: 'active',
    source: 'local-fallback',
    parityScope: 'sales-inventory-references',
    referenceType: 'suppliers',
  },
  {
    code: 'SUP-REF-002',
    name: '辅料协作供应商',
    status: 'active',
    source: 'local-fallback',
    parityScope: 'foundation-supplier',
    referenceType: 'suppliers',
  },
  {
    code: 'SUP-REF-003',
    name: '停用样例供应商',
    status: 'inactive',
    source: 'local-fallback',
    parityScope: 'foundation-supplier',
    referenceType: 'suppliers',
  },
]

const normalizeParityScope = (parity: string, tab: SalesInventoryReferenceTab): string => {
  if (parity === 'foundation-customer') return 'foundation-customer'
  if (parity === 'foundation-supplier') return 'foundation-supplier'
  return tab === 'customers' ? 'sales-inventory-references' : 'sales-inventory-references'
}

const applyParityScope = (
  rows: SalesInventoryReferenceRow[],
  parity: string,
  tab: SalesInventoryReferenceTab,
): SalesInventoryReferenceRow[] =>
  rows.map((row) => ({
    ...row,
    parityScope: normalizeParityScope(parity, tab),
  }))

const normalizeCustomerRow = (item: CustomerItem, parity: string): SalesInventoryReferenceRow => ({
  code: item.name,
  name: item.customer_name?.trim() || item.name,
  status: item.disabled ? 'inactive' : 'active',
  source: 'erpnext',
  parityScope: normalizeParityScope(parity, 'customers'),
  referenceType: 'customers',
})

const loadCustomerRows = async (parity: string): Promise<SalesInventoryReferenceLoadResult> => {
  try {
    const response = await fetchSalesInventoryCustomers({ page: 1, page_size: 100 })
    const remoteRows = response.data.items.map((item) => normalizeCustomerRow(item, parity))
    if (remoteRows.length > 0) {
      return {
        rows: remoteRows,
        usingFallback: false,
      }
    }
  } catch {
    // fall through to readonly fallback rows
  }

  return {
    rows: applyParityScope(CUSTOMER_FALLBACK_ROWS, parity, 'customers'),
    usingFallback: true,
  }
}

const loadSupplierRows = async (parity: string): Promise<SalesInventoryReferenceLoadResult> => ({
  rows: applyParityScope(SUPPLIER_FALLBACK_ROWS, parity, 'suppliers'),
  usingFallback: true,
})

export const resolveReferenceTab = (
  tabValue: unknown,
  parityValue: unknown,
): SalesInventoryReferenceTab => {
  const parity = String(parityValue || '').trim().toLowerCase()
  if (parity === 'foundation-supplier') return 'suppliers'
  const tab = String(tabValue || '').trim().toLowerCase()
  return tab === 'suppliers' ? 'suppliers' : 'customers'
}

export const loadSalesInventoryReferenceRows = async (
  tab: SalesInventoryReferenceTab,
  parity: string,
): Promise<SalesInventoryReferenceLoadResult> => {
  if (tab === 'suppliers') {
    return loadSupplierRows(parity)
  }
  return loadCustomerRows(parity)
}

export const filterReferenceRows = (
  rows: SalesInventoryReferenceRow[],
  query: SalesInventoryReferenceQuery,
): SalesInventoryReferenceRow[] => {
  const keyword = query.keyword.trim().toLowerCase()
  const status = query.status.trim().toLowerCase()
  const source = query.source.trim().toLowerCase()
  return rows.filter((row) => {
    if (status && row.status !== status) return false
    if (source && row.source !== source) return false
    if (!keyword) return true
    return [row.code, row.name, row.parityScope].join('|').toLowerCase().includes(keyword)
  })
}
