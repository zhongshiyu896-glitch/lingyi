export type FactoryStatementPayableReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export type FactoryStatementPayableReadonlyState =
  | 'invoice-created'
  | 'active-sync'
  | 'failed-sync'
  | 'summary-missing'
  | 'no-payable'

export type FactoryStatementPayableFieldKey =
  | 'payableInvoiceLabel'
  | 'latestOutboxStatusLabel'
  | 'payableOutboxCountLabel'
  | 'payableErrorLabel'

export interface FactoryStatementPayableGuardAction {
  key: string
  label: string
  reason: string
}

export const FACTORY_STATEMENT_PAYABLE_STATE_LABELS: Record<FactoryStatementPayableReadonlyState, string> = {
  'invoice-created': '已生成应付草稿镜像',
  'active-sync': '应付同步进行中',
  'failed-sync': '应付同步异常',
  'summary-missing': '应付摘要缺失',
  'no-payable': '未生成应付草稿',
}

export const FACTORY_STATEMENT_PAYABLE_STATE_TAGS: Record<
  FactoryStatementPayableReadonlyState,
  FactoryStatementPayableReadonlyTagType
> = {
  'invoice-created': 'success',
  'active-sync': 'warning',
  'failed-sync': 'danger',
  'summary-missing': 'danger',
  'no-payable': 'info',
}

export const FACTORY_STATEMENT_PAYABLE_SCOPE_LABELS: Record<string, string> = {
  '': 'factory-statement-readonly',
  'foundation-factory': 'foundation-factory parity',
}

export const FACTORY_STATEMENT_PAYABLE_FIELDS = [
  { key: 'payableInvoiceLabel', label: '应付草稿镜像' },
  { key: 'latestOutboxStatusLabel', label: '同步状态' },
  { key: 'payableOutboxCountLabel', label: 'Outbox 条数' },
  { key: 'payableErrorLabel', label: '错误快照' },
] as const satisfies ReadonlyArray<{ key: FactoryStatementPayableFieldKey; label: string }>

export const FACTORY_STATEMENT_PAYABLE_GUARD_ACTIONS: ReadonlyArray<FactoryStatementPayableGuardAction> = [
  {
    key: 'confirm',
    label: '确认',
    reason: 'payable-status readonly 仅回读单据状态与应付镜像，不开放真实确认。',
  },
  {
    key: 'cancel',
    label: '取消',
    reason: 'payable-source 仅显示来源链与状态，不开放取消回写。',
  },
  {
    key: 'payable-draft',
    label: '应付草稿',
    reason: '只读切片仅核对应付状态，不开放真实应付草稿生成。',
  },
  {
    key: 'export-download',
    label: '导出 / 下载',
    reason: '导出、下载与真实打印提交流程保持只读阻断。',
  },
  {
    key: 'worker-outbox',
    label: 'outbox / worker / ERPNext',
    reason: 'payable outbox、worker、ERPNext 与跨模块执行保持禁用。',
  },
] as const

export const FACTORY_STATEMENT_PAYABLE_GUARD_LABEL =
  'confirm/cancel/payable draft、导出下载、真实打印提交与 outbox/worker/ERPNext 动作保持只读阻断。'

export const FACTORY_STATEMENT_PAYABLE_WRITE_BOUNDARY =
  'confirm / cancel / payable-draft / export / download / print-submit disabled'

export const FACTORY_STATEMENT_PAYABLE_REMAINING_GAP =
  '未开放真实 confirm/cancel/payable draft、导出下载、ERPNext、outbox、worker。'
