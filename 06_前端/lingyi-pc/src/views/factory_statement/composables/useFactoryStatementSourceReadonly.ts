import { computed, unref, type ComputedRef, type Ref } from 'vue'
import type { FactoryStatementListItem } from '@/api/factory_statement'
import type { FactoryStatementReadonlyRecord } from '@/api/factory_statement_readonly'
import {
  FACTORY_STATEMENT_SOURCE_CARD_FIELDS,
  FACTORY_STATEMENT_SOURCE_GUARD_ACTIONS,
  FACTORY_STATEMENT_SOURCE_REMAINING_GAP,
  type FactoryStatementSourceCardKey,
  type FactoryStatementSourceDriftRow,
  type FactoryStatementSourceReadonlyStatus,
  type FactoryStatementSourceRouteItem,
} from '@/views/factory_statement/constants/factoryStatementSourceFields'

type ReadableRef<T> = Ref<T> | ComputedRef<T>

type ListLikeRow = Pick<
  FactoryStatementListItem,
  | 'source_count'
  | 'statement_status'
  | 'payable_outbox_status'
  | 'purchase_invoice_name'
  | 'payable_error_code'
  | 'payable_error_message'
>

interface UseFactoryStatementSourceReadonlyOptions {
  context: 'list' | 'detail'
  listRows?: ReadableRef<ListLikeRow[]>
  detailRecord?: ReadableRef<FactoryStatementReadonlyRecord | null>
  parity: ReadableRef<string>
  tab?: ReadableRef<string>
  mode?: ReadableRef<string>
}

export interface FactoryStatementSourceReadonlySummary {
  sourceScopeLabel: string
  parityLabel: string
  parityTone: 'warning' | 'info'
  sourceBreakpointSummary: string
  billDriftSummary: string
  remainingGap: string
  readonlyGuardReason: string
  retainedCand217: boolean
  retainedCand116: boolean
  retainedCand008: boolean
  routeItems: FactoryStatementSourceRouteItem[]
  driftRows: FactoryStatementSourceDriftRow[]
  cardValues: Record<FactoryStatementSourceCardKey, string>
}

const statusWeight: Record<FactoryStatementSourceReadonlyStatus, number> = {
  ok: 0,
  warn: 1,
  blocked: 2,
}

const normalizeStatus = (
  left: FactoryStatementSourceReadonlyStatus,
  right: FactoryStatementSourceReadonlyStatus,
): FactoryStatementSourceReadonlyStatus => (statusWeight[left] >= statusWeight[right] ? left : right)

const resolveTagType = (status: FactoryStatementSourceReadonlyStatus): 'success' | 'warning' | 'danger' => {
  if (status === 'ok') {
    return 'success'
  }
  if (status === 'warn') {
    return 'warning'
  }
  return 'danger'
}

const resolveOutboxStatusLabel = (pendingCount: number, failedCount: number, succeededCount: number): string => {
  const parts: string[] = []
  if (pendingCount > 0) {
    parts.push(`待同步 ${pendingCount}`)
  }
  if (failedCount > 0) {
    parts.push(`异常 ${failedCount}`)
  }
  if (succeededCount > 0) {
    parts.push(`镜像 ${succeededCount}`)
  }
  return parts.length > 0 ? parts.join(' / ') : '未触发 outbox'
}

