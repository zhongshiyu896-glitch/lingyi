import type { SubcontractOrderDetailData, SubcontractOrderListItem } from '@/api/subcontract'
import {
  subcontractInspectionGuardDisabledActions,
  subcontractInspectionGuardFallbackBlockedReasons,
  subcontractInspectionGuardRemainingGaps,
  type SubcontractInspectionGuardEntry,
  type SubcontractInspectionGuardLineItem,
  type SubcontractInspectionGuardSummaryCard,
  type SubcontractInspectionGuardTone,
} from '@/views/subcontract/constants/subcontractInspectionGuardFields'

export interface SubcontractInspectionGuardReadonlyModel {
  routeStateLabel: string
  routeStateTone: SubcontractInspectionGuardTone
  parityTagLabel: string
  parityTagTone: SubcontractInspectionGuardTone
  routeLabel: string
  summaryCards: SubcontractInspectionGuardSummaryCard[]
  parityLines: SubcontractInspectionGuardLineItem[]
  blockedReasons: string[]
  readonlyGuardText: string
  inspectionItems: SubcontractInspectionGuardEntry[]
  remainingGap: string
  disabledActions: ReadonlyArray<{
    key: string
    label: string
    reason: string
  }>
}

const normalizeString = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumber = (value?: string | number | null): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const toCountLabel = (value: number): string => `${value}`

const dedupe = (values: string[]): string[] => Array.from(new Set(values.filter(Boolean)))

const parseListItemStatus = (row: SubcontractOrderListItem): { label: string; tone: SubcontractInspectionGuardTone } => {
  const rejectedQty = toNumber(row.rejected_qty)
  const receivedQty = toNumber(row.received_qty)
  const acceptedQty = toNumber(row.accepted_qty)
  const issuedQty = toNumber(row.issued_qty)
  const rawStatus = normalizeString(row.status).toLowerCase()

  if (rejectedQty > 0) return { label: 'inspection blocked', tone: 'danger' }
  if (receivedQty > acceptedQty || rawStatus === 'waiting_inspection') return { label: 'inspection pending', tone: 'warning' }
  if (issuedQty > receivedQty || rawStatus === 'waiting_receive') return { label: 'receipt pending', tone: 'warning' }
  if (acceptedQty > 0) return { label: 'inspection snapshot ready', tone: 'success' }
  return { label: 'readonly snapshot', tone: 'info' }
}

const buildListBlockedReason = (row: SubcontractOrderListItem): string => {
  const rejectedQty = toNumber(row.rejected_qty)
  if (rejectedQty > 0) return `存在 ${rejectedQty} 件不良，收货/结算保持只读阻断`

  const receivedQty = toNumber(row.received_qty)
  const acceptedQty = toNumber(row.accepted_qty)
  if (receivedQty > acceptedQty) {
    return `仍有 ${receivedQty - acceptedQty} 件待验货，结算链路保持冻结`
  }

  const issuedQty = toNumber(row.issued_qty)
  if (issuedQty > receivedQty) {
    return `仍有 ${issuedQty - receivedQty} 件待收货，真实收货链路未开放`
  }

  return '写入链路冻结，仅允许只读验货核对'
}

const parseDetailItemStatus = (
  inspectedQty: number,
  acceptedQty: number,
  rejectedQty: number,
): { label: string; tone: SubcontractInspectionGuardTone } => {
  if (rejectedQty > 0) return { label: 'inspection blocked', tone: 'danger' }
  if (inspectedQty > acceptedQty) return { label: 'inspection pending', tone: 'warning' }
  if (acceptedQty > 0) return { label: 'inspection passed', tone: 'success' }
  return { label: 'readonly snapshot', tone: 'info' }
}

