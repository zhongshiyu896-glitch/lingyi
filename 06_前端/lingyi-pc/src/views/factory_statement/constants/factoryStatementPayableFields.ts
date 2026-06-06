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
    key: 'settlement-confirm',
    label: '结算确认',
    reason: 'payable-readonly 只回读结算镜像，不开放真实确认。',
  },
  {
    key: 'settlement-cancel',
    label: '结算取消',
    reason: 'settlement-source 仅显示来源链与状态，不开放取消回写。',
  },
  {
    key: 'export-download',
    label: '导出 / 下载',
    reason: '导出、下载与真实打印提交流程保持只读阻断。',
  },
  {
    key: 'worker-outbox',
    label: 'worker / outbox',
    reason: 'payable worker、outbox、ERPNext 与跨模块执行保持禁用。',
  },
  {
    key: 'refresh-permission',
    label: '刷新权限',
    reason: '当前加工厂对账详情处于 payable-readonly 边界，权限刷新入口仅保留只读提示，不执行真实刷新动作。',
  },
  {
    key: 'reload-module-actions',
    label: '重载模块动作',
    reason: '当前仅核对应付状态只读摘要，模块动作重载入口保持禁用，不执行真实重载。',
  },
] as const

export const FACTORY_STATEMENT_PAYABLE_GUARD_LABEL =
  '结算写入、应付出账、导出、真实打印提交与 worker/outbox 动作保持只读阻断。'

export const FACTORY_STATEMENT_PAYABLE_WRITE_BOUNDARY = 'settlement / payable / export / print-submit disabled'

export const FACTORY_STATEMENT_PAYABLE_REMAINING_GAP =
  '未开放真实结算写入、应付出账、导出、ERPNext、outbox、worker。'
