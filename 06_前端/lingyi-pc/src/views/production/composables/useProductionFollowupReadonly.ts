import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  ProductionFollowupTemplateListItem,
  ProductionPlanDetailData,
} from '@/api/production'
import type {
  ProductionFollowupReadonlySummary as ProductionFollowupBaseSummary,
  ProductionPlanReadbackRowLike,
} from '@/views/production/composables/useProductionPlanReadback'
import {
  PRODUCTION_FOLLOWUP_DISABLED_ACTIONS,
  PRODUCTION_FOLLOWUP_FOCUS_LABEL,
  PRODUCTION_FOLLOWUP_PARITY_LABEL,
  PRODUCTION_FOLLOWUP_READONLY_FIELDS,
  PRODUCTION_FOLLOWUP_READONLY_GUARD_REASON,
  PRODUCTION_FOLLOWUP_REMAINING_GAPS,
  PRODUCTION_FOLLOWUP_WRITE_BOUNDARY,
  type ProductionFollowupReadonlyFieldKey,
  type ProductionFollowupTagType,
} from '@/views/production/constants/productionFollowupFields'

const FALLBACK_TEXT = '-'
const ACTIVE_TEMPLATE_STATUSES = new Set(['active', 'enabled', 'submitted', 'in_use'])
const BLOCKED_SYNC_STATUSES = new Set(['pending', 'processing', 'failed', 'dead', 'blocked_scope'])

export interface ProductionFollowupReadonlyCard {
  key: ProductionFollowupReadonlyFieldKey
  label: string
  value: string
}

export interface ProductionFollowupReadonlyAction {
  label: string
  reason: string
}

export interface ProductionFollowupReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface ProductionFollowupReadonlySummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: ProductionFollowupTagType
  focusLabel: string
  focusTone: ProductionFollowupTagType
  templateStatusLabel: string
  templateStatusTone: ProductionFollowupTagType
  progressStatusLabel: string
  progressStatusTone: ProductionFollowupTagType
  sourceStatusLabel: string
  sourceStatusTone: ProductionFollowupTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: ProductionFollowupReadonlyCard[]
  disabledActions: ProductionFollowupReadonlyAction[]
  items: ProductionFollowupReadonlyItem[]
}

interface UseProductionFollowupReadonlyOptions {
  baseSummary: MaybeRef<ProductionFollowupBaseSummary | null>
  rows?: MaybeRef<ProductionPlanReadbackRowLike[]>
  detail?: MaybeRef<ProductionPlanDetailData | null>
  templates?: MaybeRef<ProductionFollowupTemplateListItem[]>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  lastLoadedAt?: MaybeRef<string | null | undefined>
  lastError?: MaybeRef<string | null | undefined>
}

const normalizeText = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumber = (value: unknown): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const templateSourceLabel = (template: ProductionFollowupTemplateListItem): string =>
  `${template.template_type || FALLBACK_TEXT} / ${template.trigger_node || FALLBACK_TEXT}`

const templateBlockedReason = (template: ProductionFollowupTemplateListItem): string =>
  ACTIVE_TEMPLATE_STATUSES.has(template.status.toLowerCase())
    ? '仅开放只读模板核对'
    : `模板状态 ${template.status || FALLBACK_TEXT}`

