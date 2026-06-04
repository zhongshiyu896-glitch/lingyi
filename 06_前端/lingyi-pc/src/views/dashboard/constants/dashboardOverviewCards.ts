export interface DashboardWorkbenchCardConfig {
  key: string
  title: string
  description: string
  path: string
  sourceModule: 'quality' | 'sales_inventory' | 'warehouse' | 'system'
  metricKind: 'todo' | 'quality_defect' | 'warehouse_alert' | 'inventory_warning'
  todoKey?: string
}

export interface DashboardReadonlyActionConfig {
  key: string
  label: string
  reason: string
}

export const DASHBOARD_WORKBENCH_CARD_CONFIGS: DashboardWorkbenchCardConfig[] = [
  {
    key: 'quality_review',
    title: '质检复核',
    description: '来源于质检汇总与缺陷统计，只开放只读核对入口。',
    path: '/quality/inspections',
    sourceModule: 'quality',
    metricKind: 'quality_defect',
  },
  {
    key: 'overdue_orders',
    title: '大货订单跟进',
    description: '来源于经营总览待办与订单超期统计，保留只读进入。',
    path: '/sales-inventory/sales-orders',
    sourceModule: 'sales_inventory',
    metricKind: 'todo',
    todoKey: 'overdue_orders',
  },
  {
    key: 'warehouse_warning',
    title: '仓储预警',
    description: '来源于仓储预警与库存安全阈值，只开放只读查看。',
    path: '/warehouse',
    sourceModule: 'warehouse',
    metricKind: 'warehouse_alert',
    todoKey: 'warehouse_warning',
  },
  {
    key: 'inventory_warning',
    title: '低库存核对',
    description: '来源于库存安全线与补货线统计，用于只读追踪补货风险。',
    path: '/sales-inventory/stock-ledger',
    sourceModule: 'sales_inventory',
    metricKind: 'inventory_warning',
  },
]

export const DASHBOARD_READONLY_ACTIONS: DashboardReadonlyActionConfig[] = [
  {
    key: 'create',
    label: '新建草稿',
    reason: '工作台只保留入口守卫和只读摘要，不在首页发起业务创建。',
  },
  {
    key: 'update',
    label: '更新状态',
    reason: '状态变更必须在对应业务模块处理，工作台仅展示守卫状态。',
  },
  {
    key: 'delete',
    label: '删除记录',
    reason: '删除动作保持 fail-closed，避免首页误触写链路。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '导出能力不在本切片启用，避免退回纯证据任务。',
  },
]

export const DASHBOARD_HEALTH_CHECK_LABELS: Record<string, string> = {
  permission_source: '权限来源',
  system_router_mapping: '系统路由映射',
  ui_route_present: '工作台路由可见',
  readonly_contract: '只读契约',
}
