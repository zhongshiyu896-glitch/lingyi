export type ProductionPlanStatusTagType = 'success' | 'warning' | 'danger' | 'info'

export interface ProductionReadonlyGuardAction {
  label: string
  reason: string
}

import type {
  ProductionFollowupTemplateListItem,
  ProductionPlanDetailData,
} from '@/api/production'
import {
  PRODUCTION_FOLLOWUP_PARITY_SCOPE_LABELS,
  PRODUCTION_FOLLOWUP_REMAINING_GAPS,
  type ProductionFollowupTagType,
} from '@/views/production/constants/productionFollowupFields'

export interface ProductionPlanReadbackRowLike {
  planNo: string
  statusCode: string
  progress: string
  workOrderStatus: string
  group: string
  source: 'backend' | 'synthetic'
}

export interface ProductionFollowupReadonlySummary {
  parityScopeLabel: string
  sourceLabel: string
  templateStatusLabel: string
  templateStatusTone: ProductionFollowupTagType
  sampleParityLabel: string
  sampleParityTone: ProductionFollowupTagType
  progressExceptionLabel: string
  progressExceptionTone: ProductionFollowupTagType
  readonlyGuardReason: string
  remainingGap: string
  templateCount: number
  sampleProcessCount: number
  exceptionCount: number
  progressSnapshot: string
}

const STATUS_LABELS: Record<string, string> = {
  draft: '草稿',
  planned: '已计划',
  material_checked: '已物料检查',
  work_order_pending: '工单待同步',
  work_order_created: '已创建工单',
  job_cards_synced: '工序卡已同步',
  cancelled: '已取消',
  failed: '失败',
  pending: '待同步',
  processing: '同步中',
  succeeded: '已同步',
  dead: '死信',
  blocked_scope: '范围阻断',
}

const STATUS_PROGRESS: Record<string, string> = {
  planned: '0%',
  material_checked: '35%',
  work_order_pending: '68%',
  work_order_created: '85%',
  job_cards_synced: '100%',
  cancelled: '0%',
  failed: '0%',
}

const PARITY_ROUTE_LABELS: Record<string, string> = {
  '': '主入口只读',
  'sample-list': '样衣计划镜像',
  'production-order': '订单计划镜像',
  'production-followup-template': '生产跟进镜像',
}

const READONLY_GUARD_ACTIONS: ProductionReadonlyGuardAction[] = [
  { label: '工单下发', reason: 'production write 冻结' },
  { label: '创建工单', reason: 'readonly guard' },
  { label: '同步工序卡', reason: 'outbox/worker 冻结' },
  { label: 'ERP 推送', reason: 'ERPNext production 冻结' },
]

const ACTIVE_TEMPLATE_STATUSES = new Set(['active', 'enabled', 'submitted', 'in_use'])

const normalizeProgressRatio = (completed: number, total: number): string => {
  if (total <= 0) return '暂无进度快照'
  return `${completed}/${total} 条工序已同步`
}

const parseTemplateSourceLabel = (rows: ProductionPlanReadbackRowLike[]): string => {
  const syntheticCount = rows.filter((row) => row.source === 'synthetic').length
  const backendCount = rows.length - syntheticCount
  return `backend ${backendCount} / synthetic ${syntheticCount}`
}

const isSampleTemplate = (template: ProductionFollowupTemplateListItem): boolean =>
  `${template.template_type} ${template.template_name} ${template.trigger_node}`.toLowerCase().includes('sample') ||
  `${template.template_type} ${template.template_name} ${template.trigger_node}`.includes('样衣')

