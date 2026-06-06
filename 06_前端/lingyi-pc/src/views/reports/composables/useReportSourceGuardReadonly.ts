import {
  REPORT_SOURCE_GUARD_DISABLED_ACTIONS,
  REPORT_SOURCE_GUARD_FALLBACK_BLOCKED_REASONS,
  REPORT_SOURCE_GUARD_REMAINING_GAPS,
  type ReportSourceGuardDisabledAction,
  type ReportSourceGuardEntry,
  type ReportSourceGuardLineItem,
  type ReportSourceGuardSummaryCard,
  type ReportSourceGuardTone,
} from '../constants/reportSourceGuardFields'

interface ReportSourceGuardCatalogItem {
  report_key: string
  name: string
  source_modules: string[]
  report_type: string
  required_filters: string[]
  optional_filters: string[]
  metric_summary: string[]
  status: string
  ui_placeholders?: string[]
  ui_buttons?: string[]
}

export interface ReportSourceGuardReadonlyModel {
  routeStateLabel: string
  routeStateTone: ReportSourceGuardTone
  parityTagLabel: string
  parityTagTone: ReportSourceGuardTone
  sourceEntryLabel: string
  routeLabel: string
  summaryCards: ReportSourceGuardSummaryCard[]
  parityLines: ReportSourceGuardLineItem[]
  blockedReasons: string[]
  readonlyGuardText: string
  sourceItems: ReportSourceGuardEntry[]
  remainingGap: string
  disabledActions: ReadonlyArray<ReportSourceGuardDisabledAction>
}

const SOURCE_ENTRY_LABELS: Record<string, string> = {
  'customer-reconciliation-report': '客户对账入口',
  'financial-process': '财务流程入口',
  'bank-flow': '银行流水入口',
  'factory-product-stock-report': '协同库存入口',
  'catalog-direct': '目录直达入口',
}

const dedupe = (values: string[]): string[] => Array.from(new Set(values.filter(Boolean)))

const buildSourceEntryLabel = (sourceEntry: string): string => SOURCE_ENTRY_LABELS[sourceEntry] || sourceEntry || '目录直达入口'

const parseRouteState = (tab: string, parity: string): { label: string; tone: ReportSourceGuardTone } => {
  if (tab === 'source-guard' || parity === 'finance-collaboration') {
    return { label: 'source-guard active', tone: 'warning' }
  }
  return { label: 'catalog readonly', tone: 'info' }
}

const parseParityState = (parity: string): { label: string; tone: ReportSourceGuardTone } => {
  if (parity === 'finance-collaboration') {
    return { label: 'finance-collaboration parity', tone: 'success' }
  }
  return { label: 'catalog direct readonly', tone: 'info' }
}

const buildReadonlyGuardText = (parity: string, sourceEntry: string): string => {
  const reasons = [
    'ReportCatalog 仅开放 source-guard summary 与目录 readback，不发送写请求。',
    'report generation、export、download、backend remediation 均保持冻结。',
    'report/system catalog write paths 与 ERPNext/outbox/worker 继续关闭。',
  ]

  if (parity === 'finance-collaboration') {
    reasons.unshift('finance-collaboration parity 仅用于目录核对，不进入真实报表生成链。')
  }
  if (sourceEntry === 'catalog-direct') {
    reasons.unshift('catalog-direct source context 已锁定，目录直达仅保留只读语义。')
  }

  return reasons.join('；')
}

const buildSourceItems = (
  rows: ReportSourceGuardCatalogItem[],
  selectedItem: ReportSourceGuardCatalogItem | null,
): ReportSourceGuardEntry[] => {
  const preferred = selectedItem
    ? [selectedItem, ...rows.filter((item) => item.report_key !== selectedItem.report_key)]
    : rows

  if (preferred.length === 0) {
    return [
      {
        key: 'source-guard-fallback',
        title: 'report source-guard readonly fallback',
        status: 'readonly snapshot',
        source: 'catalog-direct',
        tone: 'info',
        summary: '尚未读取到目录条目，保留 source-guard 只读骨架。',
        details: [
          'route state 与 parity 已锁定',
          '真实报表生成、导出、下载与目录修复链路继续冻结',
        ],
      },
    ]
  }

  return preferred.slice(0, 4).map((item) => ({
    key: item.report_key,
    title: `${item.name} / ${item.report_key}`,
    status: item.status || 'readonly',
    source: item.source_modules.join(' / ') || 'catalog',
    tone: item.status === 'active' ? 'success' : 'warning',
    summary: `type=${item.report_type} / required=${item.required_filters.length} / optional=${item.optional_filters.length}`,
    details: [
      `metrics=${item.metric_summary.join('、') || '-'}`,
      `placeholders=${(item.ui_placeholders || []).join('、') || '-'}`,
      `buttons=${(item.ui_buttons || []).join('、') || '-'}`,
    ],
  }))
}

