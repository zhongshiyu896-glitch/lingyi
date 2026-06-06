import type { ProductionPlanDetailData } from '@/api/production'
import type {
  ProductionPlanReadbackRowLike,
  ProductionPlanStatusTagType,
} from '@/views/production/composables/useProductionPlanReadback'
import {
  PRODUCTION_PROCESS_PROGRESS_REMAINING_GAPS,
  type ProductionProcessProgressTagType,
} from '@/views/production/constants/productionProcessProgressFields'

export interface ProductionProcessProgressReadonlyItem {
  key: string
  subjectLabel: string
  statusLabel: string
  progressLabel: string
  mirrorLabel: string
  blockedReason: string
}

export interface ProductionProcessProgressReadonlySummary {
  parityScopeLabel: string
  sourceLabel: string
  processProgressLabel: string
  processProgressTone: ProductionProcessProgressTagType
  jobCardMirrorLabel: string
  jobCardMirrorTone: ProductionProcessProgressTagType
  blockedReasonLabel: string
  blockedReasonTone: ProductionProcessProgressTagType
  readonlyGuardReason: string
  remainingGap: string
  mirroredJobCardCount: number
  syncPendingCount: number
  blockedCount: number
  statusSnapshot: string
  items: ProductionProcessProgressReadonlyItem[]
}

const BLOCKED_WORK_ORDER_STATUSES = new Set(['', '-', 'pending', 'processing', 'failed', 'dead', 'blocked_scope'])
const PENDING_SYNC_STATUSES = new Set(['pending', 'processing'])

const parseScopeLabel = (parity: string, tab: string, mode = ''): string => {
  if (tab === 'process-progress' && mode === 'readonly-process') return 'process-progress detail readonly'
  if (tab === 'process-progress') return 'production-process parity / process-progress'
  if (parity === 'production-process') return 'production-process parity'
  return '主入口只读'
}

const parseProcessTone = (mirroredCount: number, blockedCount: number): ProductionProcessProgressTagType => {
  if (mirroredCount > 0) return 'success'
  if (blockedCount > 0) return 'warning'
  return 'info'
}

const parseBlockedTone = (blockedCount: number): ProductionProcessProgressTagType =>
  blockedCount > 0 ? 'danger' : 'success'

const listBlockedReason = (row: ProductionPlanReadbackRowLike): string => {
  if (!row.orderNo || row.orderNo === '-') return '缺少生产订单映射'
  if (BLOCKED_WORK_ORDER_STATUSES.has(row.workOrderStatus)) return `工单同步状态=${row.workOrderStatus || '-'}`
  if (['planned', 'material_checked', 'work_order_pending'].includes(row.statusCode)) return `计划状态=${row.statusLabel || row.statusCode}`
  return '写入链路冻结，仅允许只读核对'
}

const detailBlockedReason = (
  status: string,
  operation: string,
  completedQty: number,
  expectedQty: number,
): string => {
  if (completedQty < expectedQty) return `${operation} 完成度不足 ${completedQty}/${expectedQty}`
  if (BLOCKED_WORK_ORDER_STATUSES.has(status)) return `工单同步状态=${status || '-'}`
  return '写入链路冻结，仅允许只读核对'
}

const buildStatusSnapshot = (items: string[]): string => items.filter(Boolean).join(' / ') || '暂无工序状态镜像'

const parseMirrorLabel = (statusCode: string, workOrderStatus: string): string => {
  if (!BLOCKED_WORK_ORDER_STATUSES.has(workOrderStatus)) return `工单同步=${workOrderStatus}`
  if (statusCode === 'job_cards_synced') return '工序卡已同步'
  if (statusCode === 'work_order_created') return '工单已创建待核对'
  return '工序状态待补齐'
}

const parseStatusLabel = (
  mirroredCount: number,
  blockedCount: number,
  subject = '工序状态',
): { label: string; tone: ProductionPlanStatusTagType } => {
  if (mirroredCount > 0) return { label: `${mirroredCount} 条${subject}已镜像`, tone: 'success' }
  if (blockedCount > 0) return { label: `${blockedCount} 条${subject}待补齐`, tone: 'warning' }
  return { label: `暂无${subject}镜像`, tone: 'info' }
}

