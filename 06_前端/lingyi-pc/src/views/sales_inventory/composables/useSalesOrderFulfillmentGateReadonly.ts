import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { SalesOrderDetailData, SalesOrderListItem } from '@/api/sales_inventory'
import { useSalesOrderReadback } from '@/views/sales_inventory/composables/useSalesOrderReadback'
import {
  SALES_ORDER_FULFILLMENT_GATE_DISABLED_ACTIONS,
  SALES_ORDER_FULFILLMENT_GATE_FOCUS_LABEL,
  SALES_ORDER_FULFILLMENT_GATE_PARITY_LABEL,
  SALES_ORDER_FULFILLMENT_GATE_READONLY_GUARD_REASON,
  SALES_ORDER_FULFILLMENT_GATE_REMAINING_GAP,
  SALES_ORDER_FULFILLMENT_GATE_STATE_TAGS,
  SALES_ORDER_FULFILLMENT_GATE_SUMMARY_FIELDS,
  SALES_ORDER_FULFILLMENT_GATE_WRITE_BOUNDARY,
  type SalesOrderFulfillmentGateState,
  type SalesOrderFulfillmentGateTagType,
} from '@/views/sales_inventory/constants/salesOrderFulfillmentGateFields'

const FALLBACK_TEXT = '-'

type FulfillmentSummaryFieldKey =
  (typeof SALES_ORDER_FULFILLMENT_GATE_SUMMARY_FIELDS)[number]['key']

export interface SalesOrderFulfillmentGateReadonlyCard {
  key: FulfillmentSummaryFieldKey
  label: string
  value: string
}

export interface SalesOrderFulfillmentGateReadonlyAction {
  label: string
  reason: string
}

export interface SalesOrderFulfillmentGateReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface SalesOrderFulfillmentGateReadonlyViewSummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesOrderFulfillmentGateTagType
  focusLabel: string
  focusTone: SalesOrderFulfillmentGateTagType
  stateLabel: string
  stateTone: SalesOrderFulfillmentGateTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesOrderFulfillmentGateTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  blockingCount: number
  cards: SalesOrderFulfillmentGateReadonlyCard[]
  disabledActions: SalesOrderFulfillmentGateReadonlyAction[]
  items: SalesOrderFulfillmentGateReadonlyItem[]
}

interface UseSalesOrderFulfillmentGateReadonlyOptions {
  rows?: MaybeRef<SalesOrderListItem[]>
  detail?: MaybeRef<SalesOrderDetailData | null>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  lastLoadedAt?: MaybeRef<string | null | undefined>
  lastError?: MaybeRef<string | null | undefined>
}

interface SalesOrderFulfillmentGateBaseSummary {
  state: SalesOrderFulfillmentGateState
  stateLabel: string
  blockingCount: number
  sourceStatusLabel: string
  fulfillmentStateLabel: string
  deliveryWriteLabel: string
  inventoryWriteLabel: string
  blockedReasonLabel: string
  guardReason: string
}

const normalizeText = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumber = (value: unknown): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const resolveBlockedReason = (state: SalesOrderFulfillmentGateState): string => {
  if (state === 'closed-readonly') return '销售订单已关闭，仅保留只读归档核对，不开放下游履约写入。'
  if (state === 'delivery-pending') return '销售订单仍有未发运数量，delivery/export/stock-write/customer-supplier write 保持禁写。'
  if (state === 'ready-readonly') return '履约来源已可读，但仅开放守卫核对，不进入真实 delivery / stock-write / ERPNext 链路。'
  return '履约来源尚未完成回读校验，禁止进入 delivery/export/customer-supplier write/stock-write/outbox/worker。'
}

const resolveGuardReason = (state: SalesOrderFulfillmentGateState): string => {
  if (state === 'closed-readonly') {
    return '当前订单已进入关闭只读归档， fulfillment-gate 只允许核对，不允许恢复或触发任何写链路。'
  }
  if (state === 'ready-readonly') {
    return '履约来源已可读，但当前切片只保留 readonly guard；delivery write、customer-supplier write、stock-write、ERPNext 仍冻结。'
  }
  return SALES_ORDER_FULFILLMENT_GATE_READONLY_GUARD_REASON
}

const resolveListState = (rows: SalesOrderListItem[]): SalesOrderFulfillmentGateState => {
  if (rows.length === 0) return 'awaiting-fulfillment'
  const statuses = rows.map((row) => normalizeText(row.status))
  if (statuses.every((status) => status === 'Completed' || status === 'Cancelled')) {
    return 'closed-readonly'
  }
  if (statuses.some((status) => status === 'To Deliver' || status === 'To Deliver and Bill')) {
    return 'delivery-pending'
  }
  return 'ready-readonly'
}

