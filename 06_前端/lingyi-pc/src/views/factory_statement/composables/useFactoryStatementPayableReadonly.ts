import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type { FactoryStatementReadonlyRecord } from '@/api/factory_statement_readonly'
import {
  FACTORY_STATEMENT_PAYABLE_GUARD_ACTIONS,
  FACTORY_STATEMENT_PAYABLE_GUARD_LABEL,
  FACTORY_STATEMENT_PAYABLE_REMAINING_GAP,
  FACTORY_STATEMENT_PAYABLE_SCOPE_LABELS,
  FACTORY_STATEMENT_PAYABLE_STATE_LABELS,
  FACTORY_STATEMENT_PAYABLE_STATE_TAGS,
  FACTORY_STATEMENT_PAYABLE_WRITE_BOUNDARY,
  type FactoryStatementPayableGuardAction,
  type FactoryStatementPayableReadonlyState,
  type FactoryStatementPayableReadonlyTagType,
} from '@/views/factory_statement/constants/factoryStatementPayableFields'

const ACTIVE_PAYABLE_OUTBOX_STATUS = new Set(['pending', 'processing', 'succeeded'])
const FALLBACK_TEXT = '-'

export interface FactoryStatementPayableReadonlySummary {
  sourceLabel: string
  parityScopeLabel: string
  parityLabel: string
  parityTone: FactoryStatementPayableReadonlyTagType
  queryStateLabel: string
  focusLabel: string
  sourceStatusLabel: string
  payableItemStatusLabel: string
  payableStatusLabel: string
  payableStatusTone: FactoryStatementPayableReadonlyTagType
  payableBlockedLabel: string
  payableBlockedTone: FactoryStatementPayableReadonlyTagType
  payableInvoiceLabel: string
  latestOutboxStatusLabel: string
  payableOutboxCountLabel: string
  payableErrorLabel: string
  sourceGapPrompt: string
  readonlyGuardReason: string
  remainingGap: string
  retainedCand116: boolean
  writeBoundary: string
  routeItems: Array<{
    key: string
    label: string
    route: string
    note: string
    active: boolean
  }>
  guardActions: ReadonlyArray<FactoryStatementPayableGuardAction>
}

interface UseFactoryStatementPayableReadonlyOptions {
  recordSource: MaybeRef<FactoryStatementReadonlyRecord | null>
  parity: MaybeRef<string>
  context: 'detail' | 'print'
  tab?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
}

const showText = (value: unknown): string => {
  if (value === null || value === undefined || value === '') {
    return FALLBACK_TEXT
  }
  return String(value)
}

const resolveOutboxStatusLabel = (status: string | null | undefined): string => {
  if (status === 'pending') return '待同步'
  if (status === 'processing') return '同步中'
  if (status === 'succeeded') return '已生成草稿'
  if (status === 'failed') return '同步失败'
  if (status === 'dead') return '同步死信'
  if (status === '__unknown__') return '摘要缺失'
  return status || FALLBACK_TEXT
}

const pickLatestOutbox = (record: FactoryStatementReadonlyRecord | null) => {
  const rows = record?.raw.payable_outboxes || []
  if (rows.length === 0) return null
  return rows.slice(1).reduce((latest, current) => {
    const latestTime = Date.parse(latest.updated_at || latest.created_at)
    const currentTime = Date.parse(current.updated_at || current.created_at)
    if (!Number.isNaN(latestTime) && !Number.isNaN(currentTime)) {
      return currentTime > latestTime ? current : latest
    }
    return (current.updated_at || current.created_at) > (latest.updated_at || latest.created_at) ? current : latest
  }, rows[0])
}

const resolvePayableState = (
  record: FactoryStatementReadonlyRecord | null,
  hasSummary: boolean,
): FactoryStatementPayableReadonlyState => {
  if (!record || !record.raw) return 'summary-missing'
  if (!hasSummary) return 'summary-missing'
  if (record.raw.purchase_invoice_name) return 'invoice-created'
  if (record.raw.payable_error_code || record.raw.payable_error_message) return 'failed-sync'
  if (ACTIVE_PAYABLE_OUTBOX_STATUS.has(record.raw.payable_outbox_status || '')) return 'active-sync'
  if ((record.raw.payable_outboxes || []).some((row) => row.status === 'failed' || row.status === 'dead')) return 'failed-sync'
  return 'no-payable'
}

const resolveSourceGapPrompt = (
  state: FactoryStatementPayableReadonlyState,
  parity: string,
  context: 'detail' | 'print',
): string => {
  if (state === 'summary-missing') {
    return '应付摘要缺失，当前仅保留详情/打印基础回读，payable 状态按 fail-closed 策略只读回退。'
  }
  if (parity === 'foundation-factory') {
    return 'foundation-factory parity 仅回读 payable 状态与打印镜像，不开放真实结算写入。'
  }
  if (state === 'invoice-created') {
    return '已生成 ERPNext 发票草稿镜像，仅回读单号与同步状态，不开放真实应付出账。'
  }
  if (state === 'active-sync') {
    return '当前存在 payable outbox 流程，仅提供只读跟踪与阻断提示。'
  }
  if (state === 'failed-sync') {
    return '已保留 payable 错误快照用于只读排障，不开放重试或人工写入。'
  }
  return context === 'print'
    ? '打印镜像仅回读 payable 状态，不开放真实打印提交与导出。'
    : '详情页仅回读 payable 状态，不开放结算写入与导出。'
}

