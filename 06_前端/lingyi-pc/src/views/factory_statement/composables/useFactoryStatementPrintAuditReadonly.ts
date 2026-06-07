import { computed, unref, type ComputedRef, type Ref } from 'vue'
import type { FactoryStatementReadonlyRecord } from '@/api/factory_statement_readonly'
import {
  FACTORY_STATEMENT_PRINT_AUDIT_CARD_FIELDS,
  FACTORY_STATEMENT_PRINT_AUDIT_GUARD_ACTIONS,
  FACTORY_STATEMENT_PRINT_AUDIT_REMAINING_GAP,
  type FactoryStatementPrintAuditCardKey,
  type FactoryStatementPrintAuditRouteItem,
  type FactoryStatementPrintAuditStatus,
  type FactoryStatementPrintAuditStatusRow,
} from '@/views/factory_statement/constants/factoryStatementPrintAuditFields'

type ReadableRef<T> = Ref<T> | ComputedRef<T>

interface UseFactoryStatementPrintAuditReadonlyOptions {
  detailRecord: ReadableRef<FactoryStatementReadonlyRecord | null>
  parity: ReadableRef<string>
  tab: ReadableRef<string>
  focus: ReadableRef<string>
  loading: ReadableRef<boolean>
  hasRouteStatementId: ReadableRef<boolean>
  resolvedStatementId: ReadableRef<number | null>
}

export interface FactoryStatementPrintAuditReadonlySummary {
  routeScopeLabel: string
  queryStateLabel: string
  focusLabel: string
  parityLabel: string
  parityTone: 'warning' | 'info'
  sourceStatusLabel: string
  itemStatusLabel: string
  printGuardLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  routeItems: FactoryStatementPrintAuditRouteItem[]
  statusRows: FactoryStatementPrintAuditStatusRow[]
  cardValues: Record<FactoryStatementPrintAuditCardKey, string>
}

const statusWeight: Record<FactoryStatementPrintAuditStatus, number> = {
  ok: 0,
  warn: 1,
  blocked: 2,
}

const normalizeStatus = (
  left: FactoryStatementPrintAuditStatus,
  right: FactoryStatementPrintAuditStatus,
): FactoryStatementPrintAuditStatus => (statusWeight[left] >= statusWeight[right] ? left : right)

