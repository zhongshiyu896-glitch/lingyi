import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  WarehouseFinishedGoodsInboundCandidateItem,
  WarehouseStockSummaryItem,
} from '@/api/warehouse'
import {
  WAREHOUSE_FINISHED_GOODS_INBOUND_GUARDED_ACTIONS,
  WAREHOUSE_FINISHED_GOODS_INBOUND_GUARD_MESSAGE,
  WAREHOUSE_FINISHED_GOODS_INBOUND_METRIC_FIELDS,
  WAREHOUSE_FINISHED_GOODS_INBOUND_REMAINING_GAP,
  WAREHOUSE_FINISHED_GOODS_INBOUND_ROUTE_LABELS,
  WAREHOUSE_FINISHED_GOODS_INBOUND_WRITE_BOUNDARY,
  type WarehouseFinishedGoodsInboundGuardedAction,
  type WarehouseFinishedGoodsInboundTagType,
} from '@/views/warehouse/constants/warehouseFinishedGoodsInboundFields'

type GuardTone = WarehouseFinishedGoodsInboundTagType

export interface WarehouseFinishedGoodsInboundReadonlyMetric {
  key: string
  label: string
  value: string
}

export interface WarehouseFinishedGoodsInboundReadonlyItem {
  key: string
  title: string
  sourceId: string
  itemCode: string
  quantityLabel: string
  statusLabel: string
  statusTone: GuardTone
  blockedReason: string
  note: string
}

export interface WarehouseFinishedGoodsInboundReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: WarehouseFinishedGoodsInboundReadonlyMetric[]
  items: WarehouseFinishedGoodsInboundReadonlyItem[]
  guardedActions: Array<WarehouseFinishedGoodsInboundGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  parityLabel: string
  focusStateLabel: string
  inboundStatusLabel: string
  inboundStatusTone: GuardTone
  inboundSummary: string
  blockedReasonSummary: string
  disabledEntryLabel: string
  disabledEntryReason: string
  allocationContractLabel: string
  showCompletedForcedLabel: string
  guardMessage: string
  remainingGap: string
  writeBoundary: string
}

interface UseWarehouseFinishedGoodsInboundReadonlyOptions {
  summaryRows: MaybeRef<WarehouseStockSummaryItem[]>
  candidateRows: MaybeRef<WarehouseFinishedGoodsInboundCandidateItem[]>
  canRead: MaybeRef<boolean>
  parity: MaybeRef<string>
  currentPath: MaybeRef<string>
  disabledEntryLabel: MaybeRef<string>
  disabledEntryReason: MaybeRef<string>
  allocationContract: MaybeRef<string>
  showCompletedForced: MaybeRef<boolean>
}

const resolveRouteLabel = (currentPath: string): string => {
  if (currentPath.includes('focus=inbound-readonly')) return WAREHOUSE_FINISHED_GOODS_INBOUND_ROUTE_LABELS.focusRoute
  if (currentPath.includes('tab=finished-goods-inbound')) return WAREHOUSE_FINISHED_GOODS_INBOUND_ROUTE_LABELS.parityRoute
  return WAREHOUSE_FINISHED_GOODS_INBOUND_ROUTE_LABELS.defaultRoute
}

const resolveFocusStateLabel = (currentPath: string): string => (
  currentPath.includes('focus=inbound-readonly') ? 'inbound-readonly focus' : 'summary focus'
)

const resolveParityLabel = (parity: string): string => (
  parity === 'product-stock' ? 'product-stock parity' : 'warehouse readonly parity'
)

const resolveParityTone = (parity: string): GuardTone => (
  parity === 'product-stock' ? 'info' : 'warning'
)

const buildStatus = (
  readable: boolean,
  totalCount: number,
  blockedCount: number,
): { label: string; tone: GuardTone } => {
  if (!readable) return { label: '只读受限', tone: 'danger' }
  if (totalCount === 0) return { label: '待回读', tone: 'info' }
  if (blockedCount > 0) return { label: '存在阻断', tone: 'warning' }
  return { label: '已回读', tone: 'success' }
}

