export type FactoryStatementSourceReadonlyStatus = 'ok' | 'warn' | 'blocked'

export type FactoryStatementSourceCardKey =
  | 'routeScope'
  | 'breakpointCount'
  | 'driftSeverity'
  | 'payableMirror'

export interface FactoryStatementSourceCardField {
  key: FactoryStatementSourceCardKey
  label: string
}

export interface FactoryStatementSourceRouteItem {
  key: string
  label: string
  route: string
  active: boolean
  note: string
}

export interface FactoryStatementSourceDriftRow {
  key: string
  label: string
  status: FactoryStatementSourceReadonlyStatus
  summary: string
  recommendation: string
}

export interface FactoryStatementSourceGuardAction {
  key: string
  label: string
  reason: string
}

export const FACTORY_STATEMENT_SOURCE_CARD_FIELDS: FactoryStatementSourceCardField[] = [
  { key: 'routeScope', label: '当前只读上下文' },
  { key: 'breakpointCount', label: '来源链断点' },
  { key: 'driftSeverity', label: '账单漂移' },
  { key: 'payableMirror', label: 'payable 镜像' },
]

export const FACTORY_STATEMENT_SOURCE_GUARD_ACTIONS: FactoryStatementSourceGuardAction[] = [
  {
    key: 'payable-writeback',
    label: '支付回写',
    reason: '当前切片只允许来源链断点核对，不开放支付状态回写。',
  },
  {
    key: 'print-execute',
    label: '打印执行',
    reason: '打印仅保留只读预览，不开放真实执行提交。',
  },
  {
    key: 'export-run',
    label: '导出执行',
    reason: '导出链路保持禁用，避免触发真实副作用。',
  },
  {
    key: 'backend-remediation',
    label: '后台修复',
    reason: '后台修复建议仅作只读提示，不触发执行。',
  },
]

export const FACTORY_STATEMENT_SOURCE_REMAINING_GAP =
  '真实支付状态回写、打印执行、导出、ERPNext 联动、后台修复与 outbox/worker 未开放；来源链断点仍需人工核对。'
