export type CrossModuleDestinationTagType = 'success' | 'warning' | 'danger' | 'info'

export interface CrossModuleDestinationMatrixField {
  key: 'work_order' | 'sales_order'
  title: string
  routeLabel: string
  modules: string[]
  sourceDescription: string
  blockedReason: string
  note: string
}

export interface CrossModuleDestinationGuardedAction {
  key: 'execute' | 'export' | 'sync'
  label: string
  reason: string
}

export const CROSS_MODULE_DESTINATION_MATRIX_FIELDS: CrossModuleDestinationMatrixField[] = [
  {
    key: 'work_order',
    title: '生产-库存-质量去向',
    routeLabel: '/cross-module/view#work_order',
    modules: ['生产', '库存', '质量'],
    sourceDescription: '按工单链路核对库存流水和质量检验事实，不开放写入执行。',
    blockedReason: 'blocked_reason=仅允许工单链路只读核对，不开放跨模块执行、导出、同步或后台修复。',
    note: '适用于生产工单进入库存与质量事实的只读去向矩阵。',
  },
  {
    key: 'sales_order',
    title: '销售-库存-质量去向',
    routeLabel: '/cross-module/view#sales_order',
    modules: ['销售', '库存', '质量'],
    sourceDescription: '按销售链路核对交付出库和质量检验事实，不开放写入执行。',
    blockedReason: 'blocked_reason=仅允许销售链路只读核对，不开放跨模块执行、导出、同步或后台修复。',
    note: '适用于销售订单进入库存与质量事实的只读去向矩阵。',
  },
]

export const CROSS_MODULE_DESTINATION_ACTIONS: CrossModuleDestinationGuardedAction[] = [
  {
    key: 'execute',
    label: '真实执行',
    reason: '当前仅允许入口去向矩阵核对，不开放真实跨模块执行。',
  },
  {
    key: 'export',
    label: '导出快照',
    reason: '当前仅允许 readonly matrix 浏览，不开放导出执行。',
  },
  {
    key: 'sync',
    label: '同步链路',
    reason: '当前仅允许 GET-only 查询，不开放同步或后台修复。',
  },
]

export const CROSS_MODULE_DESTINATION_ROUTE_LABELS = {
  defaultRoute: '/cross-module/view',
  moduleAvailabilityRoute: '/cross-module/view?tab=module-availability',
  dashboardEntryAlias: '/dashboard/overview?entry=module-availability',
  readonlyMode: 'CROSS_MODULE_DESTINATION_GET_ONLY',
  queryStateLabel: 'module-availability',
  sourceLabel: '去向矩阵来源',
} as const

export const CROSS_MODULE_DESTINATION_GUARD_MESSAGE =
  '当前仅开放 CrossModule 去向矩阵与只读 guard 核对，不开放真实跨模块执行、导出、同步、后台修复或 ERPNext/outbox/worker。'

export const CROSS_MODULE_DESTINATION_REMAINING_GAP =
  'remaining_gap=真实跨模块执行、导出、同步、后台修复与 ERPNext/outbox/worker 未开放；去向矩阵和 blocked reason 仍需人工核对。'