const buildListBaseSummary = (rows: SalesOrderListItem[]): SalesOrderFulfillmentGateBaseSummary => {
  const state = resolveListState(rows)
  const companyCount = new Set(rows.map((row) => normalizeText(row.company)).filter(Boolean)).size
  const customerCount = new Set(rows.map((row) => normalizeText(row.customer)).filter(Boolean)).size
  const sourceStatusLabel =
    rows.length > 0
      ? `${rows.length} orders / ${customerCount || 0} customers / ${companyCount || 0} companies`
      : 'fulfillment-source pending'
  const fulfillmentStateLabel =
    state === 'closed-readonly'
      ? 'closed source readonly'
      : state === 'delivery-pending'
        ? 'delivery follow-up pending'
        : state === 'ready-readonly'
          ? 'fulfillment-source readable'
          : 'awaiting fulfillment source'
  const blockingCount =
    state === 'closed-readonly' ? 1 : state === 'delivery-pending' ? rows.length || 1 : rows.length > 0 ? 1 : 2
  return {
    state,
    stateLabel:
      state === 'closed-readonly'
        ? '关闭订单只读归档'
        : state === 'delivery-pending'
          ? '发运待履约核对'
          : state === 'ready-readonly'
            ? '履约来源可读'
            : '待进入履约校验',
    blockingCount,
    sourceStatusLabel,
    fulfillmentStateLabel,
    deliveryWriteLabel: 'delivery write disabled',
    inventoryWriteLabel: 'stock-write disabled',
    blockedReasonLabel: resolveBlockedReason(state),
    guardReason: resolveGuardReason(state),
  }
}

const buildDetailBaseSummary = (detail: SalesOrderDetailData): SalesOrderFulfillmentGateBaseSummary => {
  const orderedQty = detail.items.reduce((sum, item) => sum + toNumber(item.qty), 0)
  const deliveredQty = detail.items.reduce((sum, item) => sum + toNumber(item.delivered_qty), 0)
  const remainingQty = Math.max(orderedQty - deliveredQty, 0)
  const state: SalesOrderFulfillmentGateState =
    normalizeText(detail.status) === 'Completed' || normalizeText(detail.status) === 'Cancelled'
      ? 'closed-readonly'
      : remainingQty > 0
        ? 'delivery-pending'
        : detail.items.length > 0
          ? 'ready-readonly'
          : 'awaiting-fulfillment'
  return {
    state,
    stateLabel:
      state === 'closed-readonly'
        ? '关闭订单只读归档'
        : state === 'delivery-pending'
          ? '发运待履约核对'
          : state === 'ready-readonly'
            ? '履约来源可读'
            : '待进入履约校验',
    blockingCount: state === 'delivery-pending' ? detail.items.length || 1 : state === 'closed-readonly' ? 1 : 1,
    sourceStatusLabel: `${detail.items.length} items / ${detail.customer || FALLBACK_TEXT}`,
    fulfillmentStateLabel:
      state === 'delivery-pending'
        ? `${deliveredQty}/${orderedQty} delivered`
        : state === 'closed-readonly'
          ? 'closed source readonly'
          : 'fulfillment-source readable',
    deliveryWriteLabel: 'delivery write disabled',
    inventoryWriteLabel: 'stock-write disabled',
    blockedReasonLabel: resolveBlockedReason(state),
    guardReason: resolveGuardReason(state),
  }
}

