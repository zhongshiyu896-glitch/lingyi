import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  WarehouseBatchItem,
  WarehouseSerialNumberItem,
  WarehouseTraceabilityItem,
} from '@/api/warehouse'
import {
  WAREHOUSE_TRACE_READONLY_ACTIONS,
  WAREHOUSE_TRACE_READONLY_BLOCKED_REASON,
  WAREHOUSE_TRACE_READONLY_GUARD_MESSAGE,
  WAREHOUSE_TRACE_READONLY_METRIC_FIELDS,
  WAREHOUSE_TRACE_READONLY_REMAINING_GAP,
  WAREHOUSE_TRACE_READONLY_ROUTE_LABELS,
  WAREHOUSE_TRACE_READONLY_STATUS_FIELDS,
  WAREHOUSE_TRACE_READONLY_WRITE_BOUNDARY,
  type WarehouseTraceReadonlyGuardedAction,
  type WarehouseTraceReadonlyTagType,
} from '@/views/warehouse/constants/warehouseTraceReadonlyFields'

type GuardTone = WarehouseTraceReadonlyTagType

export interface WarehouseTraceReadonlyMetric {
  key: string
  label: string
  value: string
}

export interface WarehouseTraceReadonlyStatusCard {
  key: string
  title: string
  statusLabel: string
  statusTone: GuardTone
  value: string
  note: string
}

export interface WarehouseTraceReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: WarehouseTraceReadonlyMetric[]
  statusCards: WarehouseTraceReadonlyStatusCard[]
  guardedActions: Array<WarehouseTraceReadonlyGuardedAction & { disabled: true }>
  currentPathLabel: string
  parityLabel: string
  focusLabel: string
  sourceStatusLabel: string
  sourceStatusTone: GuardTone
  itemStatusSummary: string
  blockedReason: string
  readonlyGuard: string
  remainingGap: string
  writeBoundary: string
}

interface UseWarehouseTraceReadonlyOptions {
  batchRows: MaybeRef<WarehouseBatchItem[]>
  serialRows: MaybeRef<WarehouseSerialNumberItem[]>
  traceabilityRows: MaybeRef<WarehouseTraceabilityItem[]>
  canRead: MaybeRef<boolean>
  parity: MaybeRef<string>
  currentPath: MaybeRef<string>
  focus: MaybeRef<string>
}

const normalizeRouteLabel = (currentPath: string): string => {
  const normalizedCurrentPath = currentPath.trim()
  return normalizedCurrentPath || WAREHOUSE_TRACE_READONLY_ROUTE_LABELS.defaultRoute
}

const resolveParityLabel = (parity: string): string => {
  if (parity === 'inventory-balance') return 'inventory-balance parity'
  if (parity === 'product-stock') return 'product-stock parity'
  if (parity === 'foundation-warehouse') return 'foundation-warehouse parity'
  return 'inventory-balance parity'
}

const resolveParityTone = (parity: string): GuardTone => {
  if (parity === 'inventory-balance') return 'success'
  if (parity === 'product-stock') return 'info'
  if (parity === 'foundation-warehouse') return 'warning'
  return 'success'
}

const resolveFocusLabel = (focus: string): string => (
  focus === 'trace-source' ? 'trace-source focus' : 'trace-source focus (default)'
)

const toSample = (values: string[], fallback: string): string => (
  values.length > 0 ? values.slice(0, 3).join(' ; ') : fallback
)

