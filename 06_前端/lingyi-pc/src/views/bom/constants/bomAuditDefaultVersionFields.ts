export type BomAuditReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'
export type BomAuditDefaultVersionState = 'default-confirmed' | 'non-default' | 'fallback' | 'missing'

export const BOM_AUDIT_DEFAULT_VERSION_STATE_TAGS: Record<BomAuditDefaultVersionState, BomAuditReadonlyTagType> = {
  'default-confirmed': 'success',
  'non-default': 'warning',
  fallback: 'info',
  missing: 'danger',
}

export const BOM_AUDIT_DEFAULT_VERSION_STATE_LABELS: Record<BomAuditDefaultVersionState, string> = {
  'default-confirmed': '默认版本已识别',
  'non-default': '当前版本非默认',
  fallback: '默认版本待真实校验',
  missing: '默认版本来源缺失',
}

export const BOM_AUDIT_PARITY_SCOPE_LABELS: Record<string, string> = {
  'product-style': 'product-style parity',
  default: 'bom-audit-readonly',
}

export const BOM_AUDIT_DEFAULT_VERSION_FIELDS = [
  { key: 'auditSourceLabel', label: '审计来源' },
  { key: 'defaultVersionStatusLabel', label: '默认版本状态' },
  { key: 'defaultVersionCoverageLabel', label: '版本覆盖' },
  { key: 'parityScopeLabel', label: '当前入口' },
] as const

export const BOM_AUDIT_READONLY_GUARD_LABEL =
  '默认版本切换、审批、导出与库存影响保持只读守卫。'

export const BOM_AUDIT_WRITE_BOUNDARY_LABEL = 'set-default / activate / export disabled'

export const BOM_AUDIT_REMAINING_GAP_LABEL =
  '未开放真实 BOM 保存、默认版本切换写入、审批、导出、库存影响、ERPNext、outbox、worker。'