const buildDetailBlockedReasons = (detail: SubcontractOrderDetailData, parity: string): string[] => {
  const reasons: string[] = []
  const issuedQty = toNumber(detail.issued_qty)
  const receivedQty = toNumber(detail.received_qty)
  const acceptedQty = toNumber(detail.accepted_qty)
  const rejectedQty = toNumber(detail.rejected_qty)

  if (issuedQty > receivedQty) {
    reasons.push(`仍有 ${issuedQty - receivedQty} 件待收货，真实收货链路保持冻结`)
  }
  if (receivedQty > acceptedQty) {
    reasons.push(`仍有 ${receivedQty - acceptedQty} 件待验货，结算链路保持冻结`)
  }
  if (rejectedQty > 0) {
    reasons.push(`存在 ${rejectedQty} 件不良，收货/结算链路保持只读阻断`)
  }
  if (parity === 'material-purchase') {
    reasons.push('material-purchase parity 仅用于采购侧核对，不进入真实库存链。')
  }

  return dedupe([...reasons, ...subcontractInspectionGuardFallbackBlockedReasons])
}

const buildReadonlyGuardText = (scope: 'list' | 'detail', parity: string, active: boolean): string => {
  const reasons = [
    '收货、发料、结算、导出仅保留 disabled UI，不触发真实请求。',
    'service/router/outbox/worker 与 ERPNext 写链路继续关闭。',
  ]

  if (parity === 'material-purchase') {
    reasons.unshift('material-purchase parity 仅用于委外验货核对，不放开采购/库存联动。')
  }
  if (scope === 'detail' && active) {
    reasons.unshift('readonly-inspection detail context 已锁定，返回列表时保持 inspection-guard query state。')
  }

  return reasons.join('；')
}

const buildRouteStateLabel = (active: boolean, scope: 'list' | 'detail'): string => {
  if (scope === 'detail') return active ? 'readonly-inspection active' : 'detail readonly default'
  return active ? 'inspection-guard active' : 'inspection default'
}

const buildParityTagLabel = (parity: string): string =>
  parity === 'material-purchase' ? 'material-purchase parity' : 'subcontract readonly'

const buildRemainingGap = (): string => `remaining_gap: ${subcontractInspectionGuardRemainingGaps.join('；')}`

