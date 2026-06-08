import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { SalesOrderDetailData, SalesOrderListItem } from '@/api/sales_inventory'
import type { SalesOrderDownstreamGuardReadonlySummary as SalesOrderDownstreamGuardBaseSummary } from '@/api/sales_inventory_sales_orders'
import {
  SALES_ORDER_DOWNSTREAM_GUARD_DISABLED_ACTIONS,
  SALES_ORDER_DOWNSTREAM_GUARD_FOCUS_LABEL,
  SALES_ORDER_DOWNSTREAM_GUARD_PARITY_LABEL,
  SALES_ORDER_DOWNSTREAM_GUARD_READONLY_GUARD_REASON,
  SALES_ORDER_DOWNSTREAM_GUARD_REMAINING_GAP,
  SALES_ORDER_DOWNSTREAM_GUARD_STATE_TAGS,
  SALES_ORDER_DOWNSTREAM_GUARD_SUMMARY_FIELDS,
  SALES_ORDER_DOWNSTREAM_GUARD_WRITE_BOUNDARY,
  type SalesOrderDownstreamGuardTagType,
} from '@/views/sales_inventory/constants/salesOrderDownstreamGuardFields'

const FALLBACK_TEXT = '-'

type DownstreamSummaryFieldKey =
  (typeof SALES_ORDER_DOWNSTREAM_GUARD_SUMMARY_FIELDS)[number]['key']

export interface SalesOrderDownstreamGuardReadonlyCard {
  key: DownstreamSummaryFieldKey
  label: string
  value: string
}

export interface SalesOrderDownstreamGuardReadonlyAction {
  label: string
  reason: string
}

export interface SalesOrderDownstreamGuardReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface SalesOrderDownstreamGuardReadonlyViewSummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesOrderDownstreamGuardTagType
  focusLabel: string
  focusTone: SalesOrderDownstreamGuardTagType
  stateLabel: string
  stateTone: SalesOrderDownstreamGuardTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesOrderDownstreamGuardTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: SalesOrderDownstreamGuardReadonlyCard[]
  disabledActions: SalesOrderDownstreamGuardReadonlyAction[]
  items: SalesOrderDownstreamGuardReadonlyItem[]
}

