import type { SubcontractSettlementReadonlyCode, SubcontractTimelineStatus } from '@/api/subcontract_readback'

export type SubcontractReadonlyTagType = 'primary' | 'success' | 'warning' | 'info' | 'danger'

export type SubcontractMilestoneKey = 'issue' | 'receipt' | 'inspection' | 'settlement'

export const SUBCONTRACT_MILESTONE_LABELS: Record<SubcontractMilestoneKey, string> = {
  issue: '发料节点',
  receipt: '收货节点',
  inspection: '验货节点',
  settlement: '结算观察',
}

export const SUBCONTRACT_TIMELINE_STATUS_LABELS: Record<SubcontractTimelineStatus, string> = {
  pending: '待回读',
  active: '进行中',
  success: '已完成',
  blocked: '阻断',
}

export const SUBCONTRACT_TIMELINE_STATUS_TAGS: Record<SubcontractTimelineStatus, SubcontractReadonlyTagType> = {
  pending: 'info',
  active: 'primary',
  success: 'success',
  blocked: 'danger',
}

export const SUBCONTRACT_SETTLEMENT_LABELS: Record<SubcontractSettlementReadonlyCode, string> = {
  pending: '待结算观察',
  ready: '可结算观察',
  locked: '已锁定观察',
  blocked: '异常阻断',
}

export const SUBCONTRACT_SETTLEMENT_TAGS: Record<SubcontractSettlementReadonlyCode, SubcontractReadonlyTagType> = {
  pending: 'info',
  ready: 'warning',
  locked: 'success',
  blocked: 'danger',
}
