import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import {
  WORKSHOP_TICKET_REGISTER_READONLY_GUARDED_ACTIONS,
  WORKSHOP_TICKET_REGISTER_READONLY_GUARD_MESSAGE,
  WORKSHOP_TICKET_REGISTER_READONLY_METRIC_FIELDS,
  WORKSHOP_TICKET_REGISTER_READONLY_REMAINING_GAP,
  WORKSHOP_TICKET_REGISTER_READONLY_ROUTE_LABELS,
  WORKSHOP_TICKET_REGISTER_READONLY_WRITE_BOUNDARY,
  type WorkshopTicketRegisterReadonlyGuardedAction,
  type WorkshopTicketRegisterReadonlyTagType,
} from '@/views/workshop/constants/workshopTicketRegisterReadonlyFields'

type GuardTone = WorkshopTicketRegisterReadonlyTagType

export interface WorkshopTicketRegisterReadonlyDraft {
  ticket_key: string
  job_card: string
  employee: string
  process_name: string
  color: string
  size: string
  qty: number
  work_date: string
  source: string
  source_ref: string
  original_ticket_id?: number
  reason: string
}

export interface WorkshopTicketRegisterReadonlyMetric {
  key: string
  label: string
  value: string
}

export interface WorkshopTicketRegisterReadonlyItem {
  key: string
  title: string
  scopeLabel: string
  statusLabel: string
  statusTone: GuardTone
  sourceStatusLabel: string
  blockedReason: string
  note: string
}

export interface WorkshopTicketRegisterReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: WorkshopTicketRegisterReadonlyMetric[]
  items: WorkshopTicketRegisterReadonlyItem[]
  guardedActions: Array<WorkshopTicketRegisterReadonlyGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  parityLabel: string
  focusStateLabel: string
  sourceStatusLabel: string
  queryStateLabel: string
  itemStatusLabel: string
  itemStatusTone: GuardTone
  registerSummary: string
  blockedReasonSummary: string
  guardMessage: string
  remainingGap: string
  writeBoundary: string
}

interface UseWorkshopTicketRegisterReadonlyOptions {
  mode: MaybeRef<'register' | 'reversal'>
  draft: MaybeRef<WorkshopTicketRegisterReadonlyDraft>
  activePermission: MaybeRef<boolean>
  requiredFields: MaybeRef<string[]>
  currentPath: MaybeRef<string>
  parity: MaybeRef<string>
  focus: MaybeRef<string>
  queryStateLabel: MaybeRef<string>
}

const resolveRouteLabel = (currentPath: string): string => {
  if (currentPath.includes('focus=dispatch-source')) return WORKSHOP_TICKET_REGISTER_READONLY_ROUTE_LABELS.focusRoute
  if (currentPath.includes('tab=order-parity')) return WORKSHOP_TICKET_REGISTER_READONLY_ROUTE_LABELS.parityRoute
  return WORKSHOP_TICKET_REGISTER_READONLY_ROUTE_LABELS.defaultRoute
}

const resolveFocusStateLabel = (focus: string): string => (
  focus === 'dispatch-source' ? 'dispatch-source focus' : 'register-summary focus'
)

const resolveParityLabel = (parity: string): string => (
  parity === 'production-order' ? 'production-order parity' : 'production-order parity'
)

const resolveSourceStatusLabel = (
  mode: 'register' | 'reversal',
  draft: WorkshopTicketRegisterReadonlyDraft,
  focus: string,
): string => {
  if (focus === 'dispatch-source') {
    return mode === 'register'
      ? `dispatch-source=${draft.source_ref || '待填写来源单号'}`
      : `dispatch-source=reversal/${draft.original_ticket_id || '待填写原工票ID'}`
  }
  return mode === 'register'
    ? `source=${draft.source || 'manual'} / ${draft.source_ref || '待填写来源单号'}`
    : `reversal reason=${draft.reason || '待填写撤销原因'}`
}

const buildStatus = (
  hasPermission: boolean,
  missingFields: string[],
): { label: string; tone: GuardTone } => {
  if (!hasPermission) return { label: '无写权限，仅保留只读核对', tone: 'danger' }
  if (missingFields.length > 0) return { label: '待补字段后进入只读预览', tone: 'warning' }
  return { label: '本地预览就绪', tone: 'success' }
}

const buildDraftFieldCount = (draft: WorkshopTicketRegisterReadonlyDraft): number => {
  const values = [
    draft.ticket_key,
    draft.job_card,
    draft.employee,
    draft.process_name,
    draft.color,
    draft.size,
    draft.source_ref,
    draft.reason,
    draft.work_date,
  ]
  return values.filter((value) => String(value || '').trim()).length + (draft.original_ticket_id ? 1 : 0)
}

