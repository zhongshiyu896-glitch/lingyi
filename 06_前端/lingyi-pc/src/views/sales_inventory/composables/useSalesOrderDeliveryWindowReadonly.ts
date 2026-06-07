import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { SalesOrderDetailData, SalesOrderListItem } from '@/api/sales_inventory'
import {
  SALES_ORDER_DELIVERY_WINDOW_DISABLED_ACTIONS,
  SALES_ORDER_DELIVERY_WINDOW_FIELDS,
  SALES_ORDER_DELIVERY_WINDOW_FOCUS_LABEL,
  SALES_ORDER_DELIVERY_WINDOW_PARITY_LABEL,
  SALES_ORDER_DELIVERY_WINDOW_READONLY_GUARD_REASON,
  SALES_ORDER_DELIVERY_WINDOW_REMAINING_GAP,
  SALES_ORDER_DELIVERY_WINDOW_WRITE_BOUNDARY,
  type SalesOrderDeliveryWindowFieldKey,
  type SalesOrderDeliveryWindowTagType,
} from '@/views/sales_inventory/constants/salesOrderDeliveryWindowFields'

const FALLBACK_TEXT = '-'

export interface SalesOrderDeliveryWindowReadonlyCard {
  key: SalesOrderDeliveryWindowFieldKey
  label: string
  value: string
}

export interface SalesOrderDeliveryWindowReadonlyAction {
  label: string
  reason: string
}

export interface SalesOrderDeliveryWindowReadonlySummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesOrderDeliveryWindowTagType
  focusLabel: string
  focusTone: SalesOrderDeliveryWindowTagType
  deliveryStatusLabel: string
  deliveryStatusTone: SalesOrderDeliveryWindowTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesOrderDeliveryWindowTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: SalesOrderDeliveryWindowReadonlyCard[]
  disabledActions: SalesOrderDeliveryWindowReadonlyAction[]
}

interface UseSalesOrderDeliveryWindowReadonlyOptions {
  rows?: MaybeRef<SalesOrderListItem[]>
  detail?: MaybeRef<SalesOrderDetailData | null>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  lastLoadedAt?: MaybeRef<string | null | undefined>
  lastError?: MaybeRef<string | null | undefined>
}

const normalizeText = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumber = (value: unknown): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const todayStamp = (): number => {
  const now = new Date()
  now.setHours(0, 0, 0, 0)
  return now.getTime()
}

const toDateStamp = (value: unknown): number | null => {
  const normalized = normalizeText(value)
  if (!normalized) return null
  const stamp = new Date(normalized).getTime()
  return Number.isFinite(stamp) ? stamp : null
}

