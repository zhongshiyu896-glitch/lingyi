import type { SalesOrderDetailData, SalesOrderListItem } from '@/api/sales_inventory'
import {
  buildSalesOrderDetailReadonlySummary,
  buildSalesOrderQuantityMatrixReadonlySummary,
  resolveSalesOrderReadonlyGroup,
  type SalesOrderQuantityMatrixReadonlySummary,
  type SalesOrderReadonlyGroup,
} from '@/api/sales_inventory_sales_orders'
import {
  SALES_ORDER_MATRIX_PROGRESS_LABELS,
  SALES_ORDER_MATRIX_PROGRESS_TAGS,
  type SalesOrderMatrixProgressState,
} from '@/views/sales_inventory/constants/salesOrderMatrixFields'

export type SalesOrderStatusTagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'
export type SalesOrderGroupTagType = 'primary' | 'warning' | 'success'
export type SalesOrderMatrixTagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

export interface SalesOrderReadonlyGuardAction {
  label: string
  reason: string
}

const STATUS_LABELS: Record<string, string> = {
  Draft: '草稿待核对',
  'To Bill': '待开票',
  'To Deliver': '待交付',
  'To Deliver and Bill': '待交付并开票',
  Completed: '已完成',
  Cancelled: '已取消',
}

const STATUS_TYPES: Record<string, SalesOrderStatusTagType> = {
  Draft: 'warning',
  'To Bill': 'warning',
  'To Deliver': 'primary',
  'To Deliver and Bill': 'success',
  Completed: 'success',
  Cancelled: 'info',
}

const GROUP_LABELS: Record<SalesOrderReadonlyGroup, string> = {
  'draft-watch': '草稿跟进',
  'delivery-followup': '交付跟进',
  closed: '关闭订单',
}

const GROUP_TYPES: Record<SalesOrderReadonlyGroup, SalesOrderGroupTagType> = {
  'draft-watch': 'warning',
  'delivery-followup': 'primary',
  closed: 'success',
}

const READONLY_GUARD_ACTIONS: SalesOrderReadonlyGuardAction[] = [
  { label: '新建草稿', reason: 'sales write 冻结' },
  { label: '取消草稿', reason: 'readonly guard' },
  { label: '导出单据', reason: 'export 冻结' },
  { label: '库存影响', reason: 'inventory impact 冻结' },
]

const normalizeString = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumberLabel = (value?: string | number | null, digits = 0): string => {
  if (value === null || value === undefined || value === '') return '-'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return String(value)
  return numeric.toLocaleString('zh-CN', {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits === 0 ? 2 : digits,
  })
}

export const useSalesOrderReadback = () => {
  const parseQueryString = (value: unknown): string => normalizeString(value)

  const statusLabel = (status?: string | null): string => {
    const raw = normalizeString(status)
    return STATUS_LABELS[raw] || raw || '未标记'
  }

  const statusType = (status?: string | null): SalesOrderStatusTagType => {
    const raw = normalizeString(status)
    return STATUS_TYPES[raw] || 'info'
  }

  const followupGroupFromRow = (row: Pick<SalesOrderListItem, 'status' | 'docstatus'>): SalesOrderReadonlyGroup =>
    resolveSalesOrderReadonlyGroup(row)

  const followupGroupLabel = (group: SalesOrderReadonlyGroup): string => GROUP_LABELS[group]

  const followupGroupType = (group: SalesOrderReadonlyGroup): SalesOrderGroupTagType => GROUP_TYPES[group]

  const customerLabel = (customer?: string | null): string => normalizeString(customer) || '未绑定客户'

  const detailSummary = (detail: SalesOrderDetailData) => buildSalesOrderDetailReadonlySummary(detail)

  const quantityMatrixSummary = (detail: SalesOrderDetailData): SalesOrderQuantityMatrixReadonlySummary =>
    buildSalesOrderQuantityMatrixReadonlySummary(detail)

  const matrixProgressLabel = (state: SalesOrderMatrixProgressState): string =>
    SALES_ORDER_MATRIX_PROGRESS_LABELS[state]

  const matrixProgressType = (state: SalesOrderMatrixProgressState): SalesOrderMatrixTagType =>
    SALES_ORDER_MATRIX_PROGRESS_TAGS[state]

  return {
    customerLabel,
    detailSummary,
    followupGroupFromRow,
    followupGroupLabel,
    followupGroupType,
    formatNumber: toNumberLabel,
    matrixProgressLabel,
    matrixProgressType,
    parseQueryString,
    quantityMatrixSummary,
    readonlyGuardActions: READONLY_GUARD_ACTIONS,
    statusLabel,
    statusType,
  }
}
