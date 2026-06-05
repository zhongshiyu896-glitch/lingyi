export type SystemFoundationSubjectStatus = 'ok' | 'warn' | 'blocked'

export interface SystemFoundationSubjectRow {
  key: string
  label: string
  status: SystemFoundationSubjectStatus
  summary: string
  recommendation: string
}

export interface SystemFoundationSubjectRouteItem {
  key: string
  label: string
  route: string
  active: boolean
  note: string
}

export interface SystemFoundationSubjectGuardAction {
  key: string
  label: string
  reason: string
}

export const systemFoundationSubjectExpectedDictionarySources = ['static_registry', 'policy_registry'] as const
export const systemFoundationSubjectExpectedHealthChecks = [
  'permission_source',
  'ui_route_present',
  'readonly_contract',
] as const

export const systemFoundationSubjectReadonlyGuardActions: SystemFoundationSubjectGuardAction[] = [
  {
    key: 'subject-maintain',
    label: '主体维护',
    reason: 'foundation-subjects 只读切片不开放主体目录维护。',
  },
  {
    key: 'config-write',
    label: '配置写入',
    reason: 'dictionary/config/report 数据保持 guarded_readonly。',
  },
  {
    key: 'report-generate',
    label: '报告生成',
    reason: '报表生成属于副作用动作，当前仅允许只读核对。',
  },
  {
    key: 'export-download',
    label: '导出下载',
    reason: '导出/下载未开放，避免触发真实副作用。',
  },
]

export const systemFoundationSubjectRemainingGap =
  '真实主体目录维护、系统配置写入、报表生成、导出与后台修复均未开放；foundation subject parity/readiness 仍需人工核对。'