export const useSalesOrderDeliveryWindowReadonly = ({
  rows,
  detail,
  tab,
  parity,
  focus,
  lastLoadedAt,
  lastError,
}: UseSalesOrderDeliveryWindowReadonlyOptions): {
  deliveryWindowReadonlySummary: ComputedRef<SalesOrderDeliveryWindowReadonlySummary>
} => {
  const deliveryWindowReadonlySummary = computed<SalesOrderDeliveryWindowReadonlySummary>(() => {
    const rowList = unref(rows) || []
    const currentDetail = unref(detail) || null
    const tabValue = normalizeText(unref(tab)) || 'delivery-window-readonly'
    const parityValue = normalizeText(unref(parity)) || 'sales-order'
    const focusValue = normalizeText(unref(focus)) || 'delivery-source'
    const loadedAt = normalizeText(unref(lastLoadedAt)) || FALLBACK_TEXT
    const errorMessage = normalizeText(unref(lastError))
    const currentToday = todayStamp()

    let recordCount = 0
    let pendingCount = 0
    let overdueCount = 0
    let sourceScopeLabel = FALLBACK_TEXT
    let coverageLabel = '交付窗口待真实校验'
    let itemStatusLabel = '无可读交付明细'

    if (currentDetail) {
      recordCount = currentDetail.items.length
      currentDetail.items.forEach((item) => {
        const qty = toNumber(item.qty)
        const deliveredQty = Math.min(toNumber(item.delivered_qty), qty)
        const remainingQty = Math.max(qty - deliveredQty, 0)
        if (remainingQty > 0) {
          pendingCount += 1
          const deliveryStamp = toDateStamp(item.delivery_date || currentDetail.delivery_date)
          if (deliveryStamp !== null && deliveryStamp < currentToday) {
            overdueCount += 1
          }
        }
      })
      sourceScopeLabel = currentDetail.name || FALLBACK_TEXT
      coverageLabel = currentDetail.items.length > 0 ? '交付窗口摘要已回读' : '交付窗口待真实校验'
      itemStatusLabel =
        currentDetail.items.length > 0
          ? `${currentDetail.items.length} 条明细 / 待交 ${pendingCount} / 逾期 ${overdueCount}`
          : '暂无销售订单明细'
    } else if (rowList.length > 0) {
      recordCount = rowList.length
      rowList.forEach((row) => {
        const status = normalizeText(row.status).toLowerCase()
        const isClosed = status === 'completed' || status === 'cancelled'
        if (!isClosed) {
          pendingCount += 1
          const deliveryStamp = toDateStamp(row.delivery_date)
          if (deliveryStamp !== null && deliveryStamp < currentToday) {
            overdueCount += 1
          }
        }
      })
      sourceScopeLabel = rowList.length === 1 ? rowList[0]?.name || FALLBACK_TEXT : `${rowList.length} orders`
      coverageLabel = '销售订单交付窗口已回读'
      itemStatusLabel = `${rowList.length} 条订单 / 待交 ${pendingCount} / 逾期 ${overdueCount}`
    }

    const cardValues: Record<SalesOrderDeliveryWindowFieldKey, string> = {
      recordCountLabel: String(recordCount),
      deliveryPendingLabel: String(pendingCount),
      overdueCountLabel: String(overdueCount),
      sourceScopeLabel,
      coverageLabel,
      refreshLabel: loadedAt,
    }
    const cards: SalesOrderDeliveryWindowReadonlyCard[] = SALES_ORDER_DELIVERY_WINDOW_FIELDS.map((field) => ({
      key: field.key,
      label: field.label,
      value: cardValues[field.key] || FALLBACK_TEXT,
    }))

    return {
      queryStateLabel: `${tabValue} | parity=${parityValue} | focus=${focusValue}`,
      parityLabel: SALES_ORDER_DELIVERY_WINDOW_PARITY_LABEL,
      parityTone: parityValue === 'sales-order' ? 'success' : 'warning',
      focusLabel: SALES_ORDER_DELIVERY_WINDOW_FOCUS_LABEL,
      focusTone: focusValue === 'delivery-source' ? 'warning' : 'info',
      deliveryStatusLabel:
        recordCount > 0
          ? pendingCount > 0
            ? overdueCount > 0
              ? 'delivery window overdue'
              : 'delivery window pending'
            : 'delivery window aligned'
          : 'delivery window fallback',
      deliveryStatusTone:
        recordCount > 0 ? (overdueCount > 0 ? 'danger' : pendingCount > 0 ? 'warning' : 'success') : 'info',
      sourceStatusLabel: recordCount > 0 ? 'delivery-source readback ready' : 'delivery-source pending',
      sourceStatusTone: recordCount > 0 ? 'success' : 'info',
      itemStatusLabel,
      blockedReason:
        errorMessage ||
        '当前切片仅开放交付窗口只读核对，真实发运确认、导出、库存写入与跨模块执行保持阻断。',
      readonlyGuardReason: SALES_ORDER_DELIVERY_WINDOW_READONLY_GUARD_REASON,
      remainingGap: SALES_ORDER_DELIVERY_WINDOW_REMAINING_GAP,
      writeBoundary: SALES_ORDER_DELIVERY_WINDOW_WRITE_BOUNDARY,
      cards,
      disabledActions: SALES_ORDER_DELIVERY_WINDOW_DISABLED_ACTIONS.map((action) => ({
        label: action.label,
        reason: action.reason,
      })),
    }
  })

  return {
    deliveryWindowReadonlySummary,
  }
}

export type { SalesOrderDeliveryWindowFieldKey }
export { SALES_ORDER_DELIVERY_WINDOW_FIELDS }
