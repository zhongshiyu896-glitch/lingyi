export type SalesOrderMatrixProgressState = 'not-started' | 'in-progress' | 'delayed' | 'completed'
export type SalesOrderQuantityMatrixReadonlyTagType =
  | 'info'
  | 'primary'
  | 'warning'
  | 'success'
  | 'danger'

export type SalesOrderQuantityMatrixReadonlyState =
  | 'ready-readonly'
  | 'query-guarded'
  | 'detail-fallback'
  | 'error-guarded'

export type SalesOrderQuantityMatrixSummaryFieldKey =
  | 'entryCountLabel'
  | 'delayedEntryCountLabel'
  | 'completedEntryCountLabel'
  | 'remainingScopeLabel'
  | 'sourceStatusCardLabel'
  | 'modeCardLabel'

export interface SalesOrderMatrixSplitResult {
  styleKey: string
  color: string
  size: string
}

export const SALES_ORDER_MATRIX_PROGRESS_LABELS: Record<SalesOrderMatrixProgressState, string> = {
  'not-started': '未启动交付',
  'in-progress': '交付中',
  delayed: '延期待交付',
  completed: '已完成交付',
}

export const SALES_ORDER_MATRIX_PROGRESS_TAGS: Record<
  SalesOrderMatrixProgressState,
  'info' | 'primary' | 'warning' | 'success' | 'danger'
> = {
  'not-started': 'info',
  'in-progress': 'primary',
  delayed: 'danger',
  completed: 'success',
}

export const SALES_ORDER_MATRIX_SUMMARY_FIELDS = [
  { key: 'matrixCellCount', label: '矩阵格数' },
  { key: 'colorCount', label: '颜色数' },
  { key: 'sizeCount', label: '尺码数' },
  { key: 'delayedLineCount', label: '延期格数' },
  { key: 'completedLineCount', label: '完成格数' },
  { key: 'matrixCompletionRateLabel', label: '整体完成率' },
] as const

export const SALES_ORDER_QUANTITY_MATRIX_SUMMARY_FIELDS = [
  { key: 'entryCountLabel', label: '只读条目' },
  { key: 'delayedEntryCountLabel', label: '延期条目' },
  { key: 'completedEntryCountLabel', label: '已完成条目' },
  { key: 'remainingScopeLabel', label: '待交范围' },
  { key: 'sourceStatusCardLabel', label: '来源状态' },
  { key: 'modeCardLabel', label: '只读模式' },
] as const satisfies ReadonlyArray<{
  key: SalesOrderQuantityMatrixSummaryFieldKey
  label: string
}>

export const SALES_ORDER_QUANTITY_MATRIX_STATE_LABELS: Record<
  SalesOrderQuantityMatrixReadonlyState,
  string
> = {
  'ready-readonly': 'quantity-matrix 只读可核对',
  'query-guarded': 'quantity-matrix 查询守卫',
  'detail-fallback': 'quantity-matrix 详情回退',
  'error-guarded': 'quantity-matrix 错误守卫',
}

export const SALES_ORDER_QUANTITY_MATRIX_STATE_TAGS: Record<
  SalesOrderQuantityMatrixReadonlyState,
  SalesOrderQuantityMatrixReadonlyTagType
> = {
  'ready-readonly': 'success',
  'query-guarded': 'warning',
  'detail-fallback': 'info',
  'error-guarded': 'danger',
}

export const SALES_ORDER_QUANTITY_MATRIX_PARITY_LABEL = 'sales-order parity / readonly'
export const SALES_ORDER_QUANTITY_MATRIX_FOCUS_LABEL = 'quantity-source focus / readonly'
export const SALES_ORDER_QUANTITY_MATRIX_READONLY_GUARD_REASON =
  '当前仅开放 sales-order quantity-matrix 只读核对；delivery / export / stock-write / outbox / worker / ERPNext / production write 均保持 disabled。'
export const SALES_ORDER_QUANTITY_MATRIX_REMAINING_GAP =
  '如需真实 delivery、export、stock-write、outbox、worker、ERPNext 或 production write，需进入后续非只读任务；当前切片仅保留数量矩阵核对。'
export const SALES_ORDER_QUANTITY_MATRIX_WRITE_BOUNDARY =
  'GET-only / delivery-export-stock-write-outbox-worker-ERPNext-production-write disabled'

export const SALES_ORDER_QUANTITY_MATRIX_DISABLED_ACTIONS = [
  { key: 'delivery', label: '交付', reason: 'delivery write disabled' },
  { key: 'export', label: '导出', reason: 'export disabled' },
  { key: 'stock-write', label: '库存写入', reason: 'stock-write disabled' },
  { key: 'outbox-worker', label: 'Outbox / Worker', reason: 'outbox / worker disabled' },
  { key: 'erpnext', label: 'ERPNext', reason: 'ERPNext bridge disabled' },
  { key: 'production-write', label: 'Production Write', reason: 'production write disabled' },
] as const

const FALLBACK_COLOR = '通用色'
const FALLBACK_SIZE = '均码'

export const splitSalesOrderMatrixStyle = (
  itemCode?: string | null,
  itemName?: string | null,
): SalesOrderMatrixSplitResult => {
  const normalizedCode = itemCode?.trim() || ''
  const codeParts = normalizedCode.split(/[-_/]/).filter(Boolean)
  if (codeParts.length >= 3) {
    return {
      styleKey: codeParts.slice(0, -2).join('-') || normalizedCode,
      color: codeParts[codeParts.length - 2],
      size: codeParts[codeParts.length - 1],
    }
  }

  const normalizedName = itemName?.trim() || ''
  const nameParts = normalizedName.split(/[\s/]/).filter(Boolean)
  if (nameParts.length >= 2) {
    return {
      styleKey: normalizedCode || normalizedName || '-',
      color: nameParts[nameParts.length - 2],
      size: nameParts[nameParts.length - 1],
    }
  }

  return {
    styleKey: normalizedCode || normalizedName || '-',
    color: FALLBACK_COLOR,
    size: FALLBACK_SIZE,
  }
}
