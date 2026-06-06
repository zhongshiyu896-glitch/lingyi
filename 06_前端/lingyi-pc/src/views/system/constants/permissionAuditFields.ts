export type PermissionAuditReadonlyTone = 'success' | 'info' | 'warning' | 'danger'

export interface PermissionAuditReadonlySummaryCard {
  key: string
  label: string
  value: string
  hint: string
  tone: PermissionAuditReadonlyTone
}

export interface PermissionAuditReadonlyLineItem {
  key: string
  label: string
  value: string
  tone: PermissionAuditReadonlyTone
}

export interface PermissionAuditReadonlyEntry {
  key: string
  title: string
  owner: string
  source: string
  status: string
  tone: PermissionAuditReadonlyTone
  summary: string
  details: string[]
}

export interface PermissionAuditReadonlyDisabledAction {
  key: string
  label: string
  reason: string
}

export const permissionAuditReadonlyRouteContracts = {
  baseline: '/permissions/governance',
  active: '/permissions/governance?tab=audit-readiness',
  parityAlias: '/system/management?parity=permission-audit&tab=governance',
} as const

export const permissionAuditReadonlyDisabledActions: PermissionAuditReadonlyDisabledAction[] = [
  {
    key: 'permission-export',
    label: '权限导出',
    reason: '权限导出属于副作用动作，当前只读切片保持 disabled。',
  },
  {
    key: 'backend-remediation',
    label: '后台修复',
    reason: '后台修复链路未开放，不允许在当前页面执行。',
  },
  {
    key: 'audit-report-generation',
    label: '审计报表生成',
    reason: '报表生成与下载链路未开放，仅保留可见原因。',
  },
]

export const permissionAuditReadonlyFallbackBlockedReasons = [
  '权限导出、后台修复、报表生成仍处于 guarded_readonly。',
  'ERPNext、outbox、worker 与 production write path 未开放。',
]
