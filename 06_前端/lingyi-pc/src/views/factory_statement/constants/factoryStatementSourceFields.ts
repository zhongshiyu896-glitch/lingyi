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
    key: 'confirm',
    label: '确认',
    reason: 'confirm 入口在 source-readonly 切片保持禁用，避免触发真实单据确认。',
  },
  {
    key: 'cancel',
    label: '取消',
    reason: 'cancel 入口在 source-readonly 切片保持禁用，避免触发真实单据取消。',
  },
  {
    key: 'settlement',
    label: '结算',
    reason: 'settlement / payable draft 在 source-readonly 切片仅保留只读说明，不触发应付草稿链路。',
  },
  {
    key: 'export',
    label: '导出',
    reason: 'export 仅保留只读提示，不开放真实导出执行。',
  },
  {
    key: 'download',
    label: '下载',
    reason: 'download 链路保持禁用，避免触发真实文件输出。',
  },
  {
    key: 'outbox',
    label: 'Outbox',
    reason: 'Outbox 状态仅可观察，不触发同步队列写入。',
  },
  {
    key: 'worker',
    label: 'Worker',
    reason: 'Worker 处理链路仅保留只读说明，不触发后台任务。',
  },
  {
    key: 'erpnext',
    label: 'ERPNext',
    reason: 'ERPNext 适配器链路在 source-readonly 切片保持禁用。',
  },
  {
    key: 'production-write',
    label: 'production write',
    reason: '所有真实 write 链路保持 fail-closed，不允许跨模块执行。',
  },
]

export const FACTORY_STATEMENT_SOURCE_REMAINING_GAP =
  '真实 confirm/cancel/settlement/export/download、ERPNext、outbox/worker 与 production write 均未开放；statement-source 断点仍需人工核对。'
