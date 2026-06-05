import { fetchSalesInventoryCustomers, type CustomerItem } from '@/api/sales_inventory'

export type SalesInventoryReferenceTab = 'customers' | 'suppliers'
export type SalesInventoryReferenceStatus = 'active' | 'inactive'
export type SalesInventoryReferenceSourceValidationState = 'verified' | 'fallback' | 'missing'
export type SalesInventoryReferenceBridgeStatus = 'ok' | 'warn' | 'blocked'
export type SalesInventoryReferenceParityGuardState =
  | 'reference-default'
  | 'foundation-customer'
  | 'foundation-supplier'

export interface SalesInventoryReferenceRow {
  code: string
  name: string
  status: SalesInventoryReferenceStatus
  source: 'erpnext' | 'local-fallback'
  parityScope: string
  referenceType: SalesInventoryReferenceTab
  sourceValidationState: SalesInventoryReferenceSourceValidationState
  sourceValidationLabel: string
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

export interface SalesInventoryReferenceRouteItem {
  key: string
  label: string
  route: string
  active: boolean
  note: string
}

export interface SalesInventoryReferenceBridgeRow {
  key: string
  label: string
  status: SalesInventoryReferenceBridgeStatus
  summary: string
  recommendation: string
}

export interface SalesInventoryReferenceGuardSummary {
  activeTab: SalesInventoryReferenceTab
  parityScopeLabel: string
  parityGuardState: SalesInventoryReferenceParityGuardState
  parityGuardLabel: string
  sourceValidationState: SalesInventoryReferenceSourceValidationState
  sourceValidationLabel: string
  readonlySourceTag: string
  readonlyGuardReason: string
  blockedReason: string
  remainingGap: string
  missingSourcePrompt: string
  verifiedCount: number
  fallbackCount: number
  missingCount: number
  blockedCount: number
  routeItems: SalesInventoryReferenceRouteItem[]
  bridgeRows: SalesInventoryReferenceBridgeRow[]
  cardValues: {
    queryScope: string
    bridgeNodes: string
    blockedCount: string
    sourceState: string
  }
}

const CUSTOMER_FALLBACK_PROMPT = '客户引用档案当前无法从 ERPNext 校验，按 fail-closed 策略切换到本地只读回退视图。'
const SUPPLIER_MISSING_PROMPT = '供应商引用档案当前没有 ERPNext 直连来源，仅提供 foundation-supplier parity 下的本地只读回退视图。'
const SALES_INVENTORY_REFERENCE_REMAINING_GAP =
  '真实订单写入、库存调整、导出、ERPNext 联动与后台修复未开放；客户/供应商引用桥仍需人工核对。'

const CUSTOMER_FALLBACK_ROWS: SalesInventoryReferenceRow[] = [
  {
    code: 'CUST-REF-001',
    name: '华东直营客户',
    status: 'active',
    source: 'local-fallback',
    parityScope: 'sales-inventory-references',
    referenceType: 'customers',
    sourceValidationState: 'fallback',
    sourceValidationLabel: '客户来源回退到本地只读',
    readonlySourceTag: '客户本地回退',
    missingSourcePrompt: CUSTOMER_FALLBACK_PROMPT,
  },
  {
    code: 'CUST-REF-002',
    name: '华南分销客户',
    status: 'active',
    source: 'local-fallback',
    parityScope: 'foundation-customer',
    referenceType: 'customers',
    sourceValidationState: 'fallback',
    sourceValidationLabel: '客户来源回退到本地只读',
    readonlySourceTag: '客户本地回退',
    missingSourcePrompt: CUSTOMER_FALLBACK_PROMPT,
  },
  {
    code: 'CUST-REF-003',
    name: '停用样例客户',
    status: 'inactive',
    source: 'local-fallback',
    parityScope: 'foundation-customer',
    referenceType: 'customers',
    sourceValidationState: 'fallback',
    sourceValidationLabel: '客户来源回退到本地只读',
    readonlySourceTag: '客户本地回退',
    missingSourcePrompt: CUSTOMER_FALLBACK_PROMPT,
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
    sourceValidationState: 'missing',
    sourceValidationLabel: '供应商来源缺失',
    readonlySourceTag: '供应商缺失直连来源',
    missingSourcePrompt: SUPPLIER_MISSING_PROMPT,
  },
  {
    code: 'SUP-REF-002',
    name: '辅料协作供应商',
    status: 'active',
    source: 'local-fallback',
    parityScope: 'foundation-supplier',
    referenceType: 'suppliers',
    sourceValidationState: 'missing',
    sourceValidationLabel: '供应商来源缺失',
    readonlySourceTag: '供应商缺失直连来源',
    missingSourcePrompt: SUPPLIER_MISSING_PROMPT,
  },
  {
    code: 'SUP-REF-003',
    name: '停用样例供应商',
    status: 'inactive',
    source: 'local-fallback',
    parityScope: 'foundation-supplier',
    referenceType: 'suppliers',
    sourceValidationState: 'missing',
    sourceValidationLabel: '供应商来源缺失',
    readonlySourceTag: '供应商缺失直连来源',
    missingSourcePrompt: SUPPLIER_MISSING_PROMPT,
  },
]

const normalizeParityScope = (parity: string, tab: SalesInventoryReferenceTab): string => {
  if (parity === 'foundation-customer') return 'foundation-customer'
  if (parity === 'foundation-supplier') return 'foundation-supplier'
  return tab === 'customers' ? 'sales-inventory-references' : 'sales-inventory-references'
}

const resolveParityGuardState = (parity: string): SalesInventoryReferenceParityGuardState => {
  if (parity === 'foundation-customer') return 'foundation-customer'
  if (parity === 'foundation-supplier') return 'foundation-supplier'
  return 'reference-default'
}

const parityGuardLabel = (state: SalesInventoryReferenceParityGuardState): string => {
  if (state === 'foundation-customer') return 'foundation-customer parity'
  if (state === 'foundation-supplier') return 'foundation-supplier parity'
  return 'sales-inventory-references'
}

const sourceValidationLabel = (
  state: SalesInventoryReferenceSourceValidationState,
  tab: SalesInventoryReferenceTab,
): string => {
  if (state === 'verified') return tab === 'customers' ? 'ERPNext客户来源已校验' : 'ERPNext供应商来源已校验'
  if (state === 'fallback') return tab === 'customers' ? '客户来源回退到本地只读' : '供应商来源回退到本地只读'
  return tab === 'customers' ? '客户来源缺失' : '供应商来源缺失'
}

const readonlySourceTag = (
  state: SalesInventoryReferenceSourceValidationState,
  tab: SalesInventoryReferenceTab,
): string => {
  if (state === 'verified') return tab === 'customers' ? '客户来源已校验' : '供应商来源已校验'
  if (state === 'fallback') return tab === 'customers' ? '客户本地回退' : '供应商本地回退'
  return tab === 'customers' ? '客户缺失直连来源' : '供应商缺失直连来源'
}

const bridgeStatusLabel = (status: SalesInventoryReferenceBridgeStatus): string => {
  if (status === 'ok') return 'ok'
  if (status === 'warn') return 'warn'
  return 'blocked'
}

const missingSourcePrompt = (
  state: SalesInventoryReferenceSourceValidationState,
  tab: SalesInventoryReferenceTab,
): string => {
  if (state === 'fallback' && tab === 'customers') return CUSTOMER_FALLBACK_PROMPT
  if (state === 'missing') return SUPPLIER_MISSING_PROMPT
  return ''
}

const resolveSourceValidationState = (
  tab: SalesInventoryReferenceTab,
  source: SalesInventoryReferenceRow['source'],
  usingFallback: boolean,
): SalesInventoryReferenceSourceValidationState => {
  if (tab === 'suppliers') return 'missing'
  if (source === 'erpnext' && !usingFallback) return 'verified'
  return 'fallback'
}

const decorateRows = (
  rows: SalesInventoryReferenceRow[],
  tab: SalesInventoryReferenceTab,
  usingFallback: boolean,
): SalesInventoryReferenceRow[] =>
  rows.map((row) => {
    const state = resolveSourceValidationState(tab, row.source, usingFallback)
    return {
      ...row,
      sourceValidationState: state,
      sourceValidationLabel: sourceValidationLabel(state, tab),
      readonlySourceTag: readonlySourceTag(state, tab),
      missingSourcePrompt: missingSourcePrompt(state, tab),
    }
  })

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
  sourceValidationState: 'verified',
  sourceValidationLabel: sourceValidationLabel('verified', 'customers'),
  readonlySourceTag: readonlySourceTag('verified', 'customers'),
  missingSourcePrompt: '',
})

