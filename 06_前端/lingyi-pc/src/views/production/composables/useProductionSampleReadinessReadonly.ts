import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  ProductionFollowupTemplateListItem,
  ProductionPlanDetailData,
} from '@/api/production'
import {
  PRODUCTION_SAMPLE_READINESS_DISABLED_ACTIONS,
  PRODUCTION_SAMPLE_READINESS_FIELDS,
  PRODUCTION_SAMPLE_READINESS_FOCUS_LABEL,
  PRODUCTION_SAMPLE_READINESS_PARITY_LABEL,
  PRODUCTION_SAMPLE_READINESS_READONLY_GUARD_REASON,
  PRODUCTION_SAMPLE_READINESS_REMAINING_GAP,
  PRODUCTION_SAMPLE_READINESS_WRITE_BOUNDARY,
  type ProductionSampleReadinessFieldKey,
  type ProductionSampleReadinessTagType,
} from '@/views/production/constants/productionSampleReadinessFields'

const FALLBACK_TEXT = '-'
const BLOCKED_WORK_ORDER_STATUSES = new Set(['pending', 'failed', 'dead', 'blocked_scope'])

export interface ProductionSampleReadinessRowLike {
  planNo: string
  styleCode: string
  statusCode: string
  workOrderStatus: string
  source: 'backend' | 'local_sample'
}

export interface ProductionSampleReadinessReadonlyCard {
  key: ProductionSampleReadinessFieldKey
  label: string
  value: string
}

export interface ProductionSampleReadinessReadonlyAction {
  label: string
  reason: string
}

export interface ProductionSampleReadinessReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface ProductionSampleReadinessReadonlySummary {
  queryStateLabel: string
  parityLabel: string
  parityTone: ProductionSampleReadinessTagType
  focusLabel: string
  focusTone: ProductionSampleReadinessTagType
  readinessStatusLabel: string
  readinessStatusTone: ProductionSampleReadinessTagType
  sourceStatusLabel: string
  sourceStatusTone: ProductionSampleReadinessTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: ProductionSampleReadinessReadonlyCard[]
  disabledActions: ProductionSampleReadinessReadonlyAction[]
  items: ProductionSampleReadinessReadonlyItem[]
}

