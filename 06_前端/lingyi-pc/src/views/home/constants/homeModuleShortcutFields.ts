export type HomeModuleShortcutStatus = 'ok' | 'warn'

export interface HomeModuleShortcutRouteItem {
  key: string
  label: string
  route: string
  note: string
  active: boolean
}

export interface HomeModuleShortcutGuardAction {
  key: string
  label: string
  reason: string
}

export const homeModuleShortcutOwnerByGroup: Record<string, string> = {
  基础资料: '基础资料组',
  物料开发: '开发组',
  大货管理: '大货组',
  物料采购: '采购组',
  物料进销存: '仓储组',
}

export const homeModuleShortcutSourceByGroup: Record<string, string> = {
  基础资料: 'sales_inventory',
  物料开发: 'quality',
  大货管理: 'sales_inventory',
  物料采购: 'sales_inventory',
  物料进销存: 'warehouse',
}

export const homeModuleShortcutReadonlyGuardActions: HomeModuleShortcutGuardAction[] = [
  {
    key: 'open-module',
    label: '打开模块',
    reason: '首页 module shortcuts 只展示本地只读去向，不在此处触发真实模块进入动作。',
  },
  {
    key: 'execute-module',
    label: '执行链路',
    reason: '真实模块执行链路保持关闭，避免从首页直接触发业务副作用。',
  },
  {
    key: 'export-sync',
    label: '导出 / 同步',
    reason: '导出、同步与后台修复不属于本切片范围，统一保持 readonly guard。',
  },
]

export const homeModuleShortcutRemainingGap =
  '真实模块执行、导出、同步、后台修复与 ERPNext/outbox/worker 未开放；module shortcuts 仍需人工核对。'
