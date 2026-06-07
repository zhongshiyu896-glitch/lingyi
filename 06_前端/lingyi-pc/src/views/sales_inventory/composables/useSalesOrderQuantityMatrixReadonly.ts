import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { SalesOrderDetailData, SalesOrderListItem } from '@/api/sales_inventory'
import {
  buildSalesOrderQuantityMatrixReadonlySummary,
  resolveSalesOrderReadonlyGroup,
  type SalesOrderQuantityMatrixReadonlySummary,
} from '@/api/sales_inventory_sales_orders'
import {
  SALES_ORDER_MATRIX_PROGRESS_LABELS,
  SALES_ORDER_QUANTITY_MATRIX_DISABLED_ACTIONS,
  SALES_ORDER_QUANTITY_MATRIX_FOCUS_LABEL,
  SALES_ORDER_QUANTITY_MATRIX_PARITY_LABEL,
  SALES_ORDER_QUANTITY_MATRIX_READONLY_GUARD_REASON,
  SALES_ORDER_QUANTITY_MATRIX_REMAINING_GAP,
  SALES_ORDER_QUANTITY_MATRIX_STATE_LABELS,
  SALES_ORDER_QUANTITY_MATRIX_STATE_TAGS,
  SALES_ORDER_QUANTITY_MATRIX_SUMMARY_FIELDS,
  SALES_ORDER_QUANTITY_MATRIX_WRITE_BOUNDARY,
  type SalesOrderMatrixProgressState,
  type SalesOrderQuantityMatrixReadonlyState,
  type SalesOrderQuantityMatrixReadonlyTagType,
  type SalesOrderQuantityMatrixSummaryFieldKey,
} from '@/views/sales_inventory/constants/salesOrderMatrixFields'

export interface SalesOrderQuantityMatrixReadonlyCard {
  key: SalesOrderQuantityMatrixSummaryFieldKey
  label: string
  value: string
}

export interface SalesOrderQuantityMatrixReadonlyAction {
  key: string
  label: string
  reason: string
}

export interface SalesOrderQuantityMatrixReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface SalesOrderQuantityMatrixReadonlyViewSummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesOrderQuantityMatrixReadonlyTagType
  focusLabel: string
  focusTone: SalesOrderQuantityMatrixReadonlyTagType
  stateLabel: string
  stateTone: SalesOrderQuantityMatrixReadonlyTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesOrderQuantityMatrixReadonlyTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: SalesOrderQuantityMatrixReadonlyCard[]
  disabledActions: SalesOrderQuantityMatrixReadonlyAction[]
  items: SalesOrderQuantityMatrixReadonlyItem[]
}

interface UseSalesOrderQuantityMatrixReadonlyOptions {
  mode: MaybeRef<'list' | 'detail'>
  currentPath: MaybeRef<string>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  rows?: MaybeRef<SalesOrderListItem[]>
  detail?: MaybeRef<SalesOrderDetailData | null>
  lastLoadedAt: MaybeRef<string>
  lastError: MaybeRef<string>
}

const FALLBACK_TEXT = '-'

const normalizeText = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const formatNumber = (value?: string | number | null): string => {
  if (value === null || value === undefined || value === '') return '0'
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return String(value)
  return numeric.toLocaleString('zh-CN', {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  })
}

const progressLabel = (state: SalesOrderMatrixProgressState): string =>
  SALES_ORDER_MATRIX_PROGRESS_LABELS[state]

const todayStamp = (): number => {
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return now.getTime()
}

const isPastDue = (value?: string | null): boolean => {
  const normalized = normalizeText(value)
  if (!normalized) return false
  const stamp = new Date(normalized).getTime()
  return Number.isFinite(stamp) && stamp < todayStamp()
}

const groupLabel = (group: ReturnType<typeof resolveSalesOrderReadonlyGroup>): string => {
  switch (group) {
    case 'draft-watch':
      return '草稿跟进'
    case 'delivery-followup':
      return '交付跟进'
    case 'closed':
      return '关闭订单'
    default:
      return '未标记'
  }
}

