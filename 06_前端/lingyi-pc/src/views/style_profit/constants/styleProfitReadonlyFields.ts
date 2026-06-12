export type StyleProfitReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'

export interface StyleProfitSnapshotReadonlyMetricField {
  key: 'snapshotCount' | 'sourceMapCount' | 'unresolvedCount' | 'guardedActionCount'
  label: string
}

export interface StyleProfitSnapshotReadonlyGuardedAction {
  key:
    | 'recalculate'
    | 'export'
    | 'submit'
    | 'erpnext-worker'
    | 'refresh-permission'
    | 'reload-module-actions'
  label: string
  reason: string
}

export type StyleProfitListMetricKey =
  | 'snapshotCount'
  | 'mappedCount'
  | 'unresolvedCount'
  | 'profitRange'

export type StyleProfitDetailMetricKey =
  | 'detailCount'
  | 'sourceMapCount'
  | 'unresolvedCount'
  | 'coverage'

export const STYLE_PROFIT_LIST_METRIC_FIELDS = [
  { key: 'snapshotCount', label: '快照数量' },
  { key: 'mappedCount', label: '已映射来源' },
  { key: 'unresolvedCount', label: '待复核来源' },
  { key: 'profitRange', label: '利润区间' },
] as const satisfies ReadonlyArray<{ key: StyleProfitListMetricKey; label: string }>

export const STYLE_PROFIT_DETAIL_METRIC_FIELDS = [
  { key: 'detailCount', label: '明细行数' },
  { key: 'sourceMapCount', label: '来源映射' },
  { key: 'unresolvedCount', label: '未解析来源' },
  { key: 'coverage', label: '纳入利润' },
] as const satisfies ReadonlyArray<{ key: StyleProfitDetailMetricKey; label: string }>

export const STYLE_PROFIT_SNAPSHOT_READONLY_METRIC_FIELDS: StyleProfitSnapshotReadonlyMetricField[] = [
  { key: 'snapshotCount', label: '快照条数' },
  { key: 'sourceMapCount', label: '来源映射' },
  { key: 'unresolvedCount', label: '待复核来源' },
  { key: 'guardedActionCount', label: '阻断动作数' },
]

export const STYLE_PROFIT_PARITY_SCOPE_LABELS: Record<string, string> = {
  '': '款式利润主入口',
  'style-profit': '款式利润主入口',
  default: '款式利润主入口',
}

export const STYLE_PROFIT_REVENUE_STATUS_LABELS: Record<string, string> = {
  actual_first: '实际优先',
  actual_only: '仅实际',
  estimated_only: '仅预估',
}

export const STYLE_PROFIT_SNAPSHOT_STATUS_LABELS: Record<string, string> = {
  complete: '已完成',
  incomplete: '待复核',
}

export const STYLE_PROFIT_ALLOCATION_STATUS_LABELS: Record<string, string> = {
  mapped: '来源已映射',
  partial: '部分映射',
  unresolved: '存在未解析',
  pending: '待补齐来源',
}

export const STYLE_PROFIT_SOURCE_TYPE_LABELS: Record<string, string> = {
  BOM: 'BOM 成本',
  WORK_ORDER: '工单成本',
  STOCK_LEDGER: '库存成本',
  SUBCONTRACT: '外协成本',
  MaterialSnapshot: '物料快照',
  JobCard: '工序工单',
}

export const STYLE_PROFIT_SOURCE_STATUS_LABELS: Record<string, string> = {
  mapped: '已映射',
  partial: '部分映射',
  unresolved: '待复核',
  submitted: '已登记',
  draft: '草稿',
  cancelled: '已取消',
}

export const STYLE_PROFIT_WRITE_BOUNDARY_LABEL = 'ERPNext / 结果传递 / 真实利润写入 disabled'

export const STYLE_PROFIT_REMAINING_GAP_LABEL =
  '未开放结果传递、ERPNext、真实利润写入、outbox、worker、生产/库存联动写链路。'

export const STYLE_PROFIT_SNAPSHOT_READONLY_ROUTE_LABELS = {
  defaultRoute: '/reports/style-profit',
  parityRoute: '/reports/style-profit?tab=snapshot-readonly&parity=style-profit',
  focusRoute: '/reports/style-profit/detail?mode=readonly-source&parity=style-profit&focus=source-map',
  sourceLabel: 'snapshot-readonly 来源',
  readonlyMode: 'STYLE_PROFIT_GET_ONLY',
} as const

