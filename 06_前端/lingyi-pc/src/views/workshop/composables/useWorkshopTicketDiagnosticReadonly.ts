import { computed, type ComputedRef, type Ref } from 'vue'
import type { WorkshopTicketRow } from '@/api/workshop'
import {
  WORKSHOP_TICKET_DIAGNOSTIC_FIELDS,
  WORKSHOP_TICKET_DIAGNOSTIC_GUARD_MESSAGE,
  WORKSHOP_TICKET_DIAGNOSTIC_METRICS,
  WORKSHOP_TICKET_DIAGNOSTIC_READONLY_ACTIONS,
  WORKSHOP_TICKET_DIAGNOSTIC_REMAINING_GAP,
  WORKSHOP_TICKET_DIAGNOSTIC_ROUTE_LABELS,
  type WorkshopTicketDiagnosticGuardedAction,
  type WorkshopTicketDiagnosticTagType,
} from '../constants/workshopTicketDiagnosticFields'

type GuardTone = WorkshopTicketDiagnosticTagType

export interface WorkshopTicketDiagnosticMetric {
  key: string
  label: string
  value: string
}

export interface WorkshopTicketDiagnosticCard {
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

export interface WorkshopTicketDiagnosticReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: WorkshopTicketDiagnosticMetric[]
  cards: WorkshopTicketDiagnosticCard[]
  guardedActions: Array<WorkshopTicketDiagnosticGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  guardMessage: string
  remainingGap: string
}

const toCountLabel = (value: number): string => `${value}`

const buildCardRows = (rows: WorkshopTicketRow[], key: WorkshopTicketDiagnosticCard['key']) => {
  if (key === 'batch_exception') {
    return rows.filter((row) => ['failed', 'dead', 'blocked_scope'].includes(row.sync_status))
  }
  if (key === 'sync_block') {
    return rows.filter((row) => ['pending', 'processing', 'blocked_scope'].includes(row.sync_status))
  }
  return rows.filter((row) => row.operation_type === 'reversal')
}

const toStatusTone = (count: number, key: WorkshopTicketDiagnosticCard['key']): GuardTone => {
  if (count <= 0) return 'info'
  if (key === 'batch_exception') return 'danger'
  if (key === 'sync_block') return 'warning'
  return 'success'
}

const toStatusLabel = (count: number, key: WorkshopTicketDiagnosticCard['key']): string => {
  if (count <= 0) return '当前无异常'
  if (key === 'batch_exception') return '异常待核对'
  if (key === 'sync_block') return '阻断待核对'
  return '撤销差异待核对'
}

const toNote = (rows: WorkshopTicketRow[], key: WorkshopTicketDiagnosticCard['key']): string => {
  if (rows.length === 0) {
    if (key === 'batch_exception') return '当前查询范围未出现批次异常工票。'
    if (key === 'sync_block') return '当前查询范围未出现同步阻断工票。'
    return '当前查询范围未出现撤销差异工票。'
  }
  const sample = rows
    .slice(0, 3)
    .map((row) => `${row.ticket_no}/${row.sync_status}`)
    .join(' ; ')
  return `sample=${sample}`
}

export const useWorkshopTicketDiagnosticReadonly = (params: {
  rows: Ref<WorkshopTicketRow[]>
  canRead: ComputedRef<boolean>
  currentPath: ComputedRef<string>
}): ComputedRef<WorkshopTicketDiagnosticReadonlySummary> =>
  computed<WorkshopTicketDiagnosticReadonlySummary>(() => {
    const rows = params.rows.value
    const exceptionRows = rows.filter((row) => ['failed', 'dead', 'blocked_scope'].includes(row.sync_status))
    const pendingRows = rows.filter((row) => ['pending', 'processing', 'blocked_scope'].includes(row.sync_status))
    const reversalRows = rows.filter((row) => row.operation_type === 'reversal')

    const tags = [
      {
        key: 'source',
        label: `${WORKSHOP_TICKET_DIAGNOSTIC_ROUTE_LABELS.sourceLabel}: ${WORKSHOP_TICKET_DIAGNOSTIC_ROUTE_LABELS.diagnostic}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: WORKSHOP_TICKET_DIAGNOSTIC_ROUTE_LABELS.readonlyMode,
        type: 'success' as GuardTone,
      },
      {
        key: 'route',
        label: `current_path=${params.currentPath.value}`,
        type: 'warning' as GuardTone,
      },
      {
        key: 'guard',
        label: params.canRead.value ? '只读诊断开放' : '列表只读受限',
        type: params.canRead.value ? ('success' as GuardTone) : ('danger' as GuardTone),
      },
    ]

    const metrics = WORKSHOP_TICKET_DIAGNOSTIC_METRICS.map((field) => {
      switch (field.key) {
        case 'ticketCount':
          return { key: field.key, label: field.label, value: toCountLabel(rows.length) }
        case 'exceptionCount':
          return { key: field.key, label: field.label, value: toCountLabel(exceptionRows.length) }
        case 'pendingCount':
          return { key: field.key, label: field.label, value: toCountLabel(pendingRows.length) }
        case 'reversalCount':
          return { key: field.key, label: field.label, value: toCountLabel(reversalRows.length) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const cards = WORKSHOP_TICKET_DIAGNOSTIC_FIELDS.map((field) => {
      const scopedRows = buildCardRows(rows, field.key)
      return {
        key: field.key,
        title: field.title,
        count: scopedRows.length,
        statusLabel: toStatusLabel(scopedRows.length, field.key),
        statusTone: toStatusTone(scopedRows.length, field.key),
        sourceRoute: field.sourceRoute,
        sourceModule: field.sourceModule,
        sourceDescription: field.sourceDescription,
        blockedReason: field.blockedReason,
        note: toNote(scopedRows, field.key),
      }
    })

    return {
      tags,
      metrics,
      cards,
      guardedActions: WORKSHOP_TICKET_DIAGNOSTIC_READONLY_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: WORKSHOP_TICKET_DIAGNOSTIC_ROUTE_LABELS.current,
      readonlyModeLabel: WORKSHOP_TICKET_DIAGNOSTIC_ROUTE_LABELS.readonlyMode,
      guardMessage: WORKSHOP_TICKET_DIAGNOSTIC_GUARD_MESSAGE,
      remainingGap: WORKSHOP_TICKET_DIAGNOSTIC_REMAINING_GAP,
    }
  })