const buildListItems = (
  rows: SalesOrderListItem[],
  blockedReason: string,
): SalesOrderQuantityMatrixReadonlyItem[] => {
  if (rows.length === 0) {
    return [
      {
        subjectLabel: 'sales-order / quantity-matrix fallback',
        statusLabel: 'guarded / waiting',
        sourceLabel: 'quantity-source / parity mirror',
        blockedReason,
      },
    ]
  }

  return rows.slice(0, 6).map((row) => {
    const group = resolveSalesOrderReadonlyGroup(row)
    const rowBlockedReason =
      group === 'closed'
        ? '订单已关闭或完成，当前仅保留只读数量矩阵核对，不开放交付、导出或库存写入。'
        : isPastDue(row.delivery_date)
          ? '当前订单存在待交付窗口，仅保留 quantity-matrix 只读核对与 blocked reason。'
          : blockedReason

    return {
      subjectLabel: `${row.name || FALLBACK_TEXT} / ${row.customer || '未绑定客户'}`,
      statusLabel: `${normalizeText(row.status) || '未标记'} / ${groupLabel(group)}`,
      sourceLabel: `${row.company || FALLBACK_TEXT} / 交期 ${normalizeText(row.delivery_date) || FALLBACK_TEXT}`,
      blockedReason: rowBlockedReason,
    }
  })
}