const summarizeTemplates = (
  templates: ProductionFollowupTemplateListItem[],
): {
  templateStatusLabel: string
  templateStatusTone: ProductionFollowupTagType
  templateCount: number
  activeCount: number
  sampleCount: number
} => {
  const activeCount = templates.filter((template) => ACTIVE_TEMPLATE_STATUSES.has(template.status.toLowerCase())).length
  const sampleCount = templates.filter(isSampleTemplate).length
  if (templates.length === 0) {
    return {
      templateStatusLabel: '未读取到模板快照',
      templateStatusTone: 'warning',
      templateCount: 0,
      activeCount: 0,
      sampleCount: 0,
    }
  }
  if (activeCount < templates.length) {
    return {
      templateStatusLabel: `${activeCount}/${templates.length} 条模板可用`,
      templateStatusTone: 'warning',
      templateCount: templates.length,
      activeCount,
      sampleCount,
    }
  }
  return {
    templateStatusLabel: `${templates.length} 条模板可用`,
    templateStatusTone: 'success',
    templateCount: templates.length,
    activeCount,
    sampleCount,
  }
}

const sampleParitySummary = (
  parity: string,
  sampleCount: number,
): { label: string; tone: ProductionFollowupTagType; metricCount: number } => {
  if (parity === 'sample-list') {
    return {
      label: sampleCount > 0 ? '样衣流程 parity 已对齐' : '样衣流程 parity 仅保留只读入口',
      tone: sampleCount > 0 ? 'success' : 'warning',
      metricCount: Math.max(sampleCount, 1),
    }
  }
  if (sampleCount > 0) {
    return {
      label: `检测到 ${sampleCount} 条样衣模板`,
      tone: 'info',
      metricCount: sampleCount,
    }
  }
  return {
    label: '未命中样衣 parity',
    tone: 'info',
    metricCount: 0,
  }
}

const progressStatusSummary = (
  exceptionCount: number,
  progressSnapshot: string,
): { label: string; tone: ProductionFollowupTagType } => {
  if (exceptionCount > 0) {
    return {
      label: `${exceptionCount} 条进度/异常待核对`,
      tone: 'warning',
    }
  }
  if (progressSnapshot !== '暂无进度快照') {
    return {
      label: '进度快照已回读',
      tone: 'success',
    }
  }
  return {
    label: '暂无进度快照',
    tone: 'info',
  }
}