export const useProductionFollowupReadonly = ({
  baseSummary,
  rows,
  detail,
  templates,
  tab,
  parity,
  focus,
  lastLoadedAt,
  lastError,
}: UseProductionFollowupReadonlyOptions): {
  followupReadonlySummary: ComputedRef<ProductionFollowupReadonlySummary>
} => {
  const followupReadonlySummary = computed<ProductionFollowupReadonlySummary>(() => {
    const summary = unref(baseSummary)
    const rowList = unref(rows) || []
    const detailData = unref(detail) || null
    const templateList = unref(templates) || []
    const tabValue = normalizeText(unref(tab)) || 'followup-readonly'
    const parityValue = normalizeText(unref(parity)) || 'production-followup-template'
    const focusValue = normalizeText(unref(focus)) || 'followup-source'
    const loadedAt = normalizeText(unref(lastLoadedAt)) || FALLBACK_TEXT
    const errorMessage = normalizeText(unref(lastError))

    let coverageLabel = '生产跟进模板待读取'
    let sourceScopeLabel = summary?.sourceLabel || FALLBACK_TEXT
    let items: ProductionFollowupReadonlyItem[] = []

    if (templateList.length > 0) {
      coverageLabel = detailData ? '详情跟进模板快照已回读' : '列表跟进模板快照已回读'
      items = templateList.slice(0, 6).map((template) => ({
        subjectLabel: `${template.template_no} / ${template.template_name}`,
        statusLabel: template.status || FALLBACK_TEXT,
        sourceLabel: templateSourceLabel(template),
        blockedReason: templateBlockedReason(template),
      }))
      if (detailData) {
        sourceScopeLabel = `${detailData.plan_no} / ${detailData.item_code}`
      }
    } else if (detailData) {
      coverageLabel = detailData.job_cards.length > 0 ? '详情工序快照已回读' : '详情跟进摘要已回读'
      sourceScopeLabel = `${detailData.plan_no} / ${detailData.item_code}`
      items =
        detailData.job_cards.length > 0
          ? detailData.job_cards.slice(0, 6).map((item) => {
              const expectedQty = toNumber(item.expected_qty)
              const completedQty = toNumber(item.completed_qty)
              return {
                subjectLabel: item.operation || item.job_card || '工序条目',
                statusLabel: completedQty >= expectedQty ? '跟进快照已回读' : '跟进条目待补齐',
                sourceLabel: item.synced_at ? `job-card@${item.synced_at}` : detailData.sync_status || 'detail snapshot',
                blockedReason:
                  completedQty >= expectedQty
                    ? '仅开放只读核对'
                    : `${completedQty}/${expectedQty} 已回读，真实 issue/release 保持冻结`,
              }
            })
          : [
              {
                subjectLabel: detailData.plan_no || detailData.item_code || '详情摘要',
                statusLabel: detailData.status || FALLBACK_TEXT,
                sourceLabel: detailData.sync_status || 'detail snapshot',
                blockedReason: detailData.write_entry_frozen_reason || '仅开放只读核对',
              },
            ]
    } else if (rowList.length > 0) {
      coverageLabel = '列表跟进摘要已回读'
      sourceScopeLabel = rowList.length === 1 ? rowList[0]?.planNo || FALLBACK_TEXT : `${rowList.length} plans`
      items = rowList.slice(0, 6).map((row) => ({
        subjectLabel: `${row.planNo} / ${row.orderNo || FALLBACK_TEXT}`,
        statusLabel: row.statusLabel || row.statusCode || FALLBACK_TEXT,
        sourceLabel: row.source === 'backend' ? 'list readback' : 'synthetic snapshot',
        blockedReason: BLOCKED_SYNC_STATUSES.has(normalizeText(row.workOrderStatus))
          ? `工序同步 ${row.workOrderStatus || 'pending'}`
          : '仅开放只读核对',
      }))
    }

    const cards: ProductionFollowupReadonlyCard[] = PRODUCTION_FOLLOWUP_READONLY_FIELDS.map((field) => {
      const cardValues: Record<ProductionFollowupReadonlyFieldKey, string> = {
        templateCountLabel: String(summary?.templateCount ?? templateList.length),
        sampleProcessCountLabel: String(summary?.sampleProcessCount ?? 0),
        exceptionCountLabel: String(summary?.exceptionCount ?? 0),
        sourceScopeLabel,
        coverageLabel,
        refreshLabel: loadedAt,
      }
      return {
        key: field.key,
        label: field.label,
        value: cardValues[field.key] || FALLBACK_TEXT,
      }
    })

    const itemStatusLabel = `${items.length} 条条目 / 异常 ${summary?.exceptionCount ?? 0} / 模板 ${summary?.templateCount ?? templateList.length}`
    const hasSourceSnapshot = items.length > 0 || Boolean(detailData) || rowList.length > 0
    const blockedReason =
      errorMessage ||
      ((summary?.exceptionCount ?? 0) > 0
        ? `检测到 ${summary?.exceptionCount ?? 0} 条生产跟进阻断；真实工单 issue/release/sync/export、outbox、worker 与 ERPNext production 仍保持冻结。`
        : '当前切片仅开放生产跟进模板 source readonly 核对，真实工单 issue/release/sync/export 与跨模块执行保持阻断。')

    return {
      queryStateLabel: `${tabValue} | parity=${parityValue} | focus=${focusValue}`,
      parityLabel: PRODUCTION_FOLLOWUP_PARITY_LABEL,
      parityTone: parityValue === 'production-followup-template' ? 'success' : 'warning',
      focusLabel: PRODUCTION_FOLLOWUP_FOCUS_LABEL,
      focusTone: focusValue === 'followup-source' ? 'warning' : 'info',
      templateStatusLabel: summary?.templateStatusLabel || '生产跟进模板待回读',
      templateStatusTone: summary?.templateStatusTone || 'info',
      progressStatusLabel: summary?.progressExceptionLabel || '异常快照待回读',
      progressStatusTone: summary?.progressExceptionTone || 'info',
      sourceStatusLabel: hasSourceSnapshot ? 'followup-source readback ready' : 'followup-source pending',
      sourceStatusTone: hasSourceSnapshot ? 'success' : 'info',
      itemStatusLabel,
      blockedReason,
      readonlyGuardReason: summary?.readonlyGuardReason || PRODUCTION_FOLLOWUP_READONLY_GUARD_REASON,
      remainingGap: summary?.remainingGap || PRODUCTION_FOLLOWUP_REMAINING_GAPS.join('；'),
      writeBoundary: PRODUCTION_FOLLOWUP_WRITE_BOUNDARY,
      cards,
      disabledActions: PRODUCTION_FOLLOWUP_DISABLED_ACTIONS.map((action) => ({
        label: action.label,
        reason: action.reason,
      })),
      items,
    }
  })

  return {
    followupReadonlySummary,
  }
}

export type { ProductionFollowupReadonlyFieldKey }
export { PRODUCTION_FOLLOWUP_READONLY_FIELDS }
