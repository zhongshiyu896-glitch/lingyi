import type {
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

export const SALES_INVENTORY_REFERENCE_GUARD_SUMMARY_FIELDS = [
  { key: 'verifiedCount', label: '已校验来源' },
  { key: 'fallbackCount', label: '回退来源' },
  { key: 'missingCount', label: '缺失来源' },
  { key: 'parityScopeLabel', label: '当前入口' },
] as const
