import {
  DASHBOARD_READONLY_SOURCE_LAYER,
  DASHBOARD_WORKBENCH_REMAINING_GAP,
} from '@/api/dashboard_readonly'

export type DashboardModuleEntryStatusSource = 'dashboard' | 'sales_inventory' | 'warehouse' | 'system'

export interface DashboardModuleEntryFieldConfig {
  key: string
  label: string
  path: string
  sourceModule: string
  sourceRoute: string
  sourceDescription: string
  entrySemantic: string
  blockedReasonHint: string
  statusSource: DashboardModuleEntryStatusSource
  healthCheckName?: string
}

export interface DashboardModuleEntryReadonlyActionConfig {
  key: string
  label: string
  reason: string
}

export const DASHBOARD_MODULE_ENTRY_FIELDS: DashboardModuleEntryFieldConfig[] = [
  {
    key: 'dashboard_overview',
    label: '首页/工作台入口',
    path: '/dashboard/overview',
    sourceModule: 'dashboard',
    sourceRoute: '/dashboard/workplace -> /dashboard/overview',
    sourceDescription: '来源：dashboard overview alias，只读核对首页/工作台入口语义和概览入口可达性。',
    entrySemantic: '首页/工作台入口语义',
    blockedReasonHint: '工作台入口仅开放只读概览，不退回非模块入口说明或弱联动占位区域。',
    statusSource: 'dashboard',
  },
  {
    key: 'foundation_references',
    label: '基础资料',
    path: '/sales-inventory/references',
    sourceModule: 'foundation',
    sourceRoute: '/foundation/customer ; /foundation/supplier -> /sales-inventory/references',
    sourceDescription: '来源：基础资料 parity redirect，只读核对客户/供应商基础资料入口是否可达。',
    entrySemantic: '基础资料只读入口',
    blockedReasonHint: '基础资料入口仅开放只读 parity drilldown，不开放真实资料维护。',
    statusSource: 'system',
    healthCheckName: 'ui_route_present',
  },
  {
    key: 'style_profit',
    label: '物料开发',
    path: '/reports/style-profit',
    sourceModule: 'style_profit',
    sourceRoute: '/reports/style-profit',
    sourceDescription: '来源：款式利润快照入口，只读核对物料开发口径差异与来源说明入口。',
    entrySemantic: '物料开发只读入口',
    blockedReasonHint: '物料开发入口只开放快照解释，不开放利润回写或委外执行。',
    statusSource: 'system',
    healthCheckName: 'system_router_mapping',
  },
  {
    key: 'workshop_tickets',
    label: '大货管理',
    path: '/workshop/tickets',
    sourceModule: 'workshop',
    sourceRoute: '/workshop/tickets',
    sourceDescription: '来源：工票列表入口，只读核对大货管理入口和同步阻断说明。',
    entrySemantic: '大货管理只读入口',
    blockedReasonHint: '大货管理入口不开放工票登记、批量导入或同步写链路。',
    statusSource: 'system',
    healthCheckName: 'system_router_mapping',
  },
  {
    key: 'factory_statement',
    label: '物料采购',
    path: '/factory-statements/list',
    sourceModule: 'factory_statement',
    sourceRoute: '/foundation/factory -> /factory-statements/list',
    sourceDescription: '来源：工厂对账入口，只读核对物料采购入口和支付/打印守卫。',
    entrySemantic: '物料采购只读入口',
    blockedReasonHint: '物料采购入口不开放支付状态回写、打印执行或导出链路。',
    statusSource: 'system',
    healthCheckName: 'ui_route_present',
  },
  {
    key: 'warehouse',
    label: '物料进销存',
    path: '/warehouse',
    sourceModule: 'warehouse',
    sourceRoute: '/warehouse',
    sourceDescription: '来源：仓库看板入口，只读核对仓储追溯链和导出诊断入口。',
    entrySemantic: '物料进销存只读入口',
    blockedReasonHint: '物料进销存入口不开放真实库存写入、导出执行或 worker 链路。',
    statusSource: 'warehouse',
  },
]

export const DASHBOARD_MODULE_ENTRY_READONLY_ACTIONS: DashboardModuleEntryReadonlyActionConfig[] = [
  {
    key: 'approve',
    label: '审批',
    reason: '入口矩阵仅支持只读入口与守卫说明，审批动作保持禁用。',
  },
  {
    key: 'export',
    label: '导出',
    reason: '导出能力必须留在业务模块内处理，此处只保留入口守卫，不开放执行链路。',
  },
  {
    key: 'cross_module_execute',
    label: '跨模块执行',
    reason: '跨模块执行必须在业务模块内完成，此处仅保留 disabled/readonly guard。',
  },
]

export {
  DASHBOARD_READONLY_SOURCE_LAYER,
  DASHBOARD_WORKBENCH_REMAINING_GAP as DASHBOARD_MODULE_ENTRY_REMAINING_GAP,
}
