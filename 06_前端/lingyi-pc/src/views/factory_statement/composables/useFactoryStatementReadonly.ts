import { computed, unref, type MaybeRef } from 'vue'
import type { FactoryStatementReadonlyRecord } from '@/api/factory_statement_readonly'

type TagType = 'warning' | 'success' | 'danger' | 'info'

const ACTIVE_PAYABLE_OUTBOX_STATUS = new Set(['pending', 'processing', 'succeeded'])

const FALLBACK_TEXT = '-'

const showText = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return FALLBACK_TEXT
  }
  return String(value)
}

export const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return FALLBACK_TEXT
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

export const formatRate = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return FALLBACK_TEXT
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? `${(numeric * 100).toFixed(2)}%` : String(value)
}

export const statementStatusLabel = (status: string | null | undefined): string => {
  if (status === 'draft') return '草稿'
  if (status === 'confirmed') return '已确认'
  if (status === 'cancelled') return '已取消'
  if (status === 'payable_draft_created') return '应付草稿已生成'
  return status || FALLBACK_TEXT
}

export const outboxStatusLabel = (status: string | null | undefined): string => {
  if (status === 'pending') return '待同步'
  if (status === 'processing') return '同步中'
  if (status === 'succeeded') return '已生成草稿'
  if (status === 'failed') return '同步失败'
  if (status === 'dead') return '同步死信'
  if (status === '__unknown__') return '摘要缺失'
  return status || FALLBACK_TEXT
}

export const statusTag = (status: string | null | undefined): TagType => {
  if (status === 'draft') return 'warning'
  if (status === 'confirmed') return 'success'
  if (status === 'cancelled') return 'danger'
  return 'info'
}

export const useFactoryStatementReadonly = (recordSource: MaybeRef<FactoryStatementReadonlyRecord | null>) => {
  const record = computed(() => unref(recordSource))
  const detail = computed(() => record.value?.raw || null)

  const hasPayableSummary = computed<boolean>(
    () => detail.value?.payable_outbox_status !== undefined && detail.value?.purchase_invoice_name !== undefined,
  )

  const summaryMissing = computed<boolean>(() => Boolean(detail.value) && !hasPayableSummary.value)

  const effectiveOutboxStatus = computed<string>(() => {
    if (!hasPayableSummary.value) {
      return '__unknown__'
    }
    return detail.value?.payable_outbox_status || ''
  })

  const hasActivePayableOutbox = computed<boolean>(() => (
    !hasPayableSummary.value || ACTIVE_PAYABLE_OUTBOX_STATUS.has(effectiveOutboxStatus.value)
  ))

  const detailKpis = computed(() => ({
    itemCount: record.value?.settlementSummary.itemCount || 0,
    logCount: record.value?.settlementSummary.logCount || 0,
    rejectedRate: formatRate(record.value?.amountSummary.rejectedRate),
    payableSyncState: hasActivePayableOutbox.value ? '同步中/待同步' : '已闭合',
  }))

  const detailGuardMessage = computed(() => {
    const reasons = ['当前页面仅提供只读详情回读']
    if (summaryMissing.value) {
      reasons.push('应付摘要缺失，按 fail-closed 策略禁用确认/取消/应付出账')
    }
    if (hasActivePayableOutbox.value) {
      reasons.push(`当前应付同步状态为 ${outboxStatusLabel(effectiveOutboxStatus.value)}，继续禁用打印、导出与应付动作`)
    }
    return reasons.join('；')
  })

  const printGuardMessage = computed(() => {
    const reasons = ['当前页面为只读打印预览']
    if (summaryMissing.value) {
      reasons.push('摘要缺失时不允许触发打印提交或导出')
    }
    reasons.push('确认、取消、导出、应付出账保持禁用')
    return reasons.join('；')
  })

  const settlementSummary = computed(() => ({
    periodText: record.value?.settlementSummary.periodText || FALLBACK_TEXT,
    sourceCount: record.value?.settlementSummary.sourceCount || 0,
    itemCount: record.value?.settlementSummary.itemCount || 0,
    logCount: record.value?.settlementSummary.logCount || 0,
    primarySubcontractNo: record.value?.settlementSummary.primarySubcontractNo || FALLBACK_TEXT,
    primaryInspectionNo: record.value?.settlementSummary.primaryInspectionNo || FALLBACK_TEXT,
    purchaseInvoiceName: record.value?.settlementSummary.purchaseInvoiceName || FALLBACK_TEXT,
    payableOutboxCount: record.value?.settlementSummary.payableOutboxCount || 0,
    payableErrorCode: record.value?.settlementSummary.payableErrorCode || FALLBACK_TEXT,
    payableErrorMessage: record.value?.settlementSummary.payableErrorMessage || FALLBACK_TEXT,
  }))

  const auditSummary = computed(() => ({
    createdBy: record.value?.auditSummary.createdBy || FALLBACK_TEXT,
    createdAt: record.value?.auditSummary.createdAt || FALLBACK_TEXT,
    latestAction: record.value?.auditSummary.latestAction || FALLBACK_TEXT,
    latestOperator: record.value?.auditSummary.latestOperator || FALLBACK_TEXT,
    latestOperatedAt: record.value?.auditSummary.latestOperatedAt || FALLBACK_TEXT,
    latestRemark: record.value?.auditSummary.latestRemark || FALLBACK_TEXT,
  }))

  const printSummary = computed(() => ({
    payableInvoice: settlementSummary.value.purchaseInvoiceName,
    primarySubcontractNo: settlementSummary.value.primarySubcontractNo,
    primaryInspectionNo: settlementSummary.value.primaryInspectionNo,
    createdBy: auditSummary.value.createdBy,
    latestAction: auditSummary.value.latestAction,
    latestOperatedAt: auditSummary.value.latestOperatedAt,
  }))

  return {
    auditSummary,
    detailGuardMessage,
    detailKpis,
    effectiveOutboxStatus,
    formatAmount,
    formatRate,
    hasActivePayableOutbox,
    outboxStatusLabel,
    printGuardMessage,
    printSummary,
    settlementSummary,
    showText,
    statementStatusLabel,
    statusTag,
    summaryMissing,
  }
}