export const useProductionPlanReadback = () => {
  const parseQueryString = (value: unknown): string => {
    const raw = Array.isArray(value) ? value[0] : value
    return typeof raw === 'string' ? raw.trim() : ''
  }

  const parityRouteLabel = (parity: string): string => PARITY_ROUTE_LABELS[parity] || '本地计划组'

  const groupLabel = (parity: string, company: string): string => {
    if (parity && PARITY_ROUTE_LABELS[parity]) return PARITY_ROUTE_LABELS[parity]
    return company === 'LY-LOCAL-TEST' ? '本地计划组' : company
  }

  const statusLabel = (status: string): string => STATUS_LABELS[status] || status

  const progressLabel = (status: string): string => STATUS_PROGRESS[status] || '0%'

  const statusType = (status: string): ProductionPlanStatusTagType => {
    if (status === 'work_order_created' || status === 'job_cards_synced') return 'success'
    if (status === 'failed') return 'danger'
    if (status === 'planned' || status === 'material_checked' || status === 'work_order_pending') return 'warning'
    return 'info'
  }

  const buildProductionFollowupListSummary = (params: {
    parity: string
    rows: ProductionPlanReadbackRowLike[]
    templates: ProductionFollowupTemplateListItem[]
  }): ProductionFollowupReadonlySummary => {
    const templateSummary = summarizeTemplates(params.templates)
    const sampleSummary = sampleParitySummary(params.parity, templateSummary.sampleCount)
    const exceptionCount = params.rows.filter((row) =>
      ['failed', 'work_order_pending'].includes(row.statusCode) ||
      ['failed', 'dead', 'pending'].includes(row.workOrderStatus),
    ).length
    const progressSnapshot =
      params.rows.length > 0
        ? `${params.rows.slice(0, 3).map((row) => `${row.planNo}:${row.progress}`).join(' / ')}${params.rows.length > 3 ? ' ...' : ''}`
        : '暂无进度快照'
    const progressSummary = progressStatusSummary(exceptionCount, progressSnapshot)
    return {
      parityScopeLabel: PRODUCTION_FOLLOWUP_PARITY_SCOPE_LABELS[params.parity] || parityRouteLabel(params.parity),
      sourceLabel: parseTemplateSourceLabel(params.rows),
      templateStatusLabel: templateSummary.templateStatusLabel,
      templateStatusTone: templateSummary.templateStatusTone,
      sampleParityLabel: sampleSummary.label,
      sampleParityTone: sampleSummary.tone,
      progressExceptionLabel: progressSummary.label,
      progressExceptionTone: progressSummary.tone,
      readonlyGuardReason:
        '当前切片仅开放生产跟进模板与样衣流程只读回读；工单下发、生产状态变更、job-card sync、outbox、worker 与 ERPNext production 均保持冻结。',
      remainingGap: PRODUCTION_FOLLOWUP_REMAINING_GAPS.join('；'),
      templateCount: templateSummary.templateCount,
      sampleProcessCount: sampleSummary.metricCount,
      exceptionCount,
      progressSnapshot,
    }
  }

  const buildProductionFollowupDetailSummary = (params: {
    parity: string
    detail: ProductionPlanDetailData
    templates: ProductionFollowupTemplateListItem[]
  }): ProductionFollowupReadonlySummary => {
    const templateSummary = summarizeTemplates(params.templates)
    const sampleSummary = sampleParitySummary(params.parity, templateSummary.sampleCount)
    const laggingJobCardCount = params.detail.job_cards.filter((item) => Number(item.completed_qty || 0) < Number(item.expected_qty || 0)).length
    const shortageCount = params.detail.material_snapshots.filter((item) => Number(item.shortage_qty || 0) > 0).length
    const syncBlocked = ['failed', 'dead', 'blocked_scope'].includes(params.detail.sync_status || '') ? 1 : 0
    const exceptionCount = laggingJobCardCount + shortageCount + syncBlocked
    const totalJobCards = params.detail.job_cards.length
    const syncedJobCards = params.detail.job_cards.filter((item) => Number(item.completed_qty || 0) >= Number(item.expected_qty || 0)).length
    const progressSnapshot =
      totalJobCards > 0
        ? normalizeProgressRatio(syncedJobCards, totalJobCards)
        : `${statusLabel(params.detail.status)} / 暂无工序卡快照`
    const progressSummary = progressStatusSummary(exceptionCount, progressSnapshot)
    return {
      parityScopeLabel: PRODUCTION_FOLLOWUP_PARITY_SCOPE_LABELS[params.parity] || parityRouteLabel(params.parity),
      sourceLabel: `${params.detail.plan_no} / ${params.detail.item_code}`,
      templateStatusLabel: templateSummary.templateStatusLabel,
      templateStatusTone: templateSummary.templateStatusTone,
      sampleParityLabel: sampleSummary.label,
      sampleParityTone: sampleSummary.tone,
      progressExceptionLabel: progressSummary.label,
      progressExceptionTone: progressSummary.tone,
      readonlyGuardReason:
        '当前详情页仅开放生产跟进模板、样衣流程 parity 和工序/异常快照只读核对；生产派工、状态变更、job-card sync、outbox、worker 与 ERPNext production 均未开放。',
      remainingGap: PRODUCTION_FOLLOWUP_REMAINING_GAPS.join('；'),
      templateCount: templateSummary.templateCount,
      sampleProcessCount: sampleSummary.metricCount,
      exceptionCount,
      progressSnapshot,
    }
  }

  return {
    buildProductionFollowupDetailSummary,
    buildProductionFollowupListSummary,
    groupLabel,
    parseQueryString,
    parityRouteLabel,
    progressLabel,
    readonlyGuardActions: READONLY_GUARD_ACTIONS,
    statusLabel,
    statusType,
  }
}