interface UseProductionSampleReadinessReadonlyOptions {
  rows?: MaybeRef<ProductionSampleReadinessRowLike[]>
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

const isSampleTemplate = (template: ProductionFollowupTemplateListItem): boolean =>
  `${template.template_type} ${template.template_name} ${template.trigger_node}`.toLowerCase().includes('sample') ||
  `${template.template_type} ${template.template_name} ${template.trigger_node}`.includes('样衣')

export const useProductionSampleReadinessReadonly = ({
  rows,
  detail,
  templates,
  tab,
  parity,
  focus,
  lastLoadedAt,
  lastError,
}: UseProductionSampleReadinessReadonlyOptions): {
  sampleReadinessReadonlySummary: ComputedRef<ProductionSampleReadinessReadonlySummary>
} => {
  const sampleReadinessReadonlySummary = computed<ProductionSampleReadinessReadonlySummary>(() => {
    const rowList = unref(rows) || []
    const currentDetail = unref(detail) || null
    const templateList = unref(templates) || []
    const tabValue = normalizeText(unref(tab)) || 'sample-readiness-readonly'
    const parityValue = normalizeText(unref(parity)) || 'sample-list'
    const focusValue = normalizeText(unref(focus)) || 'sample-source'
    const loadedAt = normalizeText(unref(lastLoadedAt)) || FALLBACK_TEXT
    const errorMessage = normalizeText(unref(lastError))

    const sampleTemplateCount = templateList.filter(isSampleTemplate).length
    let recordCount = 0
    let pendingCount = 0
    let blockedCount = 0
    let sourceScopeLabel = FALLBACK_TEXT
    let coverageLabel = '样衣 readiness 待读取'
    let itemStatusLabel = '无可读条目'
    let items: ProductionSampleReadinessReadonlyItem[] = []

    if (currentDetail) {
      recordCount = Math.max(currentDetail.material_snapshots.length, currentDetail.job_cards.length, 1)
      pendingCount = currentDetail.job_cards.filter((item) => toNumber(item.completed_qty) < toNumber(item.expected_qty)).length
      blockedCount =
        currentDetail.material_snapshots.filter((item) => toNumber(item.shortage_qty) > 0).length +
        (BLOCKED_WORK_ORDER_STATUSES.has(normalizeText(currentDetail.sync_status)) ? 1 : 0)
      sourceScopeLabel = currentDetail.plan_no || FALLBACK_TEXT
      coverageLabel = currentDetail.material_snapshots.length > 0 ? '样衣 readiness 快照已回读' : '样衣 readiness 仅保留详情摘要'
      items =
        currentDetail.material_snapshots.length > 0
          ? currentDetail.material_snapshots.slice(0, 6).map((item) => ({
              subjectLabel: item.material_item_code,
              statusLabel: toNumber(item.shortage_qty) > 0 ? '样衣物料待校验' : '样衣物料已对齐',
              sourceLabel: item.checked_at ? `snapshot@${item.checked_at}` : 'snapshot pending',
              blockedReason: toNumber(item.shortage_qty) > 0 ? `缺口 ${item.shortage_qty}` : '仅开放只读核对',
            }))
          : [
              {
                subjectLabel: currentDetail.item_code || currentDetail.plan_no,
                statusLabel: currentDetail.status || FALLBACK_TEXT,
                sourceLabel: currentDetail.latest_work_order_outbox?.status || currentDetail.sync_status || 'detail snapshot',
                blockedReason: currentDetail.write_entry_frozen_reason || '仅开放只读核对',
              },
            ]
      itemStatusLabel = `${items.length} 条条目 / 待同步 ${pendingCount} / 阻断 ${blockedCount}`
    } else if (rowList.length > 0) {
      recordCount = rowList.length
      pendingCount = rowList.filter((row) => row.statusCode !== 'job_cards_synced').length
      blockedCount = rowList.filter((row) => BLOCKED_WORK_ORDER_STATUSES.has(normalizeText(row.workOrderStatus))).length
      sourceScopeLabel = rowList.length === 1 ? rowList[0]?.planNo || FALLBACK_TEXT : `${rowList.length} plans`
      coverageLabel = '样衣入口 readiness 列表已回读'
      items = rowList.slice(0, 6).map((row) => ({
        subjectLabel: `${row.planNo} / ${row.styleCode}`,
        statusLabel: row.statusCode || FALLBACK_TEXT,
        sourceLabel: row.source === 'backend' ? 'list readback' : 'local sample snapshot',
        blockedReason: BLOCKED_WORK_ORDER_STATUSES.has(normalizeText(row.workOrderStatus))
          ? `工单同步 ${row.workOrderStatus || 'pending'}`
          : '仅开放只读核对',
      }))
      itemStatusLabel = `${items.length} 条计划 / 待同步 ${pendingCount} / 阻断 ${blockedCount}`
    }

    const readinessStatusLabel =
      recordCount > 0
        ? sampleTemplateCount > 0
          ? blockedCount > 0
            ? 'sample readiness blocked'
            : 'sample readiness mirrored'
          : pendingCount > 0
            ? 'sample readiness pending'
            : 'sample readiness fallback'
        : 'sample readiness fallback'

    const readinessStatusTone: ProductionSampleReadinessTagType =
      recordCount > 0
        ? blockedCount > 0
          ? 'warning'
          : sampleTemplateCount > 0
            ? 'success'
            : pendingCount > 0
              ? 'info'
              : 'info'
        : 'info'

    const cardValues: Record<ProductionSampleReadinessFieldKey, string> = {
      recordCountLabel: String(recordCount),
      pendingCountLabel: String(pendingCount),
      blockedCountLabel: String(blockedCount),
      sourceScopeLabel,
      coverageLabel,
      refreshLabel: loadedAt,
    }

    const cards: ProductionSampleReadinessReadonlyCard[] = PRODUCTION_SAMPLE_READINESS_FIELDS.map((field) => ({
      key: field.key,
      label: field.label,
      value: cardValues[field.key] || FALLBACK_TEXT,
    }))

    return {
      queryStateLabel: `${tabValue} | parity=${parityValue} | focus=${focusValue}`,
      parityLabel: PRODUCTION_SAMPLE_READINESS_PARITY_LABEL,
      parityTone: parityValue === 'sample-list' ? 'success' : 'warning',
      focusLabel: PRODUCTION_SAMPLE_READINESS_FOCUS_LABEL,
      focusTone: focusValue === 'sample-source' ? 'warning' : 'info',
      readinessStatusLabel,
      readinessStatusTone,
      sourceStatusLabel: recordCount > 0 ? 'sample-source readback ready' : 'sample-source pending',
      sourceStatusTone: recordCount > 0 ? 'success' : 'info',
      itemStatusLabel,
      blockedReason:
        errorMessage ||
        (blockedCount > 0
          ? `检测到 ${blockedCount} 条样衣 readiness 阻断，真实工单 issue/release/sync/export 仍保持冻结。`
          : '当前切片仅开放样衣入口 readiness 只读核对，真实工单 issue/release/sync/export 与跨模块执行保持阻断。'),
      readonlyGuardReason: PRODUCTION_SAMPLE_READINESS_READONLY_GUARD_REASON,
      remainingGap: PRODUCTION_SAMPLE_READINESS_REMAINING_GAP,
      writeBoundary: PRODUCTION_SAMPLE_READINESS_WRITE_BOUNDARY,
      cards,
      disabledActions: PRODUCTION_SAMPLE_READINESS_DISABLED_ACTIONS.map((action) => ({
        label: action.label,
        reason: action.reason,
      })),
      items,
    }
  })

  return {
    sampleReadinessReadonlySummary,
  }
}

export type { ProductionSampleReadinessFieldKey }
export { PRODUCTION_SAMPLE_READINESS_FIELDS }
