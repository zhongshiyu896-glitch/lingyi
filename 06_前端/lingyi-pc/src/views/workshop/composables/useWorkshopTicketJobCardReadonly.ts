import { computed, unref, type ComputedRef, type MaybeRef, type Ref } from 'vue'
import type { WorkshopTicketRow } from '@/api/workshop'
import {
  WORKSHOP_TICKET_JOB_CARD_READONLY_GUARDED_ACTIONS,
  WORKSHOP_TICKET_JOB_CARD_READONLY_GUARD_MESSAGE,
  WORKSHOP_TICKET_JOB_CARD_READONLY_METRIC_FIELDS,
  WORKSHOP_TICKET_JOB_CARD_READONLY_REMAINING_GAP,
  WORKSHOP_TICKET_JOB_CARD_READONLY_ROUTE_LABELS,
  WORKSHOP_TICKET_JOB_CARD_READONLY_WRITE_BOUNDARY,
  type WorkshopTicketJobCardReadonlyGuardedAction,
  type WorkshopTicketJobCardReadonlyTagType,
} from '@/views/workshop/constants/workshopTicketJobCardReadonlyFields'

type GuardTone = WorkshopTicketJobCardReadonlyTagType

export interface WorkshopTicketJobCardReadonlyMetric {
  key: string
  label: string
  value: string
}

export interface WorkshopTicketJobCardReadonlyItem {
  key: string
  title: string
  scopeLabel: string
  statusLabel: string
  statusTone: GuardTone
  sourceStatusLabel: string
  blockedReason: string
  note: string
}

export interface WorkshopTicketJobCardReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: WorkshopTicketJobCardReadonlyMetric[]
  items: WorkshopTicketJobCardReadonlyItem[]
  guardedActions: Array<WorkshopTicketJobCardReadonlyGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  parityLabel: string
  focusStateLabel: string
  sourceStatusLabel: string
  queryStateLabel: string
  itemStatusLabel: string
  itemStatusTone: GuardTone
  jobCardSummary: string
  blockedReasonSummary: string
  guardMessage: string
  remainingGap: string
  writeBoundary: string
}

interface UseWorkshopTicketJobCardReadonlyOptions {
  rows: Ref<WorkshopTicketRow[]>
  canRead: MaybeRef<boolean>
  currentPath: MaybeRef<string>
  parity: MaybeRef<string>
  focus: MaybeRef<string>
  queryStateLabel: MaybeRef<string>
}

const resolveRouteLabel = (currentPath: string): string => {
  if (currentPath.includes('focus=job-card-source')) {
    return WORKSHOP_TICKET_JOB_CARD_READONLY_ROUTE_LABELS.focusRoute
  }
  if (currentPath.includes('tab=job-card-readonly')) {
    return WORKSHOP_TICKET_JOB_CARD_READONLY_ROUTE_LABELS.parityRoute
  }
  return WORKSHOP_TICKET_JOB_CARD_READONLY_ROUTE_LABELS.defaultRoute
}

const resolveFocusStateLabel = (focus: string): string => (
  focus === 'job-card-source' ? 'job-card-source focus' : 'job-card-summary focus'
)

const resolveParityLabel = (parity: string): string => (
  parity === 'production-order' ? 'production-order parity' : 'production-order parity'
)

const isBlockedSyncStatus = (value: string): boolean => (
  ['pending', 'processing', 'failed', 'dead', 'blocked_scope'].includes(value)
)

const buildStatus = (
  canRead: boolean,
  rows: WorkshopTicketRow[],
): { label: string; tone: GuardTone } => {
  if (!canRead) {
    return { label: '无列表查看权限，仅保留只读核对', tone: 'danger' }
  }
  if (rows.length === 0) {
    return { label: '待加载工序卡样本', tone: 'warning' }
  }
  if (rows.some((row) => isBlockedSyncStatus(row.sync_status))) {
    return { label: '同步阻断待核对', tone: 'warning' }
  }
  return { label: 'job-card 只读样本已就绪', tone: 'success' }
}

const resolvePrimaryRow = (rows: WorkshopTicketRow[]): WorkshopTicketRow | null => {
  if (rows.length === 0) {
    return null
  }
  return rows.find((row) => Boolean(String(row.source_ref || '').trim())) || rows[0]
}

const buildSourceStatusLabel = (
  row: WorkshopTicketRow | null,
  focus: string,
): string => {
  if (focus === 'job-card-source') {
    if (!row) {
      return 'job-card-source=pending-source-ref'
    }
    return `job-card-source=${row.source || 'manual'} / ${row.source_ref || 'pending-source-ref'}`
  }
  if (!row) {
    return 'job_card=pending-job-card / sync=pending'
  }
  return `job_card=${row.job_card || 'pending-job-card'} / sync=${row.sync_status || 'pending'}`
}