export const useReportSourceGuardReadonly = () => {
  const buildReportSourceGuardReadonly = (params: {
    rows: ReportSourceGuardCatalogItem[]
    selectedItem: ReportSourceGuardCatalogItem | null
    tab: string
    parity: string
    sourceEntry: string
    finalPath: string
    canRead: boolean
    canExport: boolean
    exportGuardMessage: string
  }): ReportSourceGuardReadonlyModel => {
    const routeState = parseRouteState(params.tab, params.parity)
    const parityState = parseParityState(params.parity)
    const sourceEntryLabel = buildSourceEntryLabel(params.sourceEntry)
    const sourceItems = buildSourceItems(params.rows, params.selectedItem)
    const blockedReasons = dedupe([
      routeState.label === 'source-guard active'
        ? 'source-guard query state 已锁定，当前目录仅用于来源核对。'
        : '当前目录保留 source-guard 只读骨架，不开放真实报表写链路。',
      params.parity === 'finance-collaboration'
        ? 'finance-collaboration parity 仅用于目录核对，不进入真实生成/下载链。'
        : '默认目录入口只保留 catalog readback，不放开生成或修复动作。',
      params.sourceEntry === 'catalog-direct'
        ? 'catalog-direct source context 仅保留目录直达上下文，不允许导出、下载或目录修复。'
        : `source_entry=${params.sourceEntry} 已锁定为只读入口。`,
      params.canRead ? '' : '当前账号缺少 report:read 权限，只读摘要继续保留。',
      params.canExport ? '即使具备 report:export 权限，导出仍保持只读锁定。' : '当前账号缺少 report:export 权限，导出继续禁用。',
      params.exportGuardMessage,
      ...REPORT_SOURCE_GUARD_FALLBACK_BLOCKED_REASONS,
    ])

    return {
      routeStateLabel: routeState.label,
      routeStateTone: routeState.tone,
      parityTagLabel: parityState.label,
      parityTagTone: parityState.tone,
      sourceEntryLabel,
      routeLabel: params.finalPath,
      summaryCards: [
        {
          key: 'query-state',
          label: 'query state',
          value: routeState.label,
          hint: params.finalPath,
          tone: routeState.tone,
        },
        {
          key: 'parity',
          label: 'finance-collaboration parity',
          value: parityState.label,
          hint: params.parity || 'catalog-direct',
          tone: parityState.tone,
        },
        {
          key: 'source-entry',
          label: 'source context',
          value: sourceEntryLabel,
          hint: params.sourceEntry || 'catalog-direct',
          tone: params.sourceEntry === 'catalog-direct' ? 'success' : 'info',
        },
        {
          key: 'source-items',
          label: 'source items',
          value: String(params.rows.length || sourceItems.length),
          hint: params.rows.length > 0 ? 'catalog items available for readonly review' : 'fallback skeleton retained',
          tone: params.rows.length > 0 ? 'success' : 'info',
        },
      ],
      parityLines: [
        { key: 'route', label: 'route', value: params.finalPath, tone: 'info' },
        { key: 'scope', label: 'readonly scope', value: 'report source-guard', tone: routeState.tone },
        { key: 'parity', label: 'parity', value: parityState.label, tone: parityState.tone },
        { key: 'source-entry', label: 'catalog direct source context', value: sourceEntryLabel, tone: 'info' },
        { key: 'write-boundary', label: 'write boundary', value: 'generation/export/download/remediation locked', tone: 'warning' },
      ],
      blockedReasons,
      readonlyGuardText: buildReadonlyGuardText(params.parity, params.sourceEntry),
      sourceItems,
      remainingGap: `remaining_gap: ${REPORT_SOURCE_GUARD_REMAINING_GAPS.join('；')}`,
      disabledActions: REPORT_SOURCE_GUARD_DISABLED_ACTIONS,
    }
  }

  return {
    buildReportSourceGuardReadonly,
  }
}
