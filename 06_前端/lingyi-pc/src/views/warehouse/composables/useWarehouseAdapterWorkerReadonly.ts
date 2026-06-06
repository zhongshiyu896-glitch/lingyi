import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  WarehouseManagementItem,
  WarehouseOtherInboundItem,
  WarehousePurchaseReturnOutboundItem,
  WarehouseSemiFinishedOutboundItem,
  WarehouseStockSummaryItem,
} from '@/api/warehouse'
import {
  WAREHOUSE_ADAPTER_WORKER_DIAGNOSTIC_FIELDS,
  WAREHOUSE_ADAPTER_WORKER_GUARDED_ACTIONS,
  WAREHOUSE_ADAPTER_WORKER_GUARD_MESSAGE,
  WAREHOUSE_ADAPTER_WORKER_METRIC_FIELDS,
  WAREHOUSE_ADAPTER_WORKER_REMAINING_GAP,
  WAREHOUSE_ADAPTER_WORKER_ROUTE_LABELS,
  WAREHOUSE_ADAPTER_WORKER_WRITE_BOUNDARY,
  type WarehouseAdapterWorkerGuardedAction,
  type WarehouseAdapterWorkerTagType,
} from '@/views/warehouse/constants/warehouseAdapterWorkerFields'

type GuardTone = WarehouseAdapterWorkerTagType

export interface WarehouseAdapterWorkerReadonlyMetric {
  key: string
  label: string
  value: string
}

export interface WarehouseAdapterWorkerReadonlyCard {
  key: string
  title: string
  count: number
  statusLabel: string
  statusTone: GuardTone
  sourceRoute: string
  sourceModule: string
  sourceDescription: string
  blockedReason: string
  note: string
}

export interface WarehouseAdapterWorkerReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: WarehouseAdapterWorkerReadonlyMetric[]
  cards: WarehouseAdapterWorkerReadonlyCard[]
  guardedActions: Array<WarehouseAdapterWorkerGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  routeLabel: string
  parityLabel: string
  focusStateLabel: string
  adapterWorkerStatusLabel: string
  adapterWorkerStatusTone: GuardTone
  adapterWorkerStatusSummary: string
  blockedReasonSummary: string
  guardMessage: string
  remainingGap: string
  writeBoundary: string
}

interface UseWarehouseAdapterWorkerReadonlyOptions {
  summaryRows: MaybeRef<WarehouseStockSummaryItem[]>
  managementRows: MaybeRef<WarehouseManagementItem[]>
  otherInboundRows: MaybeRef<WarehouseOtherInboundItem[]>
  purchaseReturnOutboundRows: MaybeRef<WarehousePurchaseReturnOutboundItem[]>
  semiFinishedOutboundRows: MaybeRef<WarehouseSemiFinishedOutboundItem[]>
  canRead: MaybeRef<boolean>
  parity: MaybeRef<string>
  currentPath: MaybeRef<string>
}

const resolveRouteLabel = (currentPath: string): string => {
  if (currentPath.includes('focus=worker-chain')) return WAREHOUSE_ADAPTER_WORKER_ROUTE_LABELS.focusRoute
  if (currentPath.includes('tab=adapter-worker')) return WAREHOUSE_ADAPTER_WORKER_ROUTE_LABELS.parityRoute
  return WAREHOUSE_ADAPTER_WORKER_ROUTE_LABELS.defaultRoute
}

const resolveFocusStateLabel = (currentPath: string): string => (
  currentPath.includes('focus=worker-chain') ? 'worker-chain focus' : 'summary focus'
)

const resolveParityLabel = (parity: string): string => (
  parity === 'product-stock' ? 'product-stock parity' : 'warehouse readonly parity'
)

const resolveParityTone = (parity: string): GuardTone => (
  parity === 'product-stock' ? 'info' : 'warning'
)

const toSampleNote = (values: string[], emptyNote: string): string => {
  if (values.length === 0) return emptyNote
  return `sample=${values.slice(0, 3).join(' ; ')}`
}

const buildRowStatus = (totalCount: number, blockedCount: number): { label: string; tone: GuardTone } => {
  if (totalCount === 0) return { label: '待回读', tone: 'info' }
  if (blockedCount > 0) return { label: '存在阻断', tone: 'warning' }
  return { label: '已回读', tone: 'success' }
}

