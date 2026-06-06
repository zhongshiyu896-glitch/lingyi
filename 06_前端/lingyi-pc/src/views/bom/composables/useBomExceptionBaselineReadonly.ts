import { computed, type ComputedRef } from 'vue'
import {
  bomExceptionReadonlyDisabledActions,
  bomExceptionReadonlyFallbackBlockedReasons,
  type BomExceptionReadonlyEntry,
  type BomExceptionReadonlyLineItem,
  type BomExceptionReadonlySummaryCard,
  type BomExceptionReadonlyTone,
} from '@/views/bom/constants/bomExceptionBaselineFields'

export interface BomExceptionListRowInput {
  bomNo: string
  styleCode: string
  styleName: string
  version: string
  owner: string
  status: string
  updatedAt: string
  isDefault: boolean
}

export interface BomExceptionDetailLineInput {
  code: string
  name: string
  spec: string
  uom: string
  usage: number
  lossRate?: number
  remark?: string
}

interface UseBomExceptionBaselineReadonlyOptions {
  context: ComputedRef<'list' | 'detail'>
  currentRouteLabel: ComputedRef<string>
  routeTab: ComputedRef<string>
  detailMode: ComputedRef<string>
  routeParity: ComputedRef<string>
  listRows: ComputedRef<BomExceptionListRowInput[]>
  detailLines: ComputedRef<BomExceptionDetailLineInput[]>
  bomNo: ComputedRef<string>
  styleCode: ComputedRef<string>
  styleName: ComputedRef<string>
  versionLabel: ComputedRef<string>
}

const toTone = (status: string): BomExceptionReadonlyTone => {
  if (status === 'published' || status === 'aligned' || status === 'ready') return 'success'
  if (status === 'review' || status === 'attention' || status === 'readonly') return 'warning'
  if (status === 'draft' || status === 'blocked') return 'danger'
  return 'info'
}