export const useFactoryStatementPrintAuditReadonly = ({
  detailRecord,
  parity,
  tab,
  focus,
  loading,
  hasRouteStatementId,
  resolvedStatementId,
}: UseFactoryStatementPrintAuditReadonlyOptions): {
  printAuditReadonlySummary: ComputedRef<FactoryStatementPrintAuditReadonlySummary>
  cardFields: typeof FACTORY_STATEMENT_PRINT_AUDIT_CARD_FIELDS
  guardActions: typeof FACTORY_STATEMENT_PRINT_AUDIT_GUARD_ACTIONS
} => {
  const detail = computed(() => unref(detailRecord))
  const parityValue = computed(() => String(unref(parity) || '').trim().toLowerCase())
  const tabValue = computed(() => String(unref(tab) || '').trim().toLowerCase())
  const focusValue = computed(() => String(unref(focus) || '').trim().toLowerCase())
  const loadingValue = computed(() => Boolean(unref(loading)))
  const hasStatementId = computed(() => Boolean(unref(hasRouteStatementId)))
  const fallbackStatementId = computed(() => unref(resolvedStatementId))

  const printAuditReadonlySummary = computed<FactoryStatementPrintAuditReadonlySummary>(() => {
    const record = detail.value
    const sourceCount = Number(record?.raw.source_count || 0)
    const itemCount = record?.items.length || 0
    const logCount = record?.logs.length || 0
    const hasPayableError = Boolean(record?.raw.payable_error_code || record?.raw.payable_error_message)
    const hasInvoiceDraft = Boolean(record?.raw.purchase_invoice_name)
    const activeTab = tabValue.value === 'print-audit-readonly'
    const activeFocus = focusValue.value === 'print-source'
    const activeParity = parityValue.value === 'factory-statement'

    const sourceStatus = !record
      ? loadingValue.value
        ? 'warn'
        : 'blocked'
      : sourceCount > 0
        ? 'ok'
        : 'blocked'

    const itemStatus = !record
      ? loadingValue.value
        ? 'warn'
        : 'blocked'
      : itemCount > 0
        ? 'ok'
        : 'warn'

    const printPayloadStatus = !record
      ? loadingValue.value
        ? 'warn'
        : 'blocked'
      : logCount > 0 || hasInvoiceDraft
        ? 'ok'
        : 'warn'

    const printGuardStatus = normalizeStatus(
      normalizeStatus(sourceStatus, itemStatus),
      hasPayableError ? 'blocked' : printPayloadStatus,
    )

    const routeScopeLabel = activeTab
      ? 'print / print-audit-readonly'
      : 'print / readonly baseline'
    const queryStateLabel = `tab=${activeTab ? 'print-audit-readonly' : tabValue.value || '-'}`
    const focusLabel = activeFocus ? 'print-source focus' : 'print-source pending'
    const parityLabel = activeParity ? 'factory-statement parity' : 'factory-statement readonly'

    const routeItems: FactoryStatementPrintAuditRouteItem[] = [
      {
        key: 'print-baseline',
        label: '打印只读基线',
        route: '/factory-statements/print',
        active: !activeTab && !activeFocus,
        note: '打印预览基线，只保留 readonly shell 与 guard。',
      },
      {
        key: 'print-audit-readonly',
        label: 'print-audit readonly',
        route: '/factory-statements/print?tab=print-audit-readonly&parity=factory-statement',
        active: activeTab,
        note: '聚焦 print-audit query state 与 source/status，只读筛选态。',
      },
      {
        key: 'print-source-focus',
        label: 'print-source focus',
        route: '/factory-statements/print?tab=print-audit-readonly&parity=factory-statement&focus=print-source',
        active: activeFocus,
        note: '锁定 print-source 焦点，只读核对来源与状态行。',
      },
    ]

    const statusRows: FactoryStatementPrintAuditStatusRow[] = [
      {
        key: 'source-status',
        label: 'source/status',
        status: sourceStatus,
        summary: !record
          ? loadingValue.value
            ? '正在回读 source 状态，只读区已稳定挂载。'
            : '尚未获得可回读对账单，当前先展示 route/query guard。'
          : sourceCount > 0
            ? `来源条数 ${sourceCount}，可用于 print-source 只读核对。`
            : '来源条数为空，需人工核对单据来源映射。',
        recommendation: '保持只读观察，不开放真实来源修复、确认或导出。',
      },
      {
        key: 'item-status',
        label: 'item/status',
        status: itemStatus,
        summary: !record
          ? loadingValue.value
            ? '正在等待 item/status 行，只读区先展示 fallback 状态。'
            : '暂无 item/status 数据，当前以 fallback 行维持可测试只读面。'
          : itemCount > 0
            ? `明细行 ${itemCount} 条，日志 ${logCount} 条。`
            : '当前无明细行，仅保留只读状态摘要。',
        recommendation: '保留 item/status readonly 行，禁止真实打印、下载和结算链路。',
      },
      {
        key: 'print-audit',
        label: 'print-audit / payable mirror',
        status: hasPayableError ? 'blocked' : printPayloadStatus,
        summary: hasPayableError
          ? '检测到 payable 镜像错误快照，打印页仅保留只读 guard。'
          : !record
            ? loadingValue.value
              ? '打印预览载荷回读中，真实打印/导出仍禁用。'
              : '未回读到打印载荷，当前仅保留 route/query guard 与 disabled reasons。'
            : hasInvoiceDraft
              ? '已存在发票草稿镜像，打印页仅可只读观察。'
              : '当前未生成发票草稿镜像，打印页维持 fail-closed。',
        recommendation: '禁止 confirm/cancel/settlement/export/download/outbox/worker/ERPNext/write。',
      },
    ]

    const sourceStatusLabel = sourceStatus === 'ok'
      ? 'source ready'
      : sourceStatus === 'warn'
        ? 'source pending'
        : 'source blocked'
    const itemStatusLabel = itemStatus === 'ok'
      ? `${itemCount || 0} rows readonly`
      : itemStatus === 'warn'
        ? 'fallback readonly rows'
        : 'rows blocked'
    const printGuardLabel = printGuardStatus === 'blocked'
      ? 'fail-closed'
      : printGuardStatus === 'warn'
        ? 'guarded readonly'
        : 'readonly stable'

    const blockedReason = !record
      ? loadingValue.value
        ? 'print-audit/source readonly section 已先行挂载，正在回读对账单详情；真实打印、导出、结算与下载继续禁用。'
        : hasStatementId.value
          ? '当前仅获得 route/query guard，等待只读详情回读；真实打印、导出、结算与下载继续禁用。'
          : fallbackStatementId.value
            ? `当前 route 未携带 id，已回退到只读 statement ${fallbackStatementId.value} 进行核对；真实打印、导出、结算与下载继续禁用。`
            : '当前 route 未携带 id，只读区保持可见并维持 fail-closed；真实打印、导出、结算与下载继续禁用。'
      : hasPayableError
        ? '检测到 payable 镜像异常或错误快照，print-audit/source 只读区仅保留 guard 与人工核对提示。'
        : '当前仅允许 print-audit/source 核对；真实确认、取消、结算、导出、下载、Outbox、Worker、ERPNext 与 production write 均禁用。'

    return {
      routeScopeLabel,
      queryStateLabel,
      focusLabel,
      parityLabel,
      parityTone: activeParity ? 'warning' : 'info',
      sourceStatusLabel,
      itemStatusLabel,
      printGuardLabel,
      blockedReason,
      readonlyGuardReason:
        '当前页面仅允许 print-audit/source 只读核对；confirm/cancel/settlement/export/download、Outbox、Worker、ERPNext 与 production write 均禁用。',
      remainingGap: FACTORY_STATEMENT_PRINT_AUDIT_REMAINING_GAP,
      routeItems,
      statusRows,
      cardValues: {
        routeScope: routeScopeLabel,
        sourceStatus: sourceStatusLabel,
        itemStatus: itemStatusLabel,
        printGuard: printGuardLabel,
      },
    }
  })

  return {
    printAuditReadonlySummary,
    cardFields: FACTORY_STATEMENT_PRINT_AUDIT_CARD_FIELDS,
    guardActions: FACTORY_STATEMENT_PRINT_AUDIT_GUARD_ACTIONS,
  }
}