export const useWarehouseAdapterWorkerReadonly = ({
  summaryRows,
  managementRows,
  otherInboundRows,
  purchaseReturnOutboundRows,
  semiFinishedOutboundRows,
  canRead,
  parity,
  currentPath,
}: UseWarehouseAdapterWorkerReadonlyOptions): {
  warehouseAdapterWorkerReadonlySummary: ComputedRef<WarehouseAdapterWorkerReadonlySummary>
} => {
  const warehouseAdapterWorkerReadonlySummary = computed<WarehouseAdapterWorkerReadonlySummary>(() => {
    const readable = Boolean(unref(canRead))
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedCurrentPath = String(unref(currentPath) || '').trim()
    const currentSummaryRows = unref(summaryRows)
    const currentManagementRows = unref(managementRows)
    const currentOtherInboundRows = unref(otherInboundRows)
    const currentPurchaseReturnOutboundRows = unref(purchaseReturnOutboundRows)
    const currentSemiFinishedOutboundRows = unref(semiFinishedOutboundRows)

    const managementBlockedCount = currentManagementRows.filter((row) => row.status !== 'normal').length
    const otherInboundPendingCount = currentOtherInboundRows.filter((row) => row.status === 'pending').length
    const purchaseReturnPendingCount = currentPurchaseReturnOutboundRows.filter((row) => row.status === 'pending').length
    const semiFinishedPendingCount = currentSemiFinishedOutboundRows.filter((row) => row.status === 'pending').length
    const adapterPendingCount = otherInboundPendingCount + purchaseReturnPendingCount
    const workerPendingCount = semiFinishedPendingCount + managementBlockedCount
    const blockedChainCount = adapterPendingCount + workerPendingCount
    const routeLabel = resolveRouteLabel(normalizedCurrentPath)
    const focusStateLabel = resolveFocusStateLabel(normalizedCurrentPath)
    const adapterWorkerStatus = !readable
      ? { label: '只读受限', tone: 'danger' as GuardTone }
      : buildRowStatus(
        currentOtherInboundRows.length + currentPurchaseReturnOutboundRows.length + currentSemiFinishedOutboundRows.length,
        blockedChainCount,
      )

    const tags = [
      {
        key: 'source',
        label: `${WAREHOUSE_ADAPTER_WORKER_ROUTE_LABELS.sourceLabel}: ${routeLabel}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: WAREHOUSE_ADAPTER_WORKER_ROUTE_LABELS.readonlyMode,
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
        type: normalizedCurrentPath.includes('focus=worker-chain') ? ('warning' as GuardTone) : ('info' as GuardTone),
      },
      {
        key: 'status',
        label: adapterWorkerStatus.label,
        type: adapterWorkerStatus.tone,
      },
    ]

    const metrics = WAREHOUSE_ADAPTER_WORKER_METRIC_FIELDS.map((field) => {
      switch (field.key) {
        case 'productStockSkuCount':
          return { key: field.key, label: field.label, value: String(currentSummaryRows.length) }
        case 'adapterPendingCount':
          return { key: field.key, label: field.label, value: String(adapterPendingCount) }
        case 'workerPendingCount':
          return { key: field.key, label: field.label, value: String(workerPendingCount) }
        case 'blockedChainCount':
          return { key: field.key, label: field.label, value: String(blockedChainCount) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const cards = WAREHOUSE_ADAPTER_WORKER_DIAGNOSTIC_FIELDS.map((field) => {
      if (field.key === 'other_inbound_adapter') {
        const status = buildRowStatus(currentOtherInboundRows.length, otherInboundPendingCount)
        return {
          key: field.key,
          title: field.title,
          count: currentOtherInboundRows.length,
          statusLabel: status.label,
          statusTone: status.tone,
          sourceRoute: field.sourceRoute,
          sourceModule: field.sourceModule,
          sourceDescription: field.sourceDescription,
          blockedReason: field.blockedReason,
          note: toSampleNote(
            currentOtherInboundRows.map((row) => `${row.inbound_no}:${row.status}`),
            '当前查询范围未回读到其他入仓 adapter 数据。',
          ),
        }
      }

      if (field.key === 'purchase_return_adapter') {
        const status = buildRowStatus(currentPurchaseReturnOutboundRows.length, purchaseReturnPendingCount)
        return {
          key: field.key,
          title: field.title,
          count: currentPurchaseReturnOutboundRows.length,
          statusLabel: status.label,
          statusTone: status.tone,
          sourceRoute: field.sourceRoute,
          sourceModule: field.sourceModule,
          sourceDescription: field.sourceDescription,
          blockedReason: field.blockedReason,
          note: toSampleNote(
            currentPurchaseReturnOutboundRows.map((row) => `${row.outbound_no}:${row.status}`),
            '当前查询范围未回读到采购退料出仓 adapter 数据。',
          ),
        }
      }

      const status = buildRowStatus(currentSemiFinishedOutboundRows.length, semiFinishedPendingCount)
      return {
        key: field.key,
        title: field.title,
        count: currentSemiFinishedOutboundRows.length,
        statusLabel: status.label,
        statusTone: status.tone,
        sourceRoute: field.sourceRoute,
        sourceModule: field.sourceModule,
        sourceDescription: field.sourceDescription,
        blockedReason: field.blockedReason,
        note: toSampleNote(
          currentSemiFinishedOutboundRows.map((row) => `${row.outbound_no}:${row.status}`),
          '当前查询范围未回读到半成品出仓 worker 数据。',
        ),
      }
    })

    const adapterWorkerStatusSummary = !readable
      ? '当前账号仅允许仓库读侧回退，adapter-worker 区只保留 guarded readonly 提示。'
      : `${routeLabel} 已回读库存 SKU ${currentSummaryRows.length} 条，adapter 待处理 ${adapterPendingCount} 条，worker 待处理 ${workerPendingCount} 条。`

    const blockedReasonSummary = blockedChainCount > 0
      ? `当前仍有 ${blockedChainCount} 条 adapter/worker 阻断项；库存执行链路保持只读，不放开 stock entry、出库、盘点、导出或 worker。`
      : '当前查询范围未出现 adapter/worker 阻断项，但仍保持只读边界，不放开真实库存执行。'

    return {
      tags,
      metrics,
      cards,
      guardedActions: WAREHOUSE_ADAPTER_WORKER_GUARDED_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: routeLabel,
      readonlyModeLabel: WAREHOUSE_ADAPTER_WORKER_ROUTE_LABELS.readonlyMode,
      routeLabel,
      parityLabel: resolveParityLabel(normalizedParity),
      focusStateLabel,
      adapterWorkerStatusLabel: adapterWorkerStatus.label,
      adapterWorkerStatusTone: adapterWorkerStatus.tone,
      adapterWorkerStatusSummary,
      blockedReasonSummary,
      guardMessage: WAREHOUSE_ADAPTER_WORKER_GUARD_MESSAGE,
      remainingGap: WAREHOUSE_ADAPTER_WORKER_REMAINING_GAP,
      writeBoundary: WAREHOUSE_ADAPTER_WORKER_WRITE_BOUNDARY,
    }
  })

  return {
    warehouseAdapterWorkerReadonlySummary,
  }
}
