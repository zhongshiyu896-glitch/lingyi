export type ReportSourceGuardTone = 'success' | 'warning' | 'danger' | 'info'

export interface ReportSourceGuardSummaryCard {
  key: string
  label: string
  value: string
  hint: string
  tone: ReportSourceGuardTone
}

export interface ReportSourceGuardLineItem {
  key: string
  label: string
  value: string
  tone: ReportSourceGuardTone
}

export interface ReportSourceGuardDisabledAction {
  key: string
  label: string
  reason: string
}

export interface ReportSourceGuardEntry {
  key: string
  title: string
  status: string
  source: string
  tone: ReportSourceGuardTone
  summary: string
  details: string[]
}

export const REPORT_SOURCE_GUARD_DISABLED_ACTIONS = [
  { key: 'export', label: '导出报表', reason: 'report export path frozen by readonly boundary' },
  { key: 'download', label: '下载文件', reason: 'report download path frozen by readonly boundary' },
  { key: 'generate', label: '生成报表', reason: 'report generation path frozen by readonly boundary' },
  { key: 'remediation', label: '目录修复', reason: 'backend remediation path frozen by readonly boundary' },
  { key: 'refresh-permission', label: '刷新权限', reason: 'global permission refresh frozen by report source-guard readonly boundary' },
  { key: 'reload-module-actions', label: '重载模块动作', reason: 'global module action reload frozen by report source-guard readonly boundary' },
] as const satisfies ReadonlyArray<ReportSourceGuardDisabledAction>

export const REPORT_SOURCE_GUARD_FALLBACK_BLOCKED_REASONS = [
  'true report generation/export/download paths remain frozen.',
  'report/system config write paths remain frozen.',
  'backend remediation, ERPNext, outbox and worker paths remain frozen.',
] as const

export const REPORT_SOURCE_GUARD_REMAINING_GAPS = [
  '真实报表生成未开放',
  '真实导出/下载未开放',
  '系统目录/配置写入未开放',
  'backend remediation / ERPNext / outbox / worker 未开放',
] as const
