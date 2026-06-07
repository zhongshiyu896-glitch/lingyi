export type FactoryStatementPrintAuditStatus = 'ok' | 'warn' | 'blocked'

export type FactoryStatementPrintAuditCardKey =
  | 'routeScope'
  | 'sourceStatus'
  | 'itemStatus'
  | 'printGuard'

export interface FactoryStatementPrintAuditCardField {
  key: FactoryStatementPrintAuditCardKey
  label: string
}

export interface FactoryStatementPrintAuditRouteItem {
  key: string
  label: string
  route: string
  active: boolean
  note: string
}

export interface FactoryStatementPrintAuditStatusRow {
  key: string
  label: string
  status: FactoryStatementPrintAuditStatus
  summary: string
  recommendation: string
}

export interface FactoryStatementPrintAuditGuardAction {
  key: string
  label: string
  reason: string
}

export const FACTORY_STATEMENT_PRINT_AUDIT_CARD_FIELDS: FactoryStatementPrintAuditCardField[] = [
  { key: 'routeScope', label: '当前只读上下文' },
  { key: 'sourceStatus', label: 'source/status' },
  { key: 'itemStatus', label: 'item/status' },
  { key: 'printGuard', label: '打印 guard' },
]

export const FACTORY_STATEMENT_PRINT_AUDIT_GUARD_ACTIONS: FactoryStatementPrintAuditGuardAction[] = [
  {
    key: 'confirm',
    label: '确认',
    reason: 'confirm 在 print-audit/source readonly 切片保持禁用，避免触发真实单据确认。',
  },
  {
    key: 'cancel',
    label: '取消',
    reason: 'cancel 在 print-audit/source readonly 切片保持禁用，避免触发真实单据取消。',
  },
  {
    key: 'settlement',
    label: '结算',
    reason: 'settlement 在 print-audit/source readonly 切片仅保留只读说明，不触发应付或结算写链路。',
  },
  {
    key: 'print',
    label: '打印',
    reason: 'print 仅保留只读预览摘要，不触发真实打印提交。',
  },
  {
    key: 'export',
    label: '导出',
    reason: 'export 在 print-audit/source readonly 切片保持禁用，不开放真实导出执行。',
  },
  {
    key: 'download',
    label: '下载',
    reason: 'download 链路保持禁用，避免触发真实文件输出。',
  },
  {
    key: 'outbox',
    label: 'Outbox',
    reason: 'Outbox 状态仅供只读观察，不触发同步队列写入。',
  },
  {
    key: 'worker',
    label: 'Worker',
    reason: 'Worker 处理链路仅保留只读说明，不触发后台任务。',
  },
  {
    key: 'erpnext',
    label: 'ERPNext',
    reason: 'ERPNext 适配器链路在 print-audit/source readonly 切片保持禁用。',
  },
  {
    key: 'production-write',
    label: 'production write',
    reason: '所有真实 write 链路保持 fail-closed，不允许跨模块执行。',
  },
]

export const FACTORY_STATEMENT_PRINT_AUDIT_REMAINING_GAP =
  '真实 confirm/cancel/settlement/export/download、ERPNext、outbox/worker 与 production write 均未开放；print-source 仍需人工核对。'
