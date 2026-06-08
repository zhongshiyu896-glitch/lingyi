export type SalesInventoryReferencePartnerScopeReadonlyState =
  | 'ready-readonly'
  | 'query-guarded'
  | 'source-warning'
  | 'permission-guarded'

export type SalesInventoryReferencePartnerScopeReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export const SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_STATE_LABELS: Record<
  SalesInventoryReferencePartnerScopeReadonlyState,
  string
> = {
  'ready-readonly': 'partner-scope 已回读 / 只读守卫',
  'query-guarded': 'partner-scope 查询守卫',
  'source-warning': 'partner-source 缺口或回退',
  'permission-guarded': 'partner-source 权限只读守卫',
}

export const SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_STATE_TAGS: Record<
  SalesInventoryReferencePartnerScopeReadonlyState,
  SalesInventoryReferencePartnerScopeReadonlyTagType
> = {
  'ready-readonly': 'success',
  'query-guarded': 'warning',
  'source-warning': 'warning',
  'permission-guarded': 'danger',
}

export const SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_SUMMARY_FIELDS = [
  { key: 'referenceCountLabel', label: '引用条目' },
  { key: 'activeReferenceCountLabel', label: '启用条目' },
  { key: 'partnerIssueCountLabel', label: '来源阻断' },
  { key: 'guardedActionCountLabel', label: '禁用动作' },
] as const

export type SalesInventoryReferencePartnerScopeSummaryFieldKey =
  (typeof SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_SUMMARY_FIELDS)[number]['key']

export const SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_PARITY_LABEL = 'foundation-reference parity'
export const SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_FOCUS_LABEL = 'partner-source focus'
export const SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_READONLY_GUARD_REASON =
  '当前切片仅开放 partner-scope / foundation-reference 只读核对；真实 import/export/customer-supplier write/stock-write/outbox/worker/ERPNext/production write 保持冻结。'
export const SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_REMAINING_GAP =
  '未开放客户/供应商真实维护、引用导入导出、库存写入、ERPNext、outbox、worker。'
export const SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_WRITE_BOUNDARY =
  'GET-only | write_request_count=0 | enabled_write_action_texts=[] | forbidden_write_calls=[]'

export const SALES_INVENTORY_REFERENCE_PARTNER_SCOPE_DISABLED_ACTIONS = [
  { key: 'customer-write', label: '客户维护', reason: 'customer write disabled' },
  { key: 'supplier-write', label: '供应商维护', reason: 'supplier write disabled' },
  { key: 'reference-import', label: '导入引用', reason: 'import disabled' },
  { key: 'reference-export', label: '导出引用', reason: 'export disabled' },
  { key: 'stock-write', label: '库存写入', reason: 'stock-write disabled' },
  {
    key: 'erpnext-outbox',
    label: 'ERPNext / Outbox',
    reason: 'ERPNext / outbox / worker / production write disabled',
  },
] as const