export const useWorkshopTicketRegisterReadonly = ({
  mode,
  draft,
  activePermission,
  requiredFields,
  currentPath,
  parity,
  focus,
  queryStateLabel,
}: UseWorkshopTicketRegisterReadonlyOptions): {
  workshopTicketRegisterReadonlySummary: ComputedRef<WorkshopTicketRegisterReadonlySummary>
} => {
  const workshopTicketRegisterReadonlySummary = computed<WorkshopTicketRegisterReadonlySummary>(() => {
    const currentMode = unref(mode)
    const currentDraft = unref(draft)
    const hasPermission = Boolean(unref(activePermission))
    const missingFields = unref(requiredFields)
    const normalizedPath = String(unref(currentPath) || '').trim()
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedFocus = String(unref(focus) || '').trim().toLowerCase()
    const normalizedQueryState = String(unref(queryStateLabel) || '').trim() || 'mode=register; source=manual'
    const routeLabel = resolveRouteLabel(normalizedPath)
    const focusStateLabel = resolveFocusStateLabel(normalizedFocus)
    const parityLabel = resolveParityLabel(normalizedParity)
    const sourceStatusLabel = resolveSourceStatusLabel(currentMode, currentDraft, normalizedFocus)
    const status = buildStatus(hasPermission, missingFields)
    const guardedActionCount = WORKSHOP_TICKET_REGISTER_READONLY_GUARDED_ACTIONS.length

    const tags = [
      {
        key: 'source',
        label: `${WORKSHOP_TICKET_REGISTER_READONLY_ROUTE_LABELS.sourceLabel}: ${routeLabel}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: WORKSHOP_TICKET_REGISTER_READONLY_ROUTE_LABELS.readonlyMode,
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
        type: normalizedFocus === 'dispatch-source' ? ('warning' as GuardTone) : ('info' as GuardTone),
      },
      {
        key: 'status',
        label: status.label,
        type: status.tone,
      },
    ]

    const items: WorkshopTicketRegisterReadonlyItem[] = [
      {
        key: 'register-draft',
        title: `登记草稿 / ${currentDraft.job_card || 'job-card-draft'}`,
        scopeLabel: `ticket_key=${currentDraft.ticket_key || '待填写'}; employee=${currentDraft.employee || '待填写'}`,
        statusLabel: status.label,
        statusTone: status.tone,
        sourceStatusLabel: currentDraft.source_ref || 'dispatch-source 待填写',
        blockedReason: 'blocked_reason=当前仅开放工票登记 parity 只读核对，不允许真实登记、派工或确认执行。',
        note: `process=${currentDraft.process_name || '待填写'}; qty=${currentDraft.qty}; work_date=${currentDraft.work_date || '待选择'}; query_state=${normalizedQueryState}`,
      },
      {
        key: 'reversal-preview',
        title: `撤销预览 / ${currentDraft.original_ticket_id || '待填写原工票ID'}`,
        scopeLabel: `reason=${currentDraft.reason || '待填写撤销原因'}; mode=${currentMode}`,
        statusLabel: currentMode === 'reversal' ? '撤销只读预览' : '撤销影响待命',
        statusTone: currentMode === 'reversal' ? ('warning' as GuardTone) : ('info' as GuardTone),
        sourceStatusLabel: sourceStatusLabel,
        blockedReason: 'blocked_reason=当前仅开放 dispatch-source 与撤销影响只读核对，不允许真实撤销、job-card sync、outbox、worker 或 ERPNext 执行。',
        note: `source=${currentDraft.source || 'manual'}; source_ref=${currentDraft.source_ref || '待填写'}; query_state=${normalizedQueryState}`,
      },
    ]

    const metrics = WORKSHOP_TICKET_REGISTER_READONLY_METRIC_FIELDS.map((field) => {
      switch (field.key) {
        case 'draftFieldCount':
          return { key: field.key, label: field.label, value: String(buildDraftFieldCount(currentDraft)) }
        case 'missingFieldCount':
          return { key: field.key, label: field.label, value: String(missingFields.length) }
        case 'guardedActionCount':
          return { key: field.key, label: field.label, value: String(guardedActionCount) }
        case 'readonlyItemCount':
          return { key: field.key, label: field.label, value: String(items.length) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const registerSummary = currentMode === 'register'
      ? `当前展示登记草稿 parity：ticket_key=${currentDraft.ticket_key || '待填写'}，job_card=${currentDraft.job_card || '待填写'}，source_ref=${currentDraft.source_ref || '待填写'}。`
      : `当前展示撤销只读预览：original_ticket_id=${currentDraft.original_ticket_id || '待填写'}，reason=${currentDraft.reason || '待填写'}。`

    const blockedReasonSummary = !hasPermission
      ? '当前账号无真实写权限；页面仅保留工票登记 / 撤销只读核对摘要。'
      : '当前仅开放 order-parity、dispatch-source 与字段影响面核对；真实派工、确认、导出、outbox、worker、ERPNext 与跨模块执行保持关闭。'

    return {
      tags,
      metrics,
      items,
      guardedActions: WORKSHOP_TICKET_REGISTER_READONLY_GUARDED_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: routeLabel,
      readonlyModeLabel: WORKSHOP_TICKET_REGISTER_READONLY_ROUTE_LABELS.readonlyMode,
      parityLabel,
      focusStateLabel,
      sourceStatusLabel,
      queryStateLabel: normalizedQueryState,
      itemStatusLabel: status.label,
      itemStatusTone: status.tone,
      registerSummary,
      blockedReasonSummary,
      guardMessage: WORKSHOP_TICKET_REGISTER_READONLY_GUARD_MESSAGE,
      remainingGap: WORKSHOP_TICKET_REGISTER_READONLY_REMAINING_GAP,
      writeBoundary: WORKSHOP_TICKET_REGISTER_READONLY_WRITE_BOUNDARY,
    }
  })

  return {
    workshopTicketRegisterReadonlySummary,
  }
}