export const useWarehouseFinishedGoodsInboundReadonly = ({
  summaryRows,
  candidateRows,
  canRead,
  parity,
  currentPath,
  disabledEntryLabel,
  disabledEntryReason,
  allocationContract,
  showCompletedForced,
}: UseWarehouseFinishedGoodsInboundReadonlyOptions): {
  warehouseFinishedGoodsInboundReadonlySummary: ComputedRef<WarehouseFinishedGoodsInboundReadonlySummary>
} => {
  const warehouseFinishedGoodsInboundReadonlySummary = computed<WarehouseFinishedGoodsInboundReadonlySummary>(() => {
    const readable = Boolean(unref(canRead))
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedCurrentPath = String(unref(currentPath) || '').trim()
    const currentSummaryRows = unref(summaryRows)
    const currentCandidateRows = unref(candidateRows)
    const blockedCount = currentCandidateRows.filter((item) => item.disabled).length
    const readableCount = currentCandidateRows.length - blockedCount
    const inboundStatus = buildStatus(readable, currentCandidateRows.length, blockedCount)
    const routeLabel = resolveRouteLabel(normalizedCurrentPath)
    const focusStateLabel = resolveFocusStateLabel(normalizedCurrentPath)
    const disabledLabel = String(unref(disabledEntryLabel) || '').trim() || '成品预约入仓 -> 创建成品入仓'
    const disabledReason = String(unref(disabledEntryReason) || '').trim() || '当前仅开放 readonly inbound 核对，不开放真实入库创建。'
    const allocationContractLabel = String(unref(allocationContract) || '').trim() || 'strict_alloc -> zero_placeholder_fallback'
    const showCompletedForcedValue = Boolean(unref(showCompletedForced))

    const tags = [
      {
        key: 'source',
        label: `${WAREHOUSE_FINISHED_GOODS_INBOUND_ROUTE_LABELS.sourceLabel}: ${routeLabel}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: WAREHOUSE_FINISHED_GOODS_INBOUND_ROUTE_LABELS.readonlyMode,
        type: 'success' as GuardTone,
      },
      {
        key: 'parity',
        label: resolveParityLabel(normalizedParity),
        type: resolveParityTone(normalizedParity),
      },
      {
        key: 'focus',
        label: focusStateLabel,
        type: normalizedCurrentPath.includes('focus=inbound-readonly') ? ('warning' as GuardTone) : ('info' as GuardTone),
      },
      {
        key: 'status',
        label: inboundStatus.label,
        type: inboundStatus.tone,
      },
    ]

    const metrics = WAREHOUSE_FINISHED_GOODS_INBOUND_METRIC_FIELDS.map((field) => {
      switch (field.key) {
        case 'productStockSkuCount':
          return { key: field.key, label: field.label, value: String(currentSummaryRows.length) }
        case 'inboundCandidateCount':
          return { key: field.key, label: field.label, value: String(currentCandidateRows.length) }
        case 'blockedCandidateCount':
          return { key: field.key, label: field.label, value: String(blockedCount) }
        case 'readableCandidateCount':
          return { key: field.key, label: field.label, value: String(Math.max(readableCount, 0)) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const items = currentCandidateRows.map((item, index) => ({
      key: `${item.source_id || item.item_code}-${index}`,
      title: item.source_label,
      sourceId: item.source_id,
      itemCode: item.item_code,
      quantityLabel: `${item.qty} ${item.uom}`,
      statusLabel: item.disabled ? '阻断' : '可读',
      statusTone: (item.disabled ? 'warning' : 'success') as GuardTone,
      blockedReason: item.disabled
        ? (item.disabled_reason || 'blocked_reason=当前候选受控，不开放真实成品入库。')
        : 'blocked_reason=当前候选仅开放只读核对，仍不开放真实成品入库。',
      note: `allocation_contract=${allocationContractLabel}; disabled_entry=${disabledLabel}`,
    }))

    const inboundSummary = !readable
      ? '当前账号仅允许仓库读侧回退，finished-goods inbound 区只保留 guarded readonly 提示。'
      : `${routeLabel} 已回读库存 SKU ${currentSummaryRows.length} 条，finished-goods inbound 候选 ${currentCandidateRows.length} 条，阻断 ${blockedCount} 条。`

    const blockedReasonSummary = blockedCount > 0
      ? `当前仍有 ${blockedCount} 条 finished-goods inbound 阻断项；成品入库创建、过账、导出、worker 与 ERPNext 保持关闭。`
      : '当前查询范围未出现 finished-goods inbound 阻断项，但仍保持只读边界，不放开真实成品入库链路。'

    return {
      tags,
      metrics,
      items,
      guardedActions: WAREHOUSE_FINISHED_GOODS_INBOUND_GUARDED_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: routeLabel,
      readonlyModeLabel: WAREHOUSE_FINISHED_GOODS_INBOUND_ROUTE_LABELS.readonlyMode,
      parityLabel: resolveParityLabel(normalizedParity),
      focusStateLabel,
      inboundStatusLabel: inboundStatus.label,
      inboundStatusTone: inboundStatus.tone,
      inboundSummary,
      blockedReasonSummary,
      disabledEntryLabel: disabledLabel,
      disabledEntryReason: disabledReason,
      allocationContractLabel,
      showCompletedForcedLabel: showCompletedForcedValue ? 'show_completed_forced=true' : 'show_completed_forced=false',
      guardMessage: WAREHOUSE_FINISHED_GOODS_INBOUND_GUARD_MESSAGE,
      remainingGap: WAREHOUSE_FINISHED_GOODS_INBOUND_REMAINING_GAP,
      writeBoundary: WAREHOUSE_FINISHED_GOODS_INBOUND_WRITE_BOUNDARY,
    }
  })

  return {
    warehouseFinishedGoodsInboundReadonlySummary,
  }
}
