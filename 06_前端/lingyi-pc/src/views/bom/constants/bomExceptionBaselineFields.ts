export type BomExceptionReadonlyTone = 'success' | 'info' | 'warning' | 'danger'

export interface BomExceptionReadonlySummaryCard {
  key: string
  label: string
  value: string
  hint: string
  tone: BomExceptionReadonlyTone
}

export interface BomExceptionReadonlyLineItem {
  key: string
  label: string
  value: string
  tone: BomExceptionReadonlyTone
}

export interface BomExceptionReadonlyEntry {
  key: string
  title: string
  owner: string
  source: string
  status: string
  tone: BomExceptionReadonlyTone
  summary: string
  details: string[]
}

export interface BomExceptionReadonlyDisabledAction {
  key: string
  label: string
  reason: string
}

export const bomExceptionReadonlyRouteContracts = {
  baseline: '/bom/list?tab=exception-baseline',
  detail: '/bom/detail?mode=readonly-exception',
  parityAlias: '/goodsPlan/materialSamples -> /bom/list?parity=goodsplan-material-samples&tab=exception-baseline',
} as const

export const bomExceptionReadonlyDisabledActions: BomExceptionReadonlyDisabledAction[] = [
  {
    key: 'exception-audit',
    label: '异常审计',
    reason: '只读模式：异常审计动作已禁用。',
  },
  {
    key: 'version-sync',
    label: '版本同步',
    reason: '只读模式：同步链路已禁用，避免触发真实版本切换。',
  },
  {
    key: 'exception-export',
    label: '导出异常基线',
    reason: '只读模式：导出动作已禁用，不触发下载或报表生成。',
  },
]

export const bomExceptionReadonlyFallbackBlockedReasons = [
  'version switching、alternate material true save、sync/export 仍处于 guarded_readonly。',
  'backend remediation、ERPNext、outbox、worker 与 production write path 未开放。',
]

export const bomExceptionReadonlyWriteGuardReason =
  '只读模式：异常基线仅允许查看详情，写入闭环与保存本地对象已禁用。'
