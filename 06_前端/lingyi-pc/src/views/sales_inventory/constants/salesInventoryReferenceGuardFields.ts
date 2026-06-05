import type {
  SalesInventoryReferenceBridgeStatus,
  SalesInventoryReferenceParityGuardState,
  SalesInventoryReferenceSourceValidationState,
} from '@/api/sales_inventory_references'

type TagType = 'success' | 'warning' | 'danger' | 'info'

export const SALES_INVENTORY_REFERENCE_SOURCE_TAGS: Record<
  SalesInventoryReferenceSourceValidationState,
  TagType
> = {
  verified: 'success',
  fallback: 'warning',
  missing: 'danger',
}

export const SALES_INVENTORY_REFERENCE_PARITY_TAGS: Record<
  SalesInventoryReferenceParityGuardState,
  TagType
> = {
  'reference-default': 'info',
  'foundation-customer': 'warning',
  'foundation-supplier': 'warning',
}

export const SALES_INVENTORY_REFERENCE_BRIDGE_TAGS: Record<
  SalesInventoryReferenceBridgeStatus,
  TagType
> = {
  ok: 'success',
  warn: 'warning',
  blocked: 'danger',
}

export const SALES_INVENTORY_REFERENCE_GUARD_SUMMARY_FIELDS = [
  { key: 'queryScope', label: '当前查询态' },
  { key: 'bridgeNodes', label: '引用桥记录' },
  { key: 'blockedCount', label: '阻断数量' },
  { key: 'sourceState', label: '来源状态' },
] as const

export const SALES_INVENTORY_REFERENCE_GUARD_ACTIONS = [
  {
    key: 'order-write',
    label: '订单写入',
    reason: '当前切片只允许销售库存引用桥核对，不开放真实订单写入。',
  },
  {
    key: 'inventory-adjust',
    label: '库存调整',
    reason: '库存调整属于真实写链路，本地只读切片保持禁用。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '导出仅允许保留禁用态提示，不触发真实执行。',
  },
  {
    key: 'erpnext-sync',
    label: 'ERPNext 联动',
    reason: 'ERPNext 联动与后台修复均不在本切片开放范围内。',
  },
] as const
