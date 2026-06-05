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

export const FACTORY_STATEMENT_PAYABLE_GUARD_LABEL =
  '结算写入、应付出账、导出、真实打印提交与 worker/outbox 动作保持只读阻断。'

export const FACTORY_STATEMENT_PAYABLE_WRITE_BOUNDARY = 'settlement / payable / export / print-submit disabled'

export const FACTORY_STATEMENT_PAYABLE_REMAINING_GAP =
  '未开放真实结算写入、应付出账、导出、ERPNext、outbox、worker。'