export const useBomExceptionBaselineReadonly = ({
  context,
  currentRouteLabel,
  routeTab,
  detailMode,
  routeParity,
  listRows,
  detailLines,
  bomNo,
  styleCode,
  styleName,
  versionLabel,
}: UseBomExceptionBaselineReadonlyOptions) => {
  const isExceptionBaselineTab = computed<boolean>(() => routeTab.value === 'exception-baseline')
  const isReadonlyExceptionMode = computed<boolean>(() => detailMode.value === 'readonly-exception')
  const parityMode = computed<string>(() =>
    routeParity.value === 'goodsplan-material-samples' ? 'goodsplan-material-samples linked' : 'bom-local',
  )

  const exceptionRowCount = computed<number>(() =>
    context.value === 'detail' ? detailLines.value.length : listRows.value.length,
  )

  const sourceStatus = computed<string>(() => {
    if (context.value === 'detail' && isReadonlyExceptionMode.value) return 'detail-readonly-exception'
    if (isExceptionBaselineTab.value) return 'list-exception-baseline'
    return 'bom-baseline'
  })

  const blockedReasons = computed<string[]>(() => {
    const reasons = [...bomExceptionReadonlyFallbackBlockedReasons]
    if (context.value === 'list') {
      const reviewCount = listRows.value.filter((row) => row.status === 'review').length
      const draftCount = listRows.value.filter((row) => row.status === 'draft').length
      if (reviewCount > 0) reasons.unshift(`当前列表包含 ${reviewCount} 条审核中版本，异常基线仍保持只读。`)
      if (draftCount > 0) reasons.unshift(`当前列表包含 ${draftCount} 条草稿版本，禁止触发真实审计与同步。`)
    } else if (detailLines.value.some((line) => Number(line.lossRate || 0) > 3)) {
      reasons.unshift('详情存在高损耗或待确认物料行，异常明细保持只读核对。')
    }
    return reasons
  })

  const readonlyGuardText = computed<string>(() => {
    const reasons = [
      'version switching 与 alternate material true save 继续关闭',
      'audit/sync/export 仅保留 disabled UI，不触发真实执行',
      'backend remediation、ERPNext、outbox、worker 与 production write path 未开放',
    ]
    if (routeParity.value === 'goodsplan-material-samples') {
      reasons.unshift('goodsplan-materialSamples alias 仅用于只读 parity 核对，不放开真实联动。')
    }
    return reasons.join('；')
  })

  const summaryCards = computed<BomExceptionReadonlySummaryCard[]>(() => [
    {
      key: 'query-state',
      label: 'query state',
      value: context.value === 'detail'
        ? (isReadonlyExceptionMode.value ? 'readonly-exception active' : 'detail baseline')
        : (isExceptionBaselineTab.value ? 'exception-baseline active' : 'list baseline'),
      hint: currentRouteLabel.value,
      tone: (context.value === 'detail' ? isReadonlyExceptionMode.value : isExceptionBaselineTab.value) ? 'success' : 'info',
    },
    {
      key: 'parity',
      label: 'sample parity',
      value: parityMode.value,
      hint: routeParity.value === 'goodsplan-material-samples' ? 'goodsplan/materialSamples alias' : 'bom direct route',
      tone: routeParity.value === 'goodsplan-material-samples' ? 'success' : 'info',
    },
    {
      key: 'exception-rows',
      label: 'exception rows',
      value: String(exceptionRowCount.value),
      hint: context.value === 'detail' ? 'detail material lines in readonly context' : 'filtered rows in readonly list context',
      tone: exceptionRowCount.value > 0 ? 'warning' : 'info',
    },
    {
      key: 'source-status',
      label: 'source status',
      value: sourceStatus.value,
      hint: `${bomNo.value} / ${styleCode.value || styleName.value}`,
      tone: 'info',
    },
  ])

  const parityLines = computed<BomExceptionReadonlyLineItem[]>(() => [
    {
      key: 'route',
      label: 'route',
      value: currentRouteLabel.value,
      tone: 'info',
    },
    {
      key: 'bom',
      label: 'bom',
      value: `${bomNo.value} / ${versionLabel.value}`,
      tone: 'info',
    },
    {
      key: 'style',
      label: 'style',
      value: `${styleCode.value || '-'} / ${styleName.value || '-'}`,
      tone: 'info',
    },
    {
      key: 'readonly-scope',
      label: 'readonly scope',
      value: context.value === 'detail' ? 'exception detail context' : 'exception list context',
      tone: context.value === 'detail' ? 'warning' : 'success',
    },
  ])

  const listItems = computed<BomExceptionReadonlyEntry[]>(() =>
    listRows.value.slice(0, 4).map((row) => ({
      key: row.bomNo,
      title: `${row.bomNo} / ${row.styleCode}`,
      owner: row.owner,
      source: routeParity.value === 'goodsplan-material-samples' ? 'goodsplan-material-samples' : 'bom-list',
      status: row.status === 'published' ? 'baseline ready' : row.status === 'review' ? 'review blocked' : 'draft blocked',
      tone: row.status === 'published' && row.isDefault ? 'success' : toTone(row.status),
      summary: `${row.styleName} / ${row.version}`,
      details: [
        `default_version=${row.isDefault ? 'yes' : 'no'}`,
        `updated_at=${row.updatedAt}`,
        row.status === 'published' ? '已发布版本仍保持 exception-baseline 只读核对。' : '非发布版本禁止触发真实审计、同步和导出。',
      ],
    })),
  )

  const detailItems = computed<BomExceptionReadonlyEntry[]>(() =>
    detailLines.value.slice(0, 4).map((line, index) => {
      const lossRate = Number(line.lossRate || 0)
      const status = lossRate > 3 ? 'loss-rate attention' : 'readonly detail'
      return {
        key: `${line.code}-${index}`,
        title: `${line.code} / ${line.name}`,
        owner: 'bom-detail',
        source: routeParity.value === 'goodsplan-material-samples' ? 'goodsplan-material-samples' : 'bom-detail',
        status,
        tone: lossRate > 3 ? 'warning' : 'info',
        summary: `${line.spec} / usage=${line.usage}`,
        details: [
          `uom=${line.uom}`,
          `loss_rate=${lossRate}%`,
          `remark=${line.remark || 'detail readonly fallback'}`,
        ],
      }
    }),
  )

  const remainingGap = computed<string>(() => {
    if (context.value === 'detail') {
      return 'remaining_gap: 详情页仅提供 exception detail readonly context；真实版本切换、保存、导出、同步仍未开放。'
    }
    return 'remaining_gap: 列表页仅提供 exception-baseline readonly summary；真实审计、同步、导出和 backend remediation 仍未开放。'
  })

  return {
    isExceptionBaselineTab,
    isReadonlyExceptionMode,
    summaryCards,
    parityLines,
    blockedReasons,
    readonlyGuardText,
    exceptionItems: computed(() => (context.value === 'detail' ? detailItems.value : listItems.value)),
    disabledActions: bomExceptionReadonlyDisabledActions,
    remainingGap,
  }
}
