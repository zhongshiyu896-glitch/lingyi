import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  WarehouseBatchItem,
  WarehouseSerialNumberItem,
  WarehouseTraceabilityItem,
} from '@/api/warehouse'
import {
  WAREHOUSE_TRACE_READONLY_ACTIONS,
  WAREHOUSE_TRACE_READONLY_DIAGNOSTIC_FIELDS,
  WAREHOUSE_TRACE_READONLY_GUARD_MESSAGE,
  WAREHOUSE_TRACE_READONLY_METRIC_FIELDS,
  WAREHOUSE_TRACE_READONLY_REMAINING_GAP,
  WAREHOUSE_TRACE_READONLY_ROUTE_LABELS,
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

export interface WarehouseTraceReadonlyCard {
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

export interface WarehouseTraceReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: WarehouseTraceReadonlyMetric[]
  cards: WarehouseTraceReadonlyCard[]
  guardedActions: Array<WarehouseTraceReadonlyGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  traceabilityStatusLabel: string
  traceabilityStatusTone: GuardTone
  traceabilityStatusSummary: string
  parityLabel: string
  parityTone: GuardTone
  breakpointSummary: string
  guardMessage: string
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
}

const normalizeRouteLabel = (currentPath: string, parity: string): string => {
  if (currentPath.includes('tab=diagnostic')) return WAREHOUSE_TRACE_READONLY_ROUTE_LABELS.diagnostic
  if (parity === 'product-stock') return WAREHOUSE_TRACE_READONLY_ROUTE_LABELS.productStockTraceability
  return WAREHOUSE_TRACE_READONLY_ROUTE_LABELS.traceability
}

const resolveParityLabel = (parity: string): string => {
  if (parity === 'product-stock') return 'product-stock parity'
  if (parity === 'foundation-warehouse') return 'foundation-warehouse parity'
  return 'warehouse traceability readonly'
}

const resolveParityTone = (parity: string): GuardTone => {
  if (parity === 'product-stock') return 'info'
  if (parity === 'foundation-warehouse') return 'warning'
  return 'success'
}

const toNumber = (value: string | number | null | undefined): number => {
  const numeric = Number(value ?? 0)
  return Number.isFinite(numeric) ? numeric : 0
}

const toSampleNote = (values: string[], emptyNote: string): string => {
  if (values.length === 0) return emptyNote
  return `sample=${values.slice(0, 3).join(' ; ')}`
}

export const useWarehouseTraceReadonly = ({
  batchRows,
  serialRows,
  traceabilityRows,
  canRead,
  parity,
  currentPath,
}: UseWarehouseTraceReadonlyOptions): {
  warehouseTraceReadonlySummary: ComputedRef<WarehouseTraceReadonlySummary>
} => {
  const warehouseTraceReadonlySummary = computed<WarehouseTraceReadonlySummary>(() => {
    const readable = Boolean(unref(canRead))
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedCurrentPath = String(unref(currentPath) || '').trim()
    const currentBatchRows = unref(batchRows)
    const currentSerialRows = unref(serialRows)
    const currentTraceabilityRows = unref(traceabilityRows)

    const batchNoSet = new Set(currentBatchRows.map((row) => String(row.batch_no || '').trim()).filter(Boolean))
    const anomalyBatchRows = currentBatchRows.filter((row) => row.disabled || toNumber(row.qty) <= 0)
    const anomalySerialRows = currentSerialRows.filter((row) => (row.status || 'Active') !== 'Active')
    const anomalyTraceabilityRows = currentTraceabilityRows.filter((row) => (
      !row.batch_no
      || !row.serial_no
      || !row.voucher_no
      || toNumber(row.qty_after_transaction) < 0
    ))

    const batchBreakpointRows = currentTraceabilityRows.filter((row) => (
      !row.batch_no || !batchNoSet.has(String(row.batch_no || '').trim())
    ))
    const documentBreakpointRows = [
      ...currentSerialRows.filter((row) => !row.delivery_document_no && !row.purchase_document_no),
      ...currentTraceabilityRows.filter((row) => !row.voucher_no),
    ]

    const anomalyNodeCount = anomalyBatchRows.length + anomalySerialRows.length + anomalyTraceabilityRows.length
    const routeLabel = normalizeRouteLabel(normalizedCurrentPath, normalizedParity)
    const traceabilityStatusLabel = !readable
      ? '追溯链路只读受限'
      : currentBatchRows.length + currentSerialRows.length + currentTraceabilityRows.length === 0
        ? '追溯链路待真实回读'
        : anomalyNodeCount > 0 || batchBreakpointRows.length > 0 || documentBreakpointRows.length > 0
          ? '追溯链路存在异常节点'
          : '追溯链路已回读'
    const traceabilityStatusTone: GuardTone = !readable
      ? 'danger'
      : currentBatchRows.length + currentSerialRows.length + currentTraceabilityRows.length === 0
        ? 'info'
        : anomalyNodeCount > 0 || batchBreakpointRows.length > 0 || documentBreakpointRows.length > 0
          ? 'warning'
          : 'success'

    const traceabilityStatusSummary = !readable
      ? '当前账号仅允许仓库追溯读侧回退，诊断区只保留 guarded readonly 提示。'
      : `${routeLabel} 已回读批次 ${currentBatchRows.length} 条、序列 ${currentSerialRows.length} 条、追溯流水 ${currentTraceabilityRows.length} 条。`

    const tags = [
      {
        key: 'source',
        label: `${WAREHOUSE_TRACE_READONLY_ROUTE_LABELS.sourceLabel}: ${routeLabel}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: WAREHOUSE_TRACE_READONLY_ROUTE_LABELS.readonlyMode,
        type: 'success' as GuardTone,
      },
      {
        key: 'parity',
        label: resolveParityLabel(normalizedParity),
        type: resolveParityTone(normalizedParity),
      },
      {
        key: 'status',
        label: traceabilityStatusLabel,
        type: traceabilityStatusTone,
      },
    ]

    const metrics = WAREHOUSE_TRACE_READONLY_METRIC_FIELDS.map((field) => {
      switch (field.key) {
        case 'batchCount':
          return { key: field.key, label: field.label, value: String(currentBatchRows.length) }
        case 'serialCount':
          return { key: field.key, label: field.label, value: String(currentSerialRows.length) }
        case 'ledgerCount':
          return { key: field.key, label: field.label, value: String(currentTraceabilityRows.length) }
        case 'anomalyNodeCount':
          return { key: field.key, label: field.label, value: String(anomalyNodeCount) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const cards = WAREHOUSE_TRACE_READONLY_DIAGNOSTIC_FIELDS.map((field) => {
      if (field.key === 'anomaly_nodes') {
        const sample = [
          ...anomalyBatchRows.map((row) => `batch:${row.batch_no || '-'}`),
          ...anomalySerialRows.map((row) => `serial:${row.serial_no || '-'}`),
          ...anomalyTraceabilityRows.map((row) => `voucher:${row.voucher_no || '-'}`),
        ]
        return {
          key: field.key,
          title: field.title,
          count: anomalyNodeCount,
          statusLabel: anomalyNodeCount > 0 ? '异常待核对' : '当前无异常',
          statusTone: anomalyNodeCount > 0 ? ('warning' as GuardTone) : ('success' as GuardTone),
          sourceRoute: field.sourceRoute,
          sourceModule: field.sourceModule,
          sourceDescription: field.sourceDescription,
          blockedReason: field.blockedReason,
          note: toSampleNote(sample, '当前查询范围未出现异常节点。'),
        }
      }

      if (field.key === 'batch_breakpoint') {
        const sample = batchBreakpointRows.map((row) => `${row.voucher_no || '-'} / ${row.batch_no || '-'}`)
        return {
          key: field.key,
          title: field.title,
          count: batchBreakpointRows.length,
          statusLabel: batchBreakpointRows.length > 0 ? '批次断链待核对' : '批次链路完整',
          statusTone: batchBreakpointRows.length > 0 ? ('warning' as GuardTone) : ('success' as GuardTone),
          sourceRoute: field.sourceRoute,
          sourceModule: field.sourceModule,
          sourceDescription: field.sourceDescription,
          blockedReason: field.blockedReason,
          note: toSampleNote(sample, '当前查询范围未出现批次断点。'),
        }
      }

      const sample = [
        ...currentSerialRows
          .filter((row) => !row.delivery_document_no && !row.purchase_document_no)
          .map((row) => `${row.serial_no || '-'} / -`),
        ...currentTraceabilityRows
          .filter((row) => !row.voucher_no)
          .map((row) => `${row.voucher_type || '-'} / -`),
      ]
      return {
        key: field.key,
        title: field.title,
        count: documentBreakpointRows.length,
        statusLabel: documentBreakpointRows.length > 0 ? '单据断链待核对' : '单据链路完整',
        statusTone: documentBreakpointRows.length > 0 ? ('warning' as GuardTone) : ('success' as GuardTone),
        sourceRoute: field.sourceRoute,
        sourceModule: field.sourceModule,
        sourceDescription: field.sourceDescription,
        blockedReason: field.blockedReason,
        note: toSampleNote(sample, '当前查询范围未出现单据断点。'),
      }
    })

    return {
      tags,
      metrics,
      cards,
      guardedActions: WAREHOUSE_TRACE_READONLY_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: routeLabel,
      readonlyModeLabel: WAREHOUSE_TRACE_READONLY_ROUTE_LABELS.readonlyMode,
      traceabilityStatusLabel,
      traceabilityStatusTone,
      traceabilityStatusSummary,
      parityLabel: resolveParityLabel(normalizedParity),
      parityTone: resolveParityTone(normalizedParity),
      breakpointSummary: `批次断点 ${batchBreakpointRows.length} 条，单据断点 ${documentBreakpointRows.length} 条。`,
      guardMessage: WAREHOUSE_TRACE_READONLY_GUARD_MESSAGE,
      remainingGap: WAREHOUSE_TRACE_READONLY_REMAINING_GAP,
      writeBoundary: WAREHOUSE_TRACE_READONLY_WRITE_BOUNDARY,
    }
  })

  return {
    warehouseTraceReadonlySummary,
  }
}