const buildListItems = (
  rows: SalesOrderListItem[],
  blockedReason: string,
): SalesOrderFulfillmentGateReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.customer || FALLBACK_TEXT} / ${row.name}`,
    statusLabel: row.status || FALLBACK_TEXT,
    sourceLabel: `${row.company || FALLBACK_TEXT} / fulfillment-source`,
    blockedReason,
  }))

const buildDetailItems = (
  detail: SalesOrderDetailData,
  blockedReason: string,
): SalesOrderFulfillmentGateReadonlyItem[] =>
  detail.items.slice(0, 6).map((item) => {
    const orderedQty = toNumber(item.qty)
    const deliveredQty = Math.min(toNumber(item.delivered_qty), orderedQty)
    const remainingQty = Math.max(orderedQty - deliveredQty, 0)
    return {
      subjectLabel: `${detail.customer || FALLBACK_TEXT} / ${item.item_code || FALLBACK_TEXT}`,
      statusLabel:
        remainingQty > 0
          ? `${deliveredQty}/${orderedQty} delivered`
          : `${orderedQty}/${orderedQty} delivered`,
      sourceLabel: `${item.warehouse || FALLBACK_TEXT} / fulfillment-source`,
      blockedReason: remainingQty > 0 ? blockedReason : '仅开放只读核对',
    }
  })

export const useSalesOrderFulfillmentGateReadonly = ({
  rows,
  detail,
  tab,
  parity,
  focus,
  lastLoadedAt,
  lastError,
}: UseSalesOrderFulfillmentGateReadonlyOptions): {
  fulfillmentGateReadonlySummary: ComputedRef<SalesOrderFulfillmentGateReadonlyViewSummary>
} => {
  const { followupGroupFromRow, followupGroupLabel } = useSalesOrderReadback()

  const fulfillmentGateReadonlySummary = computed<SalesOrderFulfillmentGateReadonlyViewSummary>(() => {
    const rowList = unref(rows) || []
    const detailData = unref(detail) || null
    const tabValue = normalizeText(unref(tab)) || 'fulfillment-gate-readonly'
    const parityValue = normalizeText(unref(parity)) || 'sales-order'
    const focusValue = normalizeText(unref(focus)) || 'fulfillment-source'
    const loadedAt = normalizeText(unref(lastLoadedAt)) || FALLBACK_TEXT
    const errorMessage = normalizeText(unref(lastError))
    const baseSummary = detailData ? buildDetailBaseSummary(detailData) : buildListBaseSummary(rowList)
    const items = detailData
      ? buildDetailItems(detailData, baseSummary.blockedReasonLabel)
      : buildListItems(rowList, baseSummary.blockedReasonLabel)
    const itemStatusLabel = detailData
      ? `${detailData.items.length} 条明细 / 阻断 ${baseSummary.blockingCount} / ${detailData.customer || FALLBACK_TEXT}`
      : `${items.length} 条伙伴/条目 / 阻断 ${baseSummary.blockingCount} / ${
          rowList.length > 0 ? followupGroupLabel(followupGroupFromRow(rowList[0])) : FALLBACK_TEXT
        }`

    const cards: SalesOrderFulfillmentGateReadonlyCard[] =
      SALES_ORDER_FULFILLMENT_GATE_SUMMARY_FIELDS.map((field) => {
        const values: Record<FulfillmentSummaryFieldKey, string> = {
          sourceStatusLabel: baseSummary.sourceStatusLabel,
          fulfillmentStateLabel: baseSummary.fulfillmentStateLabel,
          deliveryWriteLabel: baseSummary.deliveryWriteLabel,
          inventoryWriteLabel: baseSummary.inventoryWriteLabel,
          blockingCount: String(baseSummary.blockingCount),
        }
        return {
          key: field.key,
          label: field.label,
          value: values[field.key] || FALLBACK_TEXT,
        }
      })

    return {
      queryStateLabel: `${tabValue} | parity=${parityValue} | focus=${focusValue} | loaded=${loadedAt}`,
      parityLabel: SALES_ORDER_FULFILLMENT_GATE_PARITY_LABEL,
      parityTone: parityValue === 'sales-order' ? 'success' : 'warning',
      focusLabel: SALES_ORDER_FULFILLMENT_GATE_FOCUS_LABEL,
      focusTone: focusValue === 'fulfillment-source' ? 'warning' : 'info',
      stateLabel: baseSummary.stateLabel,
      stateTone: SALES_ORDER_FULFILLMENT_GATE_STATE_TAGS[baseSummary.state],
      sourceStatusLabel: baseSummary.sourceStatusLabel,
      sourceStatusTone: items.length > 0 || rowList.length > 0 || Boolean(detailData) ? 'success' : 'info',
      itemStatusLabel,
      blockedReason: errorMessage || baseSummary.blockedReasonLabel,
      readonlyGuardReason: baseSummary.guardReason || SALES_ORDER_FULFILLMENT_GATE_READONLY_GUARD_REASON,
      remainingGap: SALES_ORDER_FULFILLMENT_GATE_REMAINING_GAP,
      writeBoundary: SALES_ORDER_FULFILLMENT_GATE_WRITE_BOUNDARY,
      blockingCount: baseSummary.blockingCount,
      cards,
      disabledActions: SALES_ORDER_FULFILLMENT_GATE_DISABLED_ACTIONS.map((action) => ({
        label: action.label,
        reason: action.reason,
      })),
      items,
    }
  })

  return {
    fulfillmentGateReadonlySummary,
  }
}