export const STYLE_PROFIT_READONLY_GUARD_REASON_MAP = {
  archive: '当前仅开放 snapshot-readonly 只读核对，不开放真实归档落库。',
  clear: '当前仅开放 snapshot-readonly 只读核对，不开放真实清空操作。',
  confirm: '当前仅开放 snapshot-readonly 只读核对，不开放真实确认落库。',
  export: '当前仅开放 snapshot/source-map 只读核对，不开放真实结果传递。',
  columnSetting: '当前仅开放 snapshot-readonly 只读核对，不开放真实列设置写入。',
  resetColumn: '当前仅开放 snapshot-readonly 只读核对，不开放真实列配置重置。',
  markRead: '当前仅开放 snapshot-readonly 只读核对，不开放真实标记已读落库。',
  deleteMsg: '当前仅开放 snapshot-readonly 只读核对，不开放真实消息删除。',
  addMsg: '当前仅开放 snapshot-readonly 只读核对，不开放真实新增消息。',
  save: '当前仅开放 snapshot/source-map 只读核对，不开放真实状态落库。',
  cancel: '当前仅开放 snapshot-readonly 只读核对，不开放真实取消落库。',
  print: '当前仅开放 snapshot/source-map 只读核对，不开放真实结果输出。',
  writeAction: '当前仅开放 snapshot/source-map 只读核对，不开放真实写动作执行。',
  recalculate: '当前仅开放 snapshot-readonly 只读核对，不开放真实利润改写。',
  submit: '当前仅开放 snapshot/source-map 只读核对，不开放真实结果落库。',
  erpnextWorker: '当前仅开放只读边界，不开放 ERPNext、outbox、worker 或生产写入执行。',
  refreshPermission: '当前款式利润页面处于 snapshot-readonly 边界，权限刷新入口仅保留只读提示，不执行真实刷新动作。',
  reloadModuleActions: '当前款式利润页面仅核对 snapshot/source-map 只读边界，模块动作重载入口保持禁用，不执行真实重载。',
} as const

export const STYLE_PROFIT_SNAPSHOT_READONLY_GUARDED_ACTIONS: StyleProfitSnapshotReadonlyGuardedAction[] = [
  {
    key: 'recalculate',
    label: '利润核对',
    reason: STYLE_PROFIT_READONLY_GUARD_REASON_MAP.recalculate,
  },
  {
    key: 'export',
    label: '结果视图',
    reason: STYLE_PROFIT_READONLY_GUARD_REASON_MAP.export,
  },
  {
    key: 'submit',
    label: '只读说明',
    reason: STYLE_PROFIT_READONLY_GUARD_REASON_MAP.submit,
  },
  {
    key: 'erpnext-worker',
    label: 'ERPNext / outbox / worker',
    reason: STYLE_PROFIT_READONLY_GUARD_REASON_MAP.erpnextWorker,
  },
  {
    key: 'refresh-permission',
    label: '刷新权限',
    reason: STYLE_PROFIT_READONLY_GUARD_REASON_MAP.refreshPermission,
  },
  {
    key: 'reload-module-actions',
    label: '重载模块动作',
    reason: STYLE_PROFIT_READONLY_GUARD_REASON_MAP.reloadModuleActions,
  },
]

export const STYLE_PROFIT_SNAPSHOT_READONLY_GUARD_MESSAGE =
  '当前仅开放 snapshot-readonly、style-profit parity 与 source-map focus 核对，不开放真实利润改写、结果传递、结果落库、ERPNext、outbox、worker 或生产写入执行。'

export const STYLE_PROFIT_SNAPSHOT_READONLY_REMAINING_GAP =
  'remaining_gap=真实利润改写、结果传递、结果落库、ERPNext、outbox、worker 与生产写链路未开放；仅保留 snapshot-readonly query state、source-map、blocked reason 与 style-profit parity 镜像。'

export const STYLE_PROFIT_SNAPSHOT_READONLY_WRITE_BOUNDARY =
  'recalculate / export / submit / ERPNext / worker / refresh-permission / reload-module-actions disabled'