const buildDetailItems = (
  matrixSummary: SalesOrderQuantityMatrixReadonlySummary,
  blockedReason: string,
): SalesOrderQuantityMatrixReadonlyItem[] => {
  if (matrixSummary.rows.length === 0) {
    return [
      {
        subjectLabel: 'quantity-matrix / detail fallback',
        statusLabel: 'guarded / waiting',
        sourceLabel: 'quantity-source / parity mirror',
        blockedReason,
      },
    ]
  }

  return matrixSummary.rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.styleKey} / ${row.color} / ${row.size}`,
    statusLabel: `${progressLabel(row.progressState)} / 完成率 ${row.completionRateLabel}`,
    sourceLabel: `${row.sourceItemsLabel || FALLBACK_TEXT} / 交期 ${row.deliveryDateLabel || FALLBACK_TEXT}`,
    blockedReason:
      row.remainingQty > 0
        ? row.progressState === 'delayed'
          ? '存在延期待交付格，仅开放 quantity-matrix 只读核对，不开放 delivery/export/stock-write。'
          : '仍有未交数量，仅保留 quantity-source 只读核对与 blocked reason。'
        : blockedReason,
  }))
}

const buildBlockedReason = ({
  mode,
  currentRows,
  detail,
  lastError,
}: {
  mode: 'list' | 'detail'
  currentRows: SalesOrderListItem[]
  detail: SalesOrderDetailData | null
  lastError: string
}): string => {
  if (lastError) {
    return `当前回读异常：${lastError}。quantity-matrix 只读区保留 fallback 壳层，不开放 delivery/export/stock-write。`
  }
  if (mode === 'detail' && !detail) {
    return '当前详情未命中可读销售订单，quantity-matrix 只读区保留 fallback 壳层，不开放 delivery/export/stock-write。'
  }
  if (currentRows.length === 0 && !detail) {
    return '当前筛选未命中销售订单，quantity-matrix 仅保留只读 query/parity/focus 壳层。'
  }
  return '当前仅开放 sales-order quantity-matrix 只读核对，不开放真实交付、导出、库存写入、outbox、worker 或 ERPNext 写链路。'
}

export const useSalesOrderQuantityMatrixReadonly = ({
  mode,
  currentPath,
  tab,
  parity,
  focus,
  rows,
  detail,
  lastLoadedAt,
  lastError,
}: UseSalesOrderQuantityMatrixReadonlyOptions): {
  salesOrderQuantityMatrixReadonlySummary: ComputedRef<SalesOrderQuantityMatrixReadonlyViewSummary>
} => {
  const salesOrderQuantityMatrixReadonlySummary =
    computed<SalesOrderQuantityMatrixReadonlyViewSummary>(() => {
      const modeValue = unref(mode)
      const currentPathValue = normalizeText(unref(currentPath)) || '/sales-inventory/sales-orders'
      const tabValue = normalizeText(unref(tab)) || 'quantity-matrix-readonly'
      const parityValue = normalizeText(unref(parity)) || 'sales-order'
      const focusValue = normalizeText(unref(focus)) || 'quantity-source'
      const lastLoadedAtValue = normalizeText(unref(lastLoadedAt)) || 'pending'
      const lastErrorValue = normalizeText(unref(lastError))
      const currentRows = unref(rows) || []
      const currentDetail = unref(detail) || null
      const matrixSummary = currentDetail
        ? buildSalesOrderQuantityMatrixReadonlySummary(currentDetail)
        : null

      const delayedCount =
        matrixSummary?.delayedLineCount ??
        currentRows.filter((row) => {
          const group = resolveSalesOrderReadonlyGroup(row)
          return group !== 'closed' && isPastDue(row.delivery_date)
        }).length
      const completedCount =
        matrixSummary?.completedLineCount ??
        currentRows.filter((row) => resolveSalesOrderReadonlyGroup(row) === 'closed').length
      const entryCount = matrixSummary?.rows.length ?? currentRows.length
      const remainingLabel = matrixSummary
        ? `${formatNumber(matrixSummary.totalRemainingQty)} 待交`
        : `${currentRows.filter((row) => resolveSalesOrderReadonlyGroup(row) !== 'closed').length} 单待交`
      const blockedReason = buildBlockedReason({
        mode: modeValue,
        currentRows,
        detail: currentDetail,
        lastError: lastErrorValue,
      })

      let state: SalesOrderQuantityMatrixReadonlyState = 'ready-readonly'
      if (lastErrorValue) {
        state = 'error-guarded'
      } else if (modeValue === 'detail' && !currentDetail) {
        state = 'detail-fallback'
      } else if (entryCount === 0) {
        state = 'query-guarded'
      }

      let sourceStatusLabel = 'quantity-source guarded / no rows'
      let sourceStatusTone: SalesOrderQuantityMatrixReadonlyTagType = 'warning'
      if (state === 'error-guarded') {
        sourceStatusLabel = 'quantity-source error guarded'
        sourceStatusTone = 'danger'
      } else if (modeValue === 'detail' && currentDetail && matrixSummary) {
        sourceStatusLabel = `quantity-source detail rows / ${matrixSummary.rows.length}`
        sourceStatusTone = matrixSummary.rows.length > 0 ? 'success' : 'warning'
      } else if (currentRows.length > 0) {
        sourceStatusLabel = `quantity-source list rows / ${currentRows.length}`
        sourceStatusTone = 'success'
      }

      const items =
        modeValue === 'detail' && matrixSummary
          ? buildDetailItems(matrixSummary, blockedReason)
          : buildListItems(currentRows, blockedReason)

      const cardValues: Record<SalesOrderQuantityMatrixSummaryFieldKey, string> = {
        entryCountLabel: String(entryCount),
        delayedEntryCountLabel: String(delayedCount),
        completedEntryCountLabel: String(completedCount),
        remainingScopeLabel: remainingLabel,
        sourceStatusCardLabel: sourceStatusLabel,
        modeCardLabel:
          modeValue === 'detail' && matrixSummary
            ? `detail / ${matrixSummary.matrixCompletionRateLabel}`
            : currentRows.length > 0
              ? 'list / readonly summary'
              : 'fallback / guarded',
      }

      return {
        queryStateLabel: `tab=${tabValue}; route=${currentPathValue}; loaded=${lastLoadedAtValue}; mode=${modeValue}`,
        parityLabel:
          parityValue === 'sales-order'
            ? SALES_ORDER_QUANTITY_MATRIX_PARITY_LABEL
            : `${parityValue || 'sales-order'} / fallback`,
        parityTone: parityValue === 'sales-order' ? 'success' : 'warning',
        focusLabel:
          focusValue === 'quantity-source'
            ? SALES_ORDER_QUANTITY_MATRIX_FOCUS_LABEL
            : `${focusValue || 'quantity-source'} / fallback`,
        focusTone: focusValue === 'quantity-source' ? 'success' : 'warning',
        stateLabel: SALES_ORDER_QUANTITY_MATRIX_STATE_LABELS[state],
        stateTone: SALES_ORDER_QUANTITY_MATRIX_STATE_TAGS[state],
        sourceStatusLabel,
        sourceStatusTone,
        itemStatusLabel: `${items.length} rows / delayed ${delayedCount} / completed ${completedCount}`,
        blockedReason,
        readonlyGuardReason: SALES_ORDER_QUANTITY_MATRIX_READONLY_GUARD_REASON,
        remainingGap: SALES_ORDER_QUANTITY_MATRIX_REMAINING_GAP,
        writeBoundary: SALES_ORDER_QUANTITY_MATRIX_WRITE_BOUNDARY,
        cards: SALES_ORDER_QUANTITY_MATRIX_SUMMARY_FIELDS.map((field) => ({
          key: field.key,
          label: field.label,
          value: cardValues[field.key],
        })),
        disabledActions: SALES_ORDER_QUANTITY_MATRIX_DISABLED_ACTIONS.map((action) => ({
          key: action.key,
          label: action.label,
          reason: action.reason,
        })),
        items,
      }
    })

  return {
    salesOrderQuantityMatrixReadonlySummary,
  }
}