interface UseSalesOrderDownstreamGuardReadonlyOptions {
  baseSummary?: MaybeRef<SalesOrderDownstreamGuardBaseSummary | null>
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

const fallbackBaseSummary = (): SalesOrderDownstreamGuardBaseSummary => ({
  state: 'factory-pending',
  stateLabel: '缺失工厂履约映射',
  blockingCount: 1,
  sourceCompletenessLabel: '待补工厂映射',
  downstreamStateLabel: '下游联动阻断',
  productionGuardLabel: '生产联动 blocked',
  purchaseGuardLabel: '采购联动 blocked',
  blockingReasonLabel: '履约工厂映射缺失，禁止进入生产/采购联动，需先补齐工厂桥接。',
  guardReason:
    '履约工厂映射缺失，禁止进入生产/采购联动，需先补齐工厂桥接。 delivery / export / customer-supplier write / stock-write / ERPNext 均保持 readonly。',
  missingBridgeTags: ['工厂履约映射缺失'],
  readonlyGuardTags: ['生产联动 blocked', '采购联动 blocked', 'customer-supplier write disabled'],
  actions: [],
})

const buildListItems = (
  rows: SalesOrderListItem[],
  summary: SalesOrderDownstreamGuardBaseSummary,
): SalesOrderDownstreamGuardReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.customer || FALLBACK_TEXT} / ${row.name}`,
    statusLabel: row.status || FALLBACK_TEXT,
    sourceLabel: `${row.company || FALLBACK_TEXT} / downstream-source`,
    blockedReason: summary.blockingReasonLabel,
  }))

const buildDetailItems = (
  detail: SalesOrderDetailData,
  summary: SalesOrderDownstreamGuardBaseSummary,
): SalesOrderDownstreamGuardReadonlyItem[] =>
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
      sourceLabel: `${item.warehouse || FALLBACK_TEXT} / downstream-source`,
      blockedReason: remainingQty > 0 ? summary.blockingReasonLabel : '仅开放只读核对',
    }
  })

export const useSalesOrderDownstreamGuardReadonly = ({
  baseSummary,
  rows,
  detail,
  tab,
  parity,
  focus,
  lastLoadedAt,
  lastError,
}: UseSalesOrderDownstreamGuardReadonlyOptions): {
  downstreamGuardReadonlySummary: ComputedRef<SalesOrderDownstreamGuardReadonlyViewSummary>
} => {
  const downstreamGuardReadonlySummary = computed<SalesOrderDownstreamGuardReadonlyViewSummary>(() => {
    const summary = unref(baseSummary) || fallbackBaseSummary()
    const rowList = unref(rows) || []
    const detailData = unref(detail) || null
    const tabValue = normalizeText(unref(tab)) || 'downstream-guard-readonly'
    const parityValue = normalizeText(unref(parity)) || 'sales-order'
    const focusValue = normalizeText(unref(focus)) || 'downstream-source'
    const loadedAt = normalizeText(unref(lastLoadedAt)) || FALLBACK_TEXT
    const errorMessage = normalizeText(unref(lastError))

    const items = detailData ? buildDetailItems(detailData, summary) : buildListItems(rowList, summary)
    const sourceScopeLabel = detailData
      ? `${detailData.customer || FALLBACK_TEXT} / ${detailData.items[0]?.item_code || FALLBACK_TEXT}`
      : rowList.length === 1
        ? `${rowList[0]?.customer || FALLBACK_TEXT} / ${rowList[0]?.name || FALLBACK_TEXT}`
        : rowList.length > 1
          ? `${rowList.length} partners/orders`
          : FALLBACK_TEXT
    const coverageLabel =
      detailData && detailData.items.length > 0
        ? '详情 downstream guard 已回读'
        : rowList.length > 0
          ? '列表 downstream guard 已回读'
          : 'downstream guard 待回读'
    const hasReadableSource = items.length > 0 || Boolean(detailData) || rowList.length > 0
    const cards: SalesOrderDownstreamGuardReadonlyCard[] = SALES_ORDER_DOWNSTREAM_GUARD_SUMMARY_FIELDS.map(
      (field) => {
        const cardValues: Record<DownstreamSummaryFieldKey, string> = {
          sourceCompletenessLabel: summary.sourceCompletenessLabel,
          downstreamStateLabel: summary.downstreamStateLabel,
          productionGuardLabel: summary.productionGuardLabel,
          purchaseGuardLabel: summary.purchaseGuardLabel,
          blockingCount: String(summary.blockingCount),
        }
        return {
          key: field.key,
          label: field.label,
          value: cardValues[field.key] || FALLBACK_TEXT,
        }
      },
    )

    return {
      queryStateLabel: `${tabValue} | parity=${parityValue} | focus=${focusValue} | loaded=${loadedAt}`,
      parityLabel: SALES_ORDER_DOWNSTREAM_GUARD_PARITY_LABEL,
      parityTone: parityValue === 'sales-order' ? 'success' : 'warning',
      focusLabel: SALES_ORDER_DOWNSTREAM_GUARD_FOCUS_LABEL,
      focusTone: focusValue === 'downstream-source' ? 'warning' : 'info',
      stateLabel: summary.stateLabel,
      stateTone: SALES_ORDER_DOWNSTREAM_GUARD_STATE_TAGS[summary.state],
      sourceStatusLabel: hasReadableSource
        ? `downstream-source readback ready / ${coverageLabel}`
        : 'downstream-source pending',
      sourceStatusTone: hasReadableSource ? 'success' : 'info',
      itemStatusLabel: `${items.length} 条伙伴/条目 / 阻断 ${summary.blockingCount} / 来源 ${sourceScopeLabel}`,
      blockedReason: errorMessage || summary.blockingReasonLabel,
      readonlyGuardReason: summary.guardReason || SALES_ORDER_DOWNSTREAM_GUARD_READONLY_GUARD_REASON,
      remainingGap: SALES_ORDER_DOWNSTREAM_GUARD_REMAINING_GAP,
      writeBoundary: SALES_ORDER_DOWNSTREAM_GUARD_WRITE_BOUNDARY,
      cards,
      disabledActions: SALES_ORDER_DOWNSTREAM_GUARD_DISABLED_ACTIONS.map((action) => ({
        label: action.label,
        reason: action.reason,
      })),
      items,
    }
  })

  return {
    downstreamGuardReadonlySummary,
  }
}