export const useWorkshopTicketJobCardReadonly = ({
  rows,
  canRead,
  currentPath,
  parity,
  focus,
  queryStateLabel,
}: UseWorkshopTicketJobCardReadonlyOptions): {
  workshopTicketJobCardReadonlySummary: ComputedRef<WorkshopTicketJobCardReadonlySummary>
} => {
  const workshopTicketJobCardReadonlySummary = computed<WorkshopTicketJobCardReadonlySummary>(() => {
    const currentRows = rows.value
    const canReadValue = Boolean(unref(canRead))
    const normalizedPath = String(unref(currentPath) || '').trim()
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedFocus = String(unref(focus) || '').trim().toLowerCase()
    const normalizedQueryState = String(unref(queryStateLabel) || '').trim() || 'job_card=ALL; employee=ALL'
    const routeLabel = resolveRouteLabel(normalizedPath)
    const focusStateLabel = resolveFocusStateLabel(normalizedFocus)
    const parityLabel = resolveParityLabel(normalizedParity)
    const status = buildStatus(canReadValue, currentRows)
    const primaryRow = resolvePrimaryRow(currentRows)
    const blockedRows = currentRows.filter((row) => isBlockedSyncStatus(row.sync_status))
    const sourceStatusLabel = buildSourceStatusLabel(primaryRow, normalizedFocus)
    const uniqueJobCardCount = new Set(currentRows.map((row) => row.job_card).filter(Boolean)).size
    const guardedActionCount = WORKSHOP_TICKET_JOB_CARD_READONLY_GUARDED_ACTIONS.length

    const tags = [
      {
        key: 'source',
        label: `${WORKSHOP_TICKET_JOB_CARD_READONLY_ROUTE_LABELS.sourceLabel}: ${routeLabel}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: WORKSHOP_TICKET_JOB_CARD_READONLY_ROUTE_LABELS.readonlyMode,
        type: 'success' as GuardTone,
      },
      {
        key: 'parity',
        label: parityLabel,
        type: 'info' as GuardTone,
      },
      {
        key: 'focus',
        label: focusStateLabel,
        type: normalizedFocus === 'job-card-source' ? ('warning' as GuardTone) : ('info' as GuardTone),
      },
      {
        key: 'status',
        label: status.label,
        type: status.tone,
      },
    ]

    const items: WorkshopTicketJobCardReadonlyItem[] = [
      {
        key: 'job-card-primary',
        title: `Job Card / ${primaryRow?.job_card || 'pending-job-card'}`,
        scopeLabel: `ticket_no=${primaryRow?.ticket_no || 'pending-ticket'}; employee=${primaryRow?.employee || 'pending-employee'}`,
        statusLabel: status.label,
        statusTone: status.tone,
        sourceStatusLabel,
        blockedReason:
          'blocked_reason=当前仅开放 job-card-readonly 与 production-order parity 核对，不允许真实派工、确认或工票执行。',
        note: `process=${primaryRow?.process_name || 'pending-process'}; qty=${primaryRow?.qty ?? 0}; work_date=${primaryRow?.work_date || 'pending-date'}; query_state=${normalizedQueryState}`,
      },
      {
        key: 'job-card-source',
        title: `来源镜像 / ${primaryRow?.source_ref || 'pending-source-ref'}`,
        scopeLabel: `source=${primaryRow?.source || 'manual'}; item_code=${primaryRow?.item_code || 'pending-item'}; created_by=${primaryRow?.created_by || 'pending-user'}`,
        statusLabel: blockedRows.length > 0 ? '同步阻断镜像' : '来源镜像已就绪',
        statusTone: blockedRows.length > 0 ? ('warning' as GuardTone) : ('success' as GuardTone),
        sourceStatusLabel,
        blockedReason:
          'blocked_reason=当前仅开放 job-card-source 只读核对，不允许真实 job-card sync、outbox、worker 或 ERPNext 执行。',
        note: blockedRows.length > 0
          ? `blocked_sync_sample=${blockedRows.slice(0, 3).map((row) => `${row.ticket_no}/${row.sync_status}`).join(' ; ')}`
          : `source_ref=${primaryRow?.source_ref || 'pending-source-ref'}; query_state=${normalizedQueryState}`,
      },
    ]

    const metrics = WORKSHOP_TICKET_JOB_CARD_READONLY_METRIC_FIELDS.map((field) => {
      switch (field.key) {
        case 'ticketCount':
          return { key: field.key, label: field.label, value: String(currentRows.length) }
        case 'jobCardCount':
          return { key: field.key, label: field.label, value: String(uniqueJobCardCount) }
        case 'blockedSyncCount':
          return { key: field.key, label: field.label, value: String(blockedRows.length) }
        case 'guardedActionCount':
          return { key: field.key, label: field.label, value: String(guardedActionCount) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const jobCardSummary = primaryRow
      ? `当前展示工序卡 ${primaryRow.job_card} 的只读镜像，样本工票 ${primaryRow.ticket_no}。`
      : '当前查询范围未命中工序卡样本，保留 job-card-readonly 只读占位摘要。'

    const blockedReasonSummary = !canReadValue
      ? '当前账号无工票列表查看权限；页面仅保留 job-card-readonly 只读核对摘要。'
      : '当前仅开放 production-order parity 与 job-card-source 只读核对；真实派工、确认、job-card sync、导出、outbox、worker、ERPNext 与跨模块执行保持关闭。'

    return {
      tags,
      metrics,
      items,
      guardedActions: WORKSHOP_TICKET_JOB_CARD_READONLY_GUARDED_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: routeLabel,
      readonlyModeLabel: WORKSHOP_TICKET_JOB_CARD_READONLY_ROUTE_LABELS.readonlyMode,
      parityLabel,
      focusStateLabel,
      sourceStatusLabel,
      queryStateLabel: normalizedQueryState,
      itemStatusLabel: status.label,
      itemStatusTone: status.tone,
      jobCardSummary,
      blockedReasonSummary,
      guardMessage: WORKSHOP_TICKET_JOB_CARD_READONLY_GUARD_MESSAGE,
      remainingGap: WORKSHOP_TICKET_JOB_CARD_READONLY_REMAINING_GAP,
      writeBoundary: WORKSHOP_TICKET_JOB_CARD_READONLY_WRITE_BOUNDARY,
    }
  })

  return {
    workshopTicketJobCardReadonlySummary,
  }
}
