import { computed, type ComputedRef } from 'vue'
import {
  workshopBatchExceptionDisabledActions,
  workshopBatchExceptionFallbackBlockedReasons,
  type WorkshopBatchExceptionEntry,
  type WorkshopBatchExceptionLineItem,
  type WorkshopBatchExceptionSummaryCard,
  type WorkshopBatchExceptionTone,
} from '@/views/workshop/constants/workshopBatchExceptionFields'

export interface WorkshopBatchPreviewRowInput {
  row_index: number
  operation_type: string
  ticket_key: string
  job_card: string
  employee: string
  qty: number
}

export interface WorkshopBatchValidationRowInput {
  row_index: number
  ticket_key: string
  code: string
  message: string
}

interface UseWorkshopBatchExceptionReadonlyOptions {
  currentRouteLabel: ComputedRef<string>
  routeTab: ComputedRef<string>
  routeParity: ComputedRef<string>
  canBatch: ComputedRef<boolean>
  previewRows: ComputedRef<WorkshopBatchPreviewRowInput[]>
  validationRows: ComputedRef<WorkshopBatchValidationRowInput[]>
}

const toTone = (value: string): WorkshopBatchExceptionTone => {
  if (value.includes('preview') || value.includes('ready')) return 'success'
  if (value.includes('blocked') || value.includes('failed')) return 'warning'
  if (value.includes('missing') || value.includes('invalid')) return 'danger'
  return 'info'
}

export const useWorkshopBatchExceptionReadonly = ({
  currentRouteLabel,
  routeTab,
  routeParity,
  canBatch,
  previewRows,
  validationRows,
}: UseWorkshopBatchExceptionReadonlyOptions) => {
  const isExceptionGuardTab = computed<boolean>(() => routeTab.value === 'exception-guard')
  const parityMode = computed<string>(() =>
    routeParity.value === 'production-order' ? 'production-order linked' : 'workshop-local',
  )

  const sourceStatus = computed<string>(() => {
    if (validationRows.value.length > 0) return 'validation-blocked'
    if (previewRows.value.length > 0) return 'preview-ready'
    return 'await-local-parse'
  })

  const blockedReasons = computed<string[]>(() => {
    const reasons = [...workshopBatchExceptionFallbackBlockedReasons]
    if (!canBatch.value) {
      reasons.unshift('当前账号无 batch submit 权限；页面仅保留只读异常核对。')
    }
    if (validationRows.value.length > 0) {
      reasons.unshift(`当前解析结果包含 ${validationRows.value.length} 条异常记录，批量提交与同步保持锁定。`)
    } else {
      reasons.unshift('当前尚未形成真实写请求上下文；batch exception guard 仅展示本地 readback。')
    }
    return reasons
  })

  const readonlyGuardText = computed<string>(() => {
    const reasons = [
      'batch submit、job-card sync、failed retry 与 export 仅保留 disabled UI',
      'outbox、worker、ERPNext 与 production write path 继续关闭',
    ]
    if (routeParity.value === 'production-order') {
      reasons.unshift('production/productOrder alias 仅用于 production-order parity 只读核对，不放开真实联动。')
    }
    return reasons.join('；')
  })

  const summaryCards = computed<WorkshopBatchExceptionSummaryCard[]>(() => [
    {
      key: 'query-state',
      label: 'query state',
      value: isExceptionGuardTab.value ? 'exception-guard active' : 'batch default',
      hint: currentRouteLabel.value,
      tone: isExceptionGuardTab.value ? 'success' : 'info',
    },
    {
      key: 'parity',
      label: 'production-order parity',
      value: parityMode.value,
      hint: routeParity.value === 'production-order' ? 'production/productOrder alias' : 'workshop batch direct route',
      tone: routeParity.value === 'production-order' ? 'success' : 'info',
    },
    {
      key: 'exception-items',
      label: 'exception items',
      value: String(validationRows.value.length || previewRows.value.length),
      hint: validationRows.value.length > 0 ? 'invalid rows retained in readonly guard' : 'preview rows retained in readonly guard',
      tone: validationRows.value.length > 0 ? 'warning' : previewRows.value.length > 0 ? 'success' : 'info',
    },
    {
      key: 'source-status',
      label: 'source status',
      value: sourceStatus.value,
      hint: canBatch.value ? 'page permission visible, write path still locked' : 'permission-limited readonly boundary',
      tone: toTone(sourceStatus.value),
    },
  ])

  const parityLines = computed<WorkshopBatchExceptionLineItem[]>(() => [
    {
      key: 'route',
      label: 'route',
      value: currentRouteLabel.value,
      tone: 'info',
    },
    {
      key: 'readonly-scope',
      label: 'readonly scope',
      value: 'workshop batch exception guard',
      tone: isExceptionGuardTab.value ? 'warning' : 'info',
    },
    {
      key: 'parity',
      label: 'parity',
      value: parityMode.value,
      tone: routeParity.value === 'production-order' ? 'success' : 'info',
    },
    {
      key: 'write-boundary',
      label: 'write boundary',
      value: 'batch-submit/sync/export locked',
      tone: 'warning',
    },
  ])

  const exceptionItems = computed<WorkshopBatchExceptionEntry[]>(() => {
    if (validationRows.value.length > 0) {
      return validationRows.value.slice(0, 4).map((row) => ({
        key: `${row.row_index}-${row.ticket_key}`,
        title: `${row.ticket_key} / row ${row.row_index}`,
        owner: routeParity.value === 'production-order' ? 'production-order' : 'workshop-batch',
        source: row.code,
        status: 'validation blocked',
        tone: 'warning',
        summary: row.message,
        details: [
          `row_index=${row.row_index}`,
          `ticket_key=${row.ticket_key}`,
          'batch submit、sync、failed retry 与 export 均保持只读锁定。',
        ],
      }))
    }
    if (previewRows.value.length > 0) {
      return previewRows.value.slice(0, 4).map((row) => ({
        key: `${row.row_index}-${row.ticket_key}`,
        title: `${row.ticket_key} / ${row.job_card}`,
        owner: routeParity.value === 'production-order' ? 'production-order' : 'workshop-batch',
        source: row.operation_type,
        status: 'preview ready',
        tone: 'success',
        summary: `${row.employee} / qty=${row.qty}`,
        details: [
          `row_index=${row.row_index}`,
          `operation_type=${row.operation_type}`,
          '当前仅允许只读预览，不触发真实 batch submit 或 sync。',
        ],
      }))
    }
    return [
      {
        key: 'fallback-row-1',
        title: 'template row / row 1',
        owner: routeParity.value === 'production-order' ? 'production-order' : 'workshop-batch',
        source: 'await-local-parse',
        status: 'await local parse',
        tone: 'info',
        summary: '尚未解析批量数据；异常项视图先保留只读骨架。',
        details: [
          'query-state 与 parity 已可见',
          '真实 batch submit / sync / export 仍保持锁定',
        ],
      },
    ]
  })

  const remainingGap = computed<string>(() => {
    if (validationRows.value.length > 0) {
      return 'remaining_gap: 当前仅提供 batch exception readonly guard；真实 batch submit、job-card sync、failed retry、export 与 backend remediation 仍未开放。'
    }
    return 'remaining_gap: 当前仅提供 batch exception readonly summary；待解析数据仅用于本地预览，真实 batch submit、sync 与 export 仍未开放。'
  })

  return {
    isExceptionGuardTab,
    summaryCards,
    parityLines,
    blockedReasons,
    readonlyGuardText,
    exceptionItems,
    disabledActions: workshopBatchExceptionDisabledActions,
    remainingGap,
  }
}