export const useWarehouseTraceReadonly = ({
  batchRows,
  serialRows,
  traceabilityRows,
  canRead,
  parity,
  currentPath,
  focus,
}: UseWarehouseTraceReadonlyOptions): {
  warehouseTraceReadonlySummary: ComputedRef<WarehouseTraceReadonlySummary>
} => {
  const warehouseTraceReadonlySummary = computed<WarehouseTraceReadonlySummary>(() => {
    const readable = Boolean(unref(canRead))
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedCurrentPath = String(unref(currentPath) || '').trim()
    const normalizedFocus = String(unref(focus) || '').trim().toLowerCase()
    const currentBatchRows = unref(batchRows)
    const currentSerialRows = unref(serialRows)
    const currentTraceabilityRows = unref(traceabilityRows)

    const routeLabel = normalizeRouteLabel(normalizedCurrentPath)
    const focusLabel = resolveFocusLabel(normalizedFocus)
    const sourceCount = currentTraceabilityRows.filter((row) => (
      Boolean(row.voucher_no) || Boolean(row.batch_no) || Boolean(row.serial_no)
    )).length

    const sourceStatusLabel = !readable
      ? 'trace-source guarded'
      : sourceCount > 0
        ? 'trace-source ready'
        : 'trace-source pending'
    const sourceStatusTone: GuardTone = !readable ? 'danger' : sourceCount > 0 ? 'success' : 'info'

    const itemStatusSummary = !readable
      ? 'trace item/status 仅保留 guarded fallback。'
      : `trace=${currentTraceabilityRows.length} / batch=${currentBatchRows.length} / serial=${currentSerialRows.length}`

    const tags = [
      {
        key: 'query',
        label: routeLabel,
        type: 'info' as GuardTone,
      },
      {
        key: 'parity',
        label: resolveParityLabel(normalizedParity),
        type: resolveParityTone(normalizedParity),
      },
      {
        key: 'focus',
        label: focusLabel,
        type: 'warning' as GuardTone,
      },
      {
        key: 'status',
        label: sourceStatusLabel,
        type: sourceStatusTone,
      },
    ]

    const metrics = WAREHOUSE_TRACE_READONLY_METRIC_FIELDS.map((field) => {
      switch (field.key) {
        case 'traceCount':
          return { key: field.key, label: field.label, value: String(currentTraceabilityRows.length) }
        case 'batchCount':
          return { key: field.key, label: field.label, value: String(currentBatchRows.length) }
        case 'serialCount':
          return { key: field.key, label: field.label, value: String(currentSerialRows.length) }
        case 'sourceCount':
          return { key: field.key, label: field.label, value: String(sourceCount) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const statusCards = WAREHOUSE_TRACE_READONLY_STATUS_FIELDS.map((field) => {
      if (field.key === 'trace_item') {
        return {
          key: field.key,
          title: field.title,
          statusLabel: currentTraceabilityRows.length > 0 ? 'trace item ready' : 'trace item pending',
          statusTone: currentTraceabilityRows.length > 0 ? ('success' as GuardTone) : ('info' as GuardTone),
          value: String(currentTraceabilityRows.length),
          note: `sample=${toSample(currentTraceabilityRows.map((row) => row.voucher_no || '-'), '-')}`,
        }
      }

      if (field.key === 'batch_status') {
        return {
          key: field.key,
          title: field.title,
          statusLabel: currentBatchRows.length > 0 ? 'batch source ready' : 'batch source pending',
          statusTone: currentBatchRows.length > 0 ? ('success' as GuardTone) : ('info' as GuardTone),
          value: String(currentBatchRows.length),
          note: `sample=${toSample(currentBatchRows.map((row) => row.batch_no || '-'), '-')}`,
        }
      }

      if (field.key === 'serial_status') {
        return {
          key: field.key,
          title: field.title,
          statusLabel: currentSerialRows.length > 0 ? 'serial source ready' : 'serial source pending',
          statusTone: currentSerialRows.length > 0 ? ('success' as GuardTone) : ('info' as GuardTone),
          value: String(currentSerialRows.length),
          note: `sample=${toSample(currentSerialRows.map((row) => row.serial_no || '-'), '-')}`,
        }
      }

      return {
        key: field.key,
        title: field.title,
        statusLabel: sourceStatusLabel,
        statusTone: sourceStatusTone,
        value: String(sourceCount),
        note: `${WAREHOUSE_TRACE_READONLY_ROUTE_LABELS.sourceLabel}=${focusLabel}`,
      }
    })

    return {
      tags,
      metrics,
      statusCards,
      guardedActions: WAREHOUSE_TRACE_READONLY_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      currentPathLabel: routeLabel,
      parityLabel: resolveParityLabel(normalizedParity),
      focusLabel,
      sourceStatusLabel,
      sourceStatusTone,
      itemStatusSummary,
      blockedReason: WAREHOUSE_TRACE_READONLY_BLOCKED_REASON,
      readonlyGuard: WAREHOUSE_TRACE_READONLY_GUARD_MESSAGE,
      remainingGap: WAREHOUSE_TRACE_READONLY_REMAINING_GAP,
      writeBoundary: WAREHOUSE_TRACE_READONLY_WRITE_BOUNDARY,
    }
  })

  return {
    warehouseTraceReadonlySummary,
  }
}
