export type SalesOrderMatrixProgressState = 'not-started' | 'in-progress' | 'delayed' | 'completed'

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
