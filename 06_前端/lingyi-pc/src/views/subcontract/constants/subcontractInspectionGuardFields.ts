export type SubcontractInspectionGuardTone = 'success' | 'warning' | 'danger' | 'info'

export interface SubcontractInspectionGuardSummaryCard {
  key: string
  label: string
  value: string
  hint: string
  tone: SubcontractInspectionGuardTone
}

export interface SubcontractInspectionGuardLineItem {
  key: string
  label: string
  value: string
  tone: SubcontractInspectionGuardTone
}

export interface SubcontractInspectionGuardDisabledAction {
  key: string
  label: string
  reason: string
}

export interface SubcontractInspectionGuardEntry {
  key: string
  title: string
  owner: string
  source: string
  status: string
  tone: SubcontractInspectionGuardTone
  summary: string
  details: string[]
}

export const subcontractInspectionGuardDisabledActions = [
  { key: 'receive', label: '收货过账', reason: 'receive write path 冻结' },
  { key: 'issue', label: '发料回写', reason: 'issue write path 冻结' },
  { key: 'settlement', label: '结算放行', reason: 'settlement write path 冻结' },
  { key: 'export', label: '导出验货', reason: 'export 冻结' },
] as const satisfies ReadonlyArray<SubcontractInspectionGuardDisabledAction>

export const subcontractInspectionGuardFallbackBlockedReasons = [
  '真实收货、发料、结算、导出、ERPNext、outbox 与 worker 链路均保持冻结。',
  '当前切片仅保留 inspection-guard readonly summary 与本地试用详情。',
] as const

export const subcontractInspectionGuardRemainingGaps = [
  '真实收货未开放',
  '真实发料回写未开放',
  '结算与导出未开放',
  'ERPNext / outbox / worker 未开放',
] as const