const loadCustomerRows = async (parity: string): Promise<SalesInventoryReferenceLoadResult> => {
  try {
    const response = await fetchSalesInventoryCustomers({ page: 1, page_size: 100 })
    const remoteRows = response.data.items.map((item) => normalizeCustomerRow(item, parity))
    if (remoteRows.length > 0) {
      return {
        rows: decorateRows(remoteRows, 'customers', false),
        usingFallback: false,
      }
    }
  } catch {
    // fall through to readonly fallback rows
  }

  return {
    rows: decorateRows(applyParityScope(CUSTOMER_FALLBACK_ROWS, parity, 'customers'), 'customers', true),
    usingFallback: true,
  }
}

const loadSupplierRows = async (parity: string): Promise<SalesInventoryReferenceLoadResult> => ({
  rows: decorateRows(applyParityScope(SUPPLIER_FALLBACK_ROWS, parity, 'suppliers'), 'suppliers', true),
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

export const buildSalesInventoryReferenceGuardSummary = (
  rows: SalesInventoryReferenceRow[],
  tab: SalesInventoryReferenceTab,
  parity: string,
  usingFallback: boolean,
): SalesInventoryReferenceGuardSummary => {
  const parityState = resolveParityGuardState(parity)
  const sourceState: SalesInventoryReferenceSourceValidationState = tab === 'suppliers'
    ? 'missing'
    : usingFallback
      ? 'fallback'
      : rows.length > 0
        ? 'verified'
        : 'missing'
  const blockedCount = rows.filter((row) => row.sourceValidationState !== 'verified').length
  const queryScopeLabel = `${tab === 'customers' ? 'customers' : 'suppliers'} / ${parityGuardLabel(parityState)}`
  const blockedReason = sourceState === 'missing'
    ? '供应商引用桥当前缺少 ERPNext 直连来源，只保留 foundation-supplier parity 与本地只读回退说明。'
    : sourceState === 'fallback'
      ? '客户引用桥当前未通过 ERPNext 实时校验，已切换到本地只读回退视图。'
      : '当前只开放销售库存引用桥与基础资料 parity 核对，订单写入、库存调整与导出继续禁用。'
  const bridgeRows: SalesInventoryReferenceBridgeRow[] = [
    {
      key: 'reference-bridge',
      label: tab === 'customers' ? '客户引用桥摘要' : '供应商引用桥摘要',
      status: sourceState === 'verified' ? 'ok' : sourceState === 'fallback' ? 'warn' : 'blocked',
      summary: `${tab === 'customers' ? '客户' : '供应商'}查询态当前回读 ${rows.length} 条引用记录，来源状态 ${sourceValidationLabel(sourceState, tab)}。`,
      recommendation: '仅保留引用桥摘要与只读核对，不开放真实订单写入或库存调整。',
    },
    {
      key: 'foundation-parity',
      label: '基础资料 parity',
      status: parityState === 'reference-default' ? 'ok' : 'warn',
      summary: parityState === 'foundation-supplier'
        ? '当前入口来自 foundation-supplier，页面保持 suppliers 查询态与 parity 标签同步。'
        : parityState === 'foundation-customer'
          ? '当前入口来自 foundation-customer，仅保留客户侧只读核对。'
          : '当前入口为 sales-inventory references 默认只读查询态。',
      recommendation: 'parity 仅用于说明入口映射，不触发基础资料写入或后台修复。',
    },
    {
      key: 'blocked-reason',
      label: 'blocked 原因',
      status: blockedCount > 0 ? 'blocked' : 'warn',
      summary: blockedReason,
      recommendation: 'disabled guard 按钮仅作说明，导出、ERPNext 联动与后台修复保持禁用。',
    },
  ]
  const routeItems: SalesInventoryReferenceRouteItem[] = [
    {
      key: 'suppliers-query',
      label: 'suppliers 查询态',
      route: '/sales-inventory/references?tab=suppliers',
      active: tab === 'suppliers' && parityState === 'reference-default',
      note: '只读展示供应商引用桥摘要与来源缺口说明。',
    },
    {
      key: 'customers-query',
      label: 'customers 查询态',
      route: '/sales-inventory/references?tab=customers',
      active: tab === 'customers' && parityState === 'reference-default',
      note: '只读展示客户引用桥摘要与回退状态。',
    },
    {
      key: 'foundation-supplier-parity',
      label: 'foundation-supplier parity',
      route: '/foundation/supplier -> /sales-inventory/references?tab=suppliers&parity=foundation-supplier',
      active: parityState === 'foundation-supplier',
      note: '基础资料供应商入口映射到 suppliers 查询态，只读核对引用桥。',
    },
  ]

  return {
    activeTab: tab,
    parityScopeLabel: parityGuardLabel(parityState),
    parityGuardState: parityState,
    parityGuardLabel: parityGuardLabel(parityState),
    sourceValidationState: sourceState,
    sourceValidationLabel: sourceValidationLabel(sourceState, tab),
    readonlySourceTag: readonlySourceTag(sourceState, tab),
    readonlyGuardReason: [
      `当前页面仅提供${tab === 'customers' ? '客户' : '供应商'}引用桥与 parity 只读核对`,
      `已锁定入口 ${parityGuardLabel(parityState)}`,
      'order write / inventory adjust / export disabled',
    ].join('；'),
    blockedReason,
    remainingGap: SALES_INVENTORY_REFERENCE_REMAINING_GAP,
    missingSourcePrompt: missingSourcePrompt(sourceState, tab),
    verifiedCount: rows.filter((row) => row.sourceValidationState === 'verified').length,
    fallbackCount: rows.filter((row) => row.sourceValidationState === 'fallback').length,
    missingCount: rows.filter((row) => row.sourceValidationState === 'missing').length,
    blockedCount,
    routeItems,
    bridgeRows,
    cardValues: {
      queryScope: queryScopeLabel,
      bridgeNodes: `${rows.length} 条`,
      blockedCount: blockedCount > 0 ? `${blockedCount} 处` : '无阻断',
      sourceState: bridgeStatusLabel(
        sourceState === 'verified' ? 'ok' : sourceState === 'fallback' ? 'warn' : 'blocked',
      ),
    },
  }
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
    return [
      row.code,
      row.name,
      row.parityScope,
      row.sourceValidationLabel,
      row.readonlySourceTag,
      row.missingSourcePrompt,
    ].join('|').toLowerCase().includes(keyword)
  })
}
