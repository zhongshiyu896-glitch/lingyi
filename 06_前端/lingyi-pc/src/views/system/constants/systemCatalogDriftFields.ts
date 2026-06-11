export type SystemCatalogDriftStatus = 'ok' | 'warn' | 'blocked'

export interface SystemCatalogDriftRow {
  key: string
  label: string
  status: SystemCatalogDriftStatus
  summary: string
  recommendation: string
}

export interface SystemCatalogDriftRouteItem {
  key: string
  label: string
  route: string
  active: boolean
  note: string
}

export interface SystemCatalogReadonlyGuardAction {
  key: string
  label: string
  reason: string
}

export const systemCatalogBaselineRoute = '/system/management'
export const systemCatalogReadonlyConfigCatalogRoute =
  '/system/management?tab=catalog-drift-readonly&parity=system-catalog'
export const systemCatalogReadonlyFocusRoute =
  '/system/management?tab=catalog-drift-readonly&parity=system-catalog&focus=config-catalog'
export const systemCatalogLegacyRouteAliases = [
  '/system/management?parity=foundation-dictionary',
  '/system/management?tab=catalog-drift',
] as const

export const systemCatalogExpectedConfigGroups = ['ui', 'security', 'audit', 'integration'] as const
export const systemCatalogExpectedDictionarySources = ['static_registry', 'policy_registry'] as const
export const systemCatalogExpectedHealthChecks = [
  'permission_source',
  'system_router_mapping',
  'ui_route_present',
  'readonly_contract',
] as const

export const systemCatalogReadonlyGuardActions: SystemCatalogReadonlyGuardAction[] = [
  {
    key: 'catalog-maintain',
    label: '目录维护',
    reason: '只读目录漂移切片不开放真实目录维护。',
  },
  {
    key: 'config-write',
    label: '配置写入',
    reason: '系统配置写入保持 guarded_readonly。',
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
  {
    key: 'backend-repair',
    label: '后台修复',
    reason: '后台修复建议仅作只读提示，不触发修复执行。',
  },
  {
    key: 'outbox-worker',
    label: 'outbox / worker',
    reason: 'outbox / worker 属于副作用链路，当前只保留禁写说明。',
  },
  {
    key: 'production-write',
    label: 'production write',
    reason: 'production write 严格禁用，当前只允许 GET-only readonly 核对。',
  },
]

export const systemCatalogRemainingGap =
  '真实目录维护、系统配置写入、报表生成、导出和后台修复均未开放；outbox / worker 与 production write 也保持关闭；目录漂移与健康差异仍需人工核对。'