export const useProductionProcessProgressReadonly = () => {
  const buildProductionProcessProgressListSummary = (params: {
    parity: string
    tab: string
    rows: ProductionPlanReadbackRowLike[]
  }): ProductionProcessProgressReadonlySummary => {
    const mirroredRows = params.rows.filter(
      (row) => row.statusCode === 'job_cards_synced' || !BLOCKED_WORK_ORDER_STATUSES.has(row.workOrderStatus),
    )
    const syncPendingRows = params.rows.filter(
      (row) => PENDING_SYNC_STATUSES.has(row.workOrderStatus) || row.statusCode === 'work_order_pending',
    )
    const blockedRows = params.rows.filter((row) => listBlockedReason(row) !== '写入链路冻结，仅允许只读核对')
    const jobCardMirror = parseStatusLabel(mirroredRows.length, blockedRows.length)
    const processTone = parseProcessTone(mirroredRows.length, blockedRows.length)
    const blockedTone = parseBlockedTone(blockedRows.length)

    return {
      parityScopeLabel: parseScopeLabel(params.parity, params.tab),
      sourceLabel: `${params.rows.length} 条计划 / work-order snapshot`,
      processProgressLabel:
        params.parity === 'production-process' || params.tab === 'process-progress'
          ? mirroredRows.length > 0
            ? 'production-process parity 已命中'
            : 'production-process parity 待补齐'
          : '主入口只读工序进度快照',
      processProgressTone: processTone,
      jobCardMirrorLabel: jobCardMirror.label,
      jobCardMirrorTone: jobCardMirror.tone,
      blockedReasonLabel: blockedRows.length > 0 ? `${blockedRows.length} 条计划存在阻断` : '无新增阻断写入项',
      blockedReasonTone: blockedTone,
      readonlyGuardReason:
        '当前切片仅开放 process-progress 与 job-card 状态镜像只读回读；job-card sync、导出、worker 补偿、ERPNext production 与真实生产写链路均保持冻结。',
      remainingGap: PRODUCTION_PROCESS_PROGRESS_REMAINING_GAPS.join('；'),
      mirroredJobCardCount: mirroredRows.length,
      syncPendingCount: syncPendingRows.length,
      blockedCount: blockedRows.length,
      statusSnapshot: buildStatusSnapshot(
        params.rows.slice(0, 3).map((row) => `${row.planNo}:${row.progress}/${row.workOrderStatus || '-'}`),
      ),
      items: params.rows.slice(0, 4).map((row) => ({
        key: row.planNo,
        subjectLabel: `${row.planNo} / ${row.orderNo || '-'}`,
        statusLabel: row.statusLabel || row.statusCode,
        progressLabel: row.progress,
        mirrorLabel: parseMirrorLabel(row.statusCode, row.workOrderStatus),
        blockedReason: listBlockedReason(row),
      })),
    }
  }

  const buildProductionProcessProgressDetailSummary = (params: {
    parity: string
    tab: string
    mode: string
    detail: ProductionPlanDetailData
  }): ProductionProcessProgressReadonlySummary => {
    const mirroredCards = params.detail.job_cards.filter(
      (item) =>
        Number(item.completed_qty || 0) >= Number(item.expected_qty || 0) &&
        !BLOCKED_WORK_ORDER_STATUSES.has(params.detail.sync_status || ''),
    )
    const syncPendingCount =
      PENDING_SYNC_STATUSES.has(params.detail.sync_status || '') || params.detail.status === 'work_order_pending'
        ? 1
        : 0
    const blockedReasons = [
      !params.detail.work_order ? '缺少 Work Order 映射' : '',
      BLOCKED_WORK_ORDER_STATUSES.has(params.detail.sync_status || '') ? `工单同步状态=${params.detail.sync_status || '-'}` : '',
      params.detail.job_cards.some((item) => Number(item.completed_qty || 0) < Number(item.expected_qty || 0))
        ? '存在工序完成度不足'
        : '',
    ].filter(Boolean)
    const jobCardMirror = parseStatusLabel(mirroredCards.length, blockedReasons.length, '工序状态')
    const processTone = parseProcessTone(mirroredCards.length, blockedReasons.length)
    const blockedTone = parseBlockedTone(blockedReasons.length)

    return {
      parityScopeLabel: parseScopeLabel(params.parity, params.tab, params.mode),
      sourceLabel: `${params.detail.plan_no} / ${params.detail.work_order || params.detail.sales_order || '-'}`,
      processProgressLabel:
        params.parity === 'production-process' || params.tab === 'process-progress'
          ? mirroredCards.length > 0
            ? 'production-process parity 已命中'
            : 'production-process parity 待补齐'
          : '主入口只读工序进度快照',
      processProgressTone: processTone,
      jobCardMirrorLabel: jobCardMirror.label,
      jobCardMirrorTone: jobCardMirror.tone,
      blockedReasonLabel: blockedReasons.length > 0 ? blockedReasons.join('；') : '无新增阻断写入项',
      blockedReasonTone: blockedTone,
      readonlyGuardReason:
        '当前详情仅开放 process-progress、job-card 状态镜像与 production-process parity 只读核对；job-card sync、导出、worker 补偿、ERPNext production 与真实生产写链路均保持冻结。',
      remainingGap: PRODUCTION_PROCESS_PROGRESS_REMAINING_GAPS.join('；'),
      mirroredJobCardCount: mirroredCards.length,
      syncPendingCount,
      blockedCount: blockedReasons.length,
      statusSnapshot: buildStatusSnapshot(
        params.detail.job_cards
          .slice(0, 3)
          .map((item) => `${item.operation || '工序'}:${item.completed_qty}/${item.expected_qty}`),
      ),
      items: params.detail.job_cards.slice(0, 4).map((item) => ({
        key: item.job_card,
        subjectLabel: `${item.job_card} / ${item.operation || '工序'}`,
        statusLabel: item.erpnext_status || params.detail.sync_status || '-',
        progressLabel: `${item.completed_qty}/${item.expected_qty}`,
        mirrorLabel:
          Number(item.completed_qty || 0) >= Number(item.expected_qty || 0) ? '工序状态已镜像' : '工序镜像待补齐',
        blockedReason: detailBlockedReason(
          params.detail.sync_status || '',
          item.operation || '工序',
          Number(item.completed_qty || 0),
          Number(item.expected_qty || 0),
        ),
      })),
    }
  }

  return {
    buildProductionProcessProgressDetailSummary,
    buildProductionProcessProgressListSummary,
  }
}