export const useFactoryStatementSourceReadonly = ({
  context,
  listRows,
  detailRecord,
  parity,
  tab,
  mode,
}: UseFactoryStatementSourceReadonlyOptions): {
  sourceReadonlySummary: ComputedRef<FactoryStatementSourceReadonlySummary>
  cardFields: typeof FACTORY_STATEMENT_SOURCE_CARD_FIELDS
  guardActions: typeof FACTORY_STATEMENT_SOURCE_GUARD_ACTIONS
  statusTagType: typeof resolveTagType
} => {
  const parityValue = computed(() => String(unref(parity) || '').trim().toLowerCase())
  const tabValue = computed(() => String(unref(tab) || '').trim().toLowerCase())
  const modeValue = computed(() => String(unref(mode) || '').trim().toLowerCase())
  const currentListRows = computed(() => unref(listRows) || [])
  const currentDetailRecord = computed(() => unref(detailRecord) || null)

  const sourceReadonlySummary = computed<FactoryStatementSourceReadonlySummary>(() => {
    const rows = currentListRows.value
    const detail = currentDetailRecord.value

    const sourceGapCount = context === 'list'
      ? rows.filter((row) => Number(row.source_count || 0) <= 0).length
      : detail && Number(detail.raw.source_count || 0) <= 0
        ? 1
        : 0

    const detailItemGapCount = context === 'detail'
      ? detail && detail.items.length === 0
        ? 1
        : 0
      : 0

    const failedOutboxCount = context === 'list'
      ? rows.filter((row) => row.payable_outbox_status === 'failed' || row.payable_outbox_status === 'dead').length
      : detail && detail.raw.payable_outbox_status && ['failed', 'dead'].includes(detail.raw.payable_outbox_status)
        ? 1
        : 0

    const pendingOutboxCount = context === 'list'
      ? rows.filter((row) => row.payable_outbox_status === 'pending' || row.payable_outbox_status === 'processing').length
      : detail && detail.raw.payable_outbox_status && ['pending', 'processing'].includes(detail.raw.payable_outbox_status)
        ? 1
        : 0

    const succeededOutboxCount = context === 'list'
      ? rows.filter((row) => row.payable_outbox_status === 'succeeded').length
      : detail?.raw.payable_outbox_status === 'succeeded'
        ? 1
        : 0

    const invoiceGapCount = context === 'list'
      ? rows.filter((row) => row.statement_status === 'payable_draft_created' && !row.purchase_invoice_name).length
      : detail && detail.raw.statement_status === 'payable_draft_created' && !detail.raw.purchase_invoice_name
        ? 1
        : 0

    const payableErrorCount = context === 'list'
      ? rows.filter((row) => Boolean(row.payable_error_code || row.payable_error_message)).length
      : detail && (detail.raw.payable_error_code || detail.raw.payable_error_message)
        ? 1
        : 0

    const logGapCount = context === 'detail'
      ? detail && detail.logs.length === 0
        ? 1
        : 0
      : 0

    const breakpointCount = sourceGapCount + detailItemGapCount + invoiceGapCount + failedOutboxCount + logGapCount
    const driftSeverity = normalizeStatus(
      sourceGapCount > 0 || detailItemGapCount > 0 || invoiceGapCount > 0 || logGapCount > 0 ? 'warn' : 'ok',
      failedOutboxCount > 0 || payableErrorCount > 0 ? 'blocked' : 'ok',
    )

    const sourceScopeLabel = context === 'list'
      ? tabValue.value === 'source-parity'
        ? 'list / source-parity'
        : 'list / readonly baseline'
      : modeValue.value === 'readonly-lineage'
        ? 'detail / readonly-lineage'
        : 'detail / readonly baseline'

    const parityLabel = parityValue.value === 'foundation-factory'
      ? 'foundation-factory parity'
      : 'factory-statement readonly'

    const routeItems: FactoryStatementSourceRouteItem[] = [
      {
        key: 'list-source-parity',
        label: '列表 source-parity',
        route: '/factory-statements/list?tab=source-parity',
        active: context === 'list' && tabValue.value === 'source-parity',
        note: '聚焦来源链断点和账单漂移，只读筛选态。',
      },
      {
        key: 'detail-readonly-lineage',
        label: '详情 readonly-lineage',
        route: '/factory-statements/detail?mode=readonly-lineage',
        active: context === 'detail' && modeValue.value === 'readonly-lineage',
        note: '聚焦单据来源链和 payable 镜像状态，只读详情态。',
      },
      {
        key: 'foundation-factory-parity',
        label: '基础资料 parity',
        route: '/foundation/factory -> /factory-statements/list?parity=foundation-factory&tab=source-parity',
        active: parityValue.value === 'foundation-factory',
        note: '说明基础资料加工厂入口如何映射到工厂对账只读核对。',
      },
    ]

    const driftRows: FactoryStatementSourceDriftRow[] = [
      {
        key: 'source-breakpoint',
        label: '来源链断点',
        status: sourceGapCount > 0 || detailItemGapCount > 0 ? 'blocked' : 'ok',
        summary:
          sourceGapCount > 0 || detailItemGapCount > 0
            ? `发现 ${sourceGapCount + detailItemGapCount} 处来源链断点，需人工核对 source_count、对账明细行和单据来源映射。`
            : '当前页未发现来源条数缺失或明细缺席的断点。',
        recommendation: '保留只读核对，真实来源修复需走后台受控链路。',
      },
      {
        key: 'payable-mirror-drift',
        label: '账单漂移 / payable 镜像',
        status: failedOutboxCount > 0 || payableErrorCount > 0 ? 'blocked' : invoiceGapCount > 0 ? 'warn' : 'ok',
        summary:
          failedOutboxCount > 0 || payableErrorCount > 0
            ? `发现 ${failedOutboxCount + payableErrorCount} 处 payable 镜像异常或错误快照。`
            : invoiceGapCount > 0
              ? `发现 ${invoiceGapCount} 处已生成应付草稿状态但缺少发票镜像。`
              : 'payable 镜像状态与当前只读摘要一致。',
        recommendation: '仅保留镜像说明与 guard，禁止支付回写、ERPNext 联动和后台修复。',
      },
      {
        key: 'audit-trail-readonly',
        label: '日志 / 打印 / 导出 guard',
        status: logGapCount > 0 ? 'warn' : 'ok',
        summary:
          logGapCount > 0
            ? '详情页操作日志缺失，当前仅能维持断点与 guard 说明。'
            : '日志链路可回读，但打印、导出和后台修复均保持禁用。',
        recommendation: '打印仅保留只读预览，导出和后台修复继续保持 guard。',
      },
    ]

    const sourceBreakpointSummary = breakpointCount > 0
      ? `来源链断点 ${breakpointCount} 处，当前只读区仅提示 source_count / 明细 / payable 镜像差异。`
      : '当前页未发现显式来源链断点，保留只读核对摘要。'

    const billDriftSummary = driftSeverity === 'blocked'
      ? '账单漂移包含 payable 镜像异常或错误快照，需人工判定。'
      : driftSeverity === 'warn'
        ? '账单漂移存在只读缺项提示，但未触发真实写链路。'
        : '账单漂移未发现阻断级异常，仍保持只读 guard。'

    return {
      sourceScopeLabel,
      parityLabel,
      parityTone: parityValue.value === 'foundation-factory' ? 'warning' : 'info',
      sourceBreakpointSummary,
      billDriftSummary,
      remainingGap: FACTORY_STATEMENT_SOURCE_REMAINING_GAP,
      readonlyGuardReason: '当前仅允许来源链断点核对；支付回写、打印执行、导出、ERPNext 联动和后台修复均禁用。',
      retainedCand217: true,
      retainedCand116: true,
      retainedCand008: true,
      routeItems,
      driftRows,
      cardValues: {
        routeScope: sourceScopeLabel,
        breakpointCount: breakpointCount > 0 ? `${breakpointCount} 处` : '无显式断点',
        driftSeverity: driftSeverity === 'blocked' ? 'blocked' : driftSeverity === 'warn' ? 'warn' : 'ok',
        payableMirror: resolveOutboxStatusLabel(pendingOutboxCount, failedOutboxCount, succeededOutboxCount),
      },
    }
  })

  return {
    sourceReadonlySummary,
    cardFields: FACTORY_STATEMENT_SOURCE_CARD_FIELDS,
    guardActions: FACTORY_STATEMENT_SOURCE_GUARD_ACTIONS,
    statusTagType: resolveTagType,
  }
}