export const useSubcontractInspectionGuardReadonly = () => {
  const buildSubcontractInspectionGuardListModel = (params: {
    rows: SubcontractOrderListItem[]
    tab: string
    parity: string
    finalPath: string
  }): SubcontractInspectionGuardReadonlyModel => {
    const active = params.tab === 'inspection-guard'
    const blockedRows = params.rows.filter((row) => buildListBlockedReason(row) !== '写入链路冻结，仅允许只读验货核对')
    const inspectionRows = params.rows.filter((row) => {
      const receivedQty = toNumber(row.received_qty)
      const inspectedQty = toNumber(row.inspected_qty)
      const acceptedQty = toNumber(row.accepted_qty)
      const rejectedQty = toNumber(row.rejected_qty)
      return receivedQty > 0 || inspectedQty > 0 || acceptedQty > 0 || rejectedQty > 0
    })
    const blockedReasons = dedupe([
      active
        ? 'inspection-guard query state 已锁定，当前列表仅用于委外验货阻断核对。'
        : '当前列表保留 inspection guard 只读骨架，不开放真实收发/结算链路。',
      params.parity === 'material-purchase'
        ? 'material-purchase parity 仅用于采购侧核对，不进入真实库存链。'
        : '默认委外只读入口，库存与采购写回均保持冻结。',
      ...blockedRows.slice(0, 3).map((row) => `${row.subcontract_no}: ${buildListBlockedReason(row)}`),
      ...subcontractInspectionGuardFallbackBlockedReasons,
    ])

    return {
      routeStateLabel: buildRouteStateLabel(active, 'list'),
      routeStateTone: active ? 'warning' : 'info',
      parityTagLabel: buildParityTagLabel(params.parity),
      parityTagTone: params.parity === 'material-purchase' ? 'success' : 'info',
      routeLabel: params.finalPath,
      summaryCards: [
        {
          key: 'query-state',
          label: 'query state',
          value: active ? 'inspection-guard active' : 'default readonly',
          hint: params.finalPath,
          tone: active ? 'success' : 'info',
        },
        {
          key: 'parity',
          label: 'material-purchase parity',
          value: params.parity === 'material-purchase' ? 'locked' : 'subcontract readonly',
          hint: params.parity === 'material-purchase' ? 'material-purchase linked list route' : 'direct subcontract list route',
          tone: params.parity === 'material-purchase' ? 'success' : 'info',
        },
        {
          key: 'inspection-items',
          label: 'inspection items',
          value: toCountLabel(inspectionRows.length),
          hint: inspectionRows.length > 0 ? 'rows retained for inspection readonly review' : 'rows fallback to readonly skeleton',
          tone: inspectionRows.length > 0 ? 'success' : 'info',
        },
        {
          key: 'blocked-rows',
          label: 'blocked rows',
          value: toCountLabel(blockedRows.length),
          hint: blockedRows.length > 0 ? 'receive/settlement blocked rows retained' : 'write path remains frozen by default',
          tone: blockedRows.length > 0 ? 'warning' : 'info',
        },
      ],
      parityLines: [
        { key: 'route', label: 'route', value: params.finalPath, tone: 'info' },
        { key: 'scope', label: 'readonly scope', value: 'subcontract inspection guard', tone: active ? 'warning' : 'info' },
        {
          key: 'parity',
          label: 'parity',
          value: params.parity === 'material-purchase' ? 'material-purchase linked' : 'subcontract-local',
          tone: params.parity === 'material-purchase' ? 'success' : 'info',
        },
        { key: 'write-boundary', label: 'write boundary', value: 'receive/issue/settlement/export locked', tone: 'warning' },
      ],
      blockedReasons,
      readonlyGuardText: buildReadonlyGuardText('list', params.parity, active),
      inspectionItems:
        params.rows.length > 0
          ? params.rows.slice(0, 4).map((row) => {
              const itemStatus = parseListItemStatus(row)
              return {
                key: `${row.id}`,
                title: `${row.subcontract_no} / ${row.item_code}`,
                owner: row.supplier || 'subcontract-list',
                source: row.process_name || 'inspection',
                status: itemStatus.label,
                tone: itemStatus.tone,
                summary: `验货 ${toNumber(row.inspected_qty)} / 合格 ${toNumber(row.accepted_qty)} / 不良 ${toNumber(row.rejected_qty)}`,
                details: [
                  `计划/发料/回料/验收=${toNumber(row.planned_qty)}/${toNumber(row.issued_qty)}/${toNumber(row.received_qty)}/${toNumber(row.accepted_qty)}`,
                  `销售订单=${row.sales_order || '-'} / 工单=${row.work_order || '-'}`,
                  buildListBlockedReason(row),
                ],
              }
            })
          : [
              {
                key: 'inspection-fallback',
                title: 'inspection guard readonly fallback',
                owner: 'subcontract-list',
                source: 'local-readback',
                status: 'readonly snapshot',
                tone: 'info',
                summary: '尚未读取到委外验货明细，保留 inspection guard 只读骨架。',
                details: [
                  'query-state 与 parity 已锁定',
                  '真实收货、发料、结算与导出保持冻结',
                ],
              },
            ],
      remainingGap: buildRemainingGap(),
      disabledActions: subcontractInspectionGuardDisabledActions,
    }
  }

  const buildSubcontractInspectionGuardDetailModel = (params: {
    detail: SubcontractOrderDetailData
    mode: string
    parity: string
    finalPath: string
  }): SubcontractInspectionGuardReadonlyModel => {
    const active = params.mode === 'readonly-inspection'
    const blockedReasons = buildDetailBlockedReasons(params.detail, params.parity)
    const remainingAcceptanceQty = Math.max(
      toNumber(params.detail.received_qty) - toNumber(params.detail.accepted_qty),
      0,
    )

    return {
      routeStateLabel: buildRouteStateLabel(active, 'detail'),
      routeStateTone: active ? 'warning' : 'info',
      parityTagLabel: buildParityTagLabel(params.parity),
      parityTagTone: params.parity === 'material-purchase' ? 'success' : 'info',
      routeLabel: params.finalPath,
      summaryCards: [
        {
          key: 'query-state',
          label: 'query state',
          value: active ? 'readonly-inspection active' : 'detail readonly default',
          hint: params.finalPath,
          tone: active ? 'success' : 'info',
        },
        {
          key: 'parity',
          label: 'material-purchase parity',
          value: params.parity === 'material-purchase' ? 'locked' : 'subcontract readonly',
          hint: params.parity === 'material-purchase' ? 'material-purchase linked detail route' : 'direct subcontract detail route',
          tone: params.parity === 'material-purchase' ? 'success' : 'info',
        },
        {
          key: 'inspection-items',
          label: 'inspection items',
          value: toCountLabel(params.detail.inspections.length),
          hint: params.detail.inspections.length > 0 ? 'inspection rows retained for readonly review' : 'detail fallback to readonly skeleton',
          tone: params.detail.inspections.length > 0 ? 'success' : 'info',
        },
        {
          key: 'blocked-items',
          label: 'blocked hints',
          value: toCountLabel(blockedReasons.length),
          hint: remainingAcceptanceQty > 0 ? 'remaining acceptance gap retained' : 'write path remains frozen by default',
          tone: blockedReasons.length > 2 ? 'warning' : 'info',
        },
      ],
      parityLines: [
        { key: 'route', label: 'route', value: params.finalPath, tone: 'info' },
        { key: 'scope', label: 'readonly scope', value: 'subcontract inspection detail', tone: active ? 'warning' : 'info' },
        {
          key: 'parity',
          label: 'parity',
          value: params.parity === 'material-purchase' ? 'material-purchase linked' : 'subcontract-local',
          tone: params.parity === 'material-purchase' ? 'success' : 'info',
        },
        { key: 'write-boundary', label: 'write boundary', value: 'receive/issue/settlement/export locked', tone: 'warning' },
      ],
      blockedReasons,
      readonlyGuardText: buildReadonlyGuardText('detail', params.parity, active),
      inspectionItems:
        params.detail.inspections.length > 0
          ? params.detail.inspections.slice(0, 4).map((item) => {
              const inspectedQty = toNumber(item.inspected_qty)
              const acceptedQty = toNumber(item.accepted_qty)
              const rejectedQty = toNumber(item.rejected_qty)
              const itemStatus = parseDetailItemStatus(inspectedQty, acceptedQty, rejectedQty)
              return {
                key: `${item.inspection_no}-${item.receipt_batch_no}`,
                title: `${item.inspection_no} / ${item.receipt_batch_no}`,
                owner: 'subcontract-detail',
                source: params.detail.process_name || 'inspection',
                status: itemStatus.label,
                tone: itemStatus.tone,
                summary: `验货 ${inspectedQty} / 合格 ${acceptedQty} / 不良 ${rejectedQty}`,
                details: [
                  `净额=${normalizeString(item.net_amount) || '0'} / 扣款=${normalizeString(item.deduction_amount) || '0'}`,
                  `验货人=${item.inspected_by || 'local-dev'} / 时间=${item.inspected_at || '-'}`,
                  blockedReasons[0] || '写入链路冻结，仅允许只读验货核对',
                ],
              }
            })
          : [
              {
                key: `${params.detail.id}-inspection-fallback`,
                title: `${params.detail.subcontract_no} / 验货只读摘要`,
                owner: 'subcontract-detail',
                source: params.detail.process_name || 'inspection',
                status: remainingAcceptanceQty > 0 ? 'inspection pending' : 'readonly snapshot',
                tone: remainingAcceptanceQty > 0 ? 'warning' : 'info',
                summary: `验货 ${toNumber(params.detail.inspected_qty)} / 合格 ${toNumber(params.detail.accepted_qty)} / 不良 ${toNumber(params.detail.rejected_qty)}`,
                details: [
                  `收货/验收差=${remainingAcceptanceQty}`,
                  `工单=${params.detail.work_order || '-'} / 销售订单=${params.detail.sales_order || '-'}`,
                  blockedReasons[0] || '写入链路冻结，仅允许只读验货核对',
                ],
              },
            ],
      remainingGap: buildRemainingGap(),
      disabledActions: subcontractInspectionGuardDisabledActions,
    }
  }

  return {
    buildSubcontractInspectionGuardDetailModel,
    buildSubcontractInspectionGuardListModel,
  }
}
