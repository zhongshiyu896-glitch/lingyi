export type SalesInventoryReferenceGuardReadonlyState =
  | 'ready-readonly'
  | 'query-guarded'
  | 'source-warning'
  | 'permission-guarded'

export type SalesInventoryReferenceGuardReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export const SALES_INVENTORY_REFERENCE_GUARD_STATE_LABELS: Record<
  SalesInventoryReferenceGuardReadonlyState,
  string
> = {
  'ready-readonly': 'foundation-source 已回读 / 只读守卫',
  'query-guarded': '当前筛选无结果 / 保留只读壳层',
  'source-warning': '来源存在缺口或回退',
  'permission-guarded': 'reference-source 权限只读守卫',
}

export const SALES_INVENTORY_REFERENCE_GUARD_STATE_TAGS: Record<
  SalesInventoryReferenceGuardReadonlyState,
  SalesInventoryReferenceGuardReadonlyTagType
> = {
  'ready-readonly': 'success',
  'query-guarded': 'warning',
  'source-warning': 'warning',
  'permission-guarded': 'danger',
}

export const SALES_INVENTORY_REFERENCE_GUARD_SUMMARY_FIELDS = [
  { key: 'referenceCountLabel', label: '引用条目' },
  { key: 'activeReferenceCountLabel', label: '启用条目' },
  { key: 'sourceIssueCountLabel', label: '来源阻断' },
  { key: 'guardedActionCountLabel', label: '禁用动作' },
] as const

export type SalesInventoryReferenceGuardSummaryFieldKey =
  (typeof SALES_INVENTORY_REFERENCE_GUARD_SUMMARY_FIELDS)[number]['key']

export const SALES_INVENTORY_REFERENCE_GUARD_PARITY_LABEL = 'foundation-reference parity'
export const SALES_INVENTORY_REFERENCE_GUARD_FOCUS_LABEL = 'reference-source focus'
export const SALES_INVENTORY_REFERENCE_GUARD_READONLY_GUARD_REASON =
  '当前切片仅开放 foundation-source guard / source-status 只读核对；真实客户/供应商维护、导入、导出、库存写入、ERPNext、outbox、worker 与 production write 保持冻结。'
export const SALES_INVENTORY_REFERENCE_GUARD_REMAINING_GAP =
  '未开放客户/供应商真实维护、导入、导出、库存写入、ERPNext、outbox、worker。'
export const SALES_INVENTORY_REFERENCE_GUARD_WRITE_BOUNDARY =
  'GET-only | write_request_count=0 | enabled_write_action_texts=[] | forbidden_write_calls=[]'

export const SALES_INVENTORY_REFERENCE_GUARD_DISABLED_ACTIONS = [
  {
    label: '客户维护',
    reason: 'customer write / customer-supplier maintenance 链路冻结',
  },
  {
    label: '供应商维护',
    reason: 'supplier write / customer-supplier maintenance 链路冻结',
  },
  {
    label: '导入引用',
    reason: 'reference import / customer-supplier write 链路冻结',
  },
  {
    label: '导出引用',
    reason: 'export / download 链路冻结',
  },
  {
    label: '库存写入',
    reason: 'inventory write / cross-module execution 链路冻结',
  },
  {
    label: 'ERPNext 联动',
    reason: 'ERPNext / outbox / worker / production write 链路冻结',
  },
] as const
