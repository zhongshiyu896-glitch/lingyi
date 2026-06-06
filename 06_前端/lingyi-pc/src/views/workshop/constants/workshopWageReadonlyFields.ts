export type WorkshopWageReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export interface WorkshopWageReadonlyMetricField {
  key: 'rateCount' | 'activeRateCount' | 'globalRateCount' | 'blockedActionCount'
  label: string
}

export interface WorkshopWageReadonlyGuardedAction {
  key:
    | 'create'
    | 'deactivate'
    | 'import'
    | 'export'
    | 'worker'
    | 'refresh-permission'
    | 'reload-module-actions'
  label: string
  reason: string
}

export const WORKSHOP_WAGE_READONLY_METRIC_FIELDS: WorkshopWageReadonlyMetricField[] = [
  { key: 'rateCount', label: '工价条数' },
  { key: 'activeRateCount', label: 'active 条数' },
  { key: 'globalRateCount', label: '通用工价条数' },
  { key: 'blockedActionCount', label: '阻断动作数' },
]

export const WORKSHOP_WAGE_READONLY_GUARDED_ACTIONS: WorkshopWageReadonlyGuardedAction[] = [
  {
    key: 'create',
    label: '新增工价',
    reason: '当前仅开放工价档案只读摘要，不开放真实工价维护创建。',
  },
  {
    key: 'deactivate',
    label: '停用工价',
    reason: '当前仅开放工价状态核对，不开放真实停用执行。',
  },
  {
    key: 'import',
    label: '导入工价',
    reason: '当前仅开放 readonly-wage 查询态，不开放工价导入。',
  },
  {
    key: 'export',
    label: '导出工价',
    reason: '当前仅开放工价档案只读摘要，不开放导出执行。',
  },
  {
    key: 'worker',
    label: 'worker / ERPNext',
    reason: '当前仅开放只读边界，不开放 outbox、worker、ERPNext 或跨模块执行。',
  },
  {
    key: 'refresh-permission',
    label: '刷新权限',
    reason: '当前工价档案页面处于 readonly-wage 边界，权限刷新入口仅保留只读提示，不执行真实刷新动作。',
  },
  {
    key: 'reload-module-actions',
    label: '重载模块动作',
    reason: '当前工价档案页面仅核对只读边界，模块动作重载入口保持禁用，不执行真实重载。',
  },
]

export const WORKSHOP_WAGE_READONLY_ROUTE_LABELS = {
  defaultRoute: '/workshop/wage-rates',
  parityRoute: '/workshop/wage-rates?tab=readonly-wage&parity=production-order',
  focusRoute: '/workshop/wage-rates?tab=readonly-wage&parity=production-order&focus=rate-source',
  sourceLabel: 'readonly-wage 来源',
  readonlyMode: 'WORKSHOP_WAGE_GET_ONLY',
} as const

export const WORKSHOP_WAGE_READONLY_GUARD_MESSAGE =
  '当前仅开放工价档案、production-order parity 与 rate-source focus 核对，不开放真实工价维护、导入、导出、worker、ERPNext 或跨模块执行。'

export const WORKSHOP_WAGE_READONLY_REMAINING_GAP =
  'remaining_gap=真实工价维护、导入、导出、outbox、worker、ERPNext 与跨模块执行链路未开放；仅保留 readonly-wage query state、rate item/status、blocked reason 与 parity 镜像。'

export const WORKSHOP_WAGE_READONLY_WRITE_BOUNDARY =
  'create / deactivate / import / export / worker / refresh-permission / reload-module-actions disabled'