const resolveSourceStatusLabel = (
  record: FactoryStatementReadonlyRecord | null,
  parity: string,
  focus: string,
): string => {
  const detail = record?.raw
  if (!detail) {
    return '来源镜像缺失 / 等待只读回补'
  }
  if (focus === 'settlement-source') {
    return `settlement-source / ${showText(record?.settlementSummary.primarySubcontractNo || detail.supplier)}`
  }
  if (parity === 'foundation-factory') {
    return `foundation-factory / ${showText(detail.supplier)}`
  }
  return `detail-readonly / ${showText(detail.statement_no)}`
}

const resolvePayableItemStatusLabel = (
  record: FactoryStatementReadonlyRecord | null,
  state: FactoryStatementPayableReadonlyState,
): string => {
  const itemCount = record?.items?.length || 0
  return `${itemCount} 行 / ${FACTORY_STATEMENT_PAYABLE_STATE_LABELS[state]}`
}

export const useFactoryStatementPayableReadonly = ({
  recordSource,
  parity,
  context,
  tab,
  focus,
}: UseFactoryStatementPayableReadonlyOptions): { payableReadonlySummary: ComputedRef<FactoryStatementPayableReadonlySummary> } => {
  const record = computed(() => unref(recordSource))
  const parityValue = computed(() => String(unref(parity) || '').trim().toLowerCase())
  const tabValue = computed(() => String(unref(tab) || '').trim().toLowerCase())
  const focusValue = computed(() => String(unref(focus) || '').trim().toLowerCase())

  const payableReadonlySummary = computed<FactoryStatementPayableReadonlySummary>(() => {
    const currentRecord = record.value
    const currentDetail = currentRecord?.raw || null
    const hasSummary = currentDetail?.payable_outbox_status !== undefined && currentDetail?.purchase_invoice_name !== undefined
    const latestOutbox = pickLatestOutbox(currentRecord)
    const state = resolvePayableState(currentRecord, hasSummary)
    const latestOutboxStatus = showText(
      currentDetail?.payable_outbox_status || latestOutbox?.status || (hasSummary ? '' : '__unknown__'),
    )
    const payableErrorLabel = showText(
      currentDetail?.payable_error_code ||
        currentDetail?.payable_error_message ||
        latestOutbox?.last_error_code ||
        latestOutbox?.last_error_message,
    )
    return {
      sourceLabel: context === 'print' ? '打印镜像只读扩展' : '详情只读扩展',
      parityScopeLabel:
        FACTORY_STATEMENT_PAYABLE_SCOPE_LABELS[parityValue.value] || FACTORY_STATEMENT_PAYABLE_SCOPE_LABELS[''],
      parityLabel: parityValue.value === 'foundation-factory' ? 'foundation-factory parity' : '主入口只读',
      parityTone: parityValue.value === 'foundation-factory' ? 'warning' : 'info',
      queryStateLabel: context === 'print'
        ? 'print-readonly'
        : (tabValue.value === 'payable-readonly' ? 'payable-readonly' : 'detail-readonly'),
      focusLabel: focusValue.value === 'settlement-source' ? 'settlement-source' : 'settlement-summary',
      sourceStatusLabel: resolveSourceStatusLabel(currentRecord, parityValue.value, focusValue.value),
      payableItemStatusLabel: resolvePayableItemStatusLabel(currentRecord, state),
      payableStatusLabel: FACTORY_STATEMENT_PAYABLE_STATE_LABELS[state],
      payableStatusTone: FACTORY_STATEMENT_PAYABLE_STATE_TAGS[state],
      payableBlockedLabel: 'payable readonly guard',
      payableBlockedTone: state === 'summary-missing' || state === 'failed-sync' ? 'danger' : 'warning',
      payableInvoiceLabel: showText(currentDetail?.purchase_invoice_name),
      latestOutboxStatusLabel: resolveOutboxStatusLabel(latestOutboxStatus),
      payableOutboxCountLabel: String(currentDetail?.payable_outboxes?.length || 0),
      payableErrorLabel,
      sourceGapPrompt: resolveSourceGapPrompt(state, parityValue.value, context),
      readonlyGuardReason: FACTORY_STATEMENT_PAYABLE_GUARD_LABEL,
      remainingGap: FACTORY_STATEMENT_PAYABLE_REMAINING_GAP,
      retainedCand116: true,
      writeBoundary: FACTORY_STATEMENT_PAYABLE_WRITE_BOUNDARY,
      routeItems: context === 'detail'
        ? [
            {
              key: 'detail',
              label: '详情入口',
              route: '/factory-statements/detail',
              note: '默认只读详情回补入口',
              active: !tabValue.value && !parityValue.value && !focusValue.value,
            },
            {
              key: 'payable-readonly',
              label: 'payable 查询态',
              route: '/factory-statements/detail?tab=payable-readonly&parity=foundation-factory',
              note: 'foundation-factory parity',
              active: tabValue.value === 'payable-readonly' || parityValue.value === 'foundation-factory',
            },
            {
              key: 'settlement-source',
              label: 'focus 来源态',
              route: '/factory-statements/detail?tab=payable-readonly&parity=foundation-factory&focus=settlement-source',
              note: 'settlement-source focus',
              active: focusValue.value === 'settlement-source',
            },
          ]
        : [],
      guardActions: FACTORY_STATEMENT_PAYABLE_GUARD_ACTIONS,
    }
  })

  return {
    payableReadonlySummary,
  }
}
