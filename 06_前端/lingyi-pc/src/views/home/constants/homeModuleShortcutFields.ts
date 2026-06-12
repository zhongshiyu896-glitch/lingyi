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

export interface HomeModuleShortcutWorkflowRow {
  key: string
  label: string
  status: string
  tone: 'success' | 'warning' | 'info'
  note: string
  detail: string
}

export interface HomeModuleShortcutWorkflowFlag {
  key: string
  label: string
  value: string
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

export const homeModuleShortcutWorkflowRows: HomeModuleShortcutWorkflowRow[] = [
  {
    key: 'w001a-state',
    label: 'W001A 当前状态',
    status: 'PARKED_BEFORE_SEAL',
    tone: 'warning',
    note: '首页状态面板已切到 /home 干净宿主，当前只做只读收口，不宣告 SEALED。',
    detail: 'Home status panel 必须与 dashboard module-entry residual 分离，保持用户裁决前 parked。',
  },
  {
    key: 'cand04',
    label: 'WRITE-CAND-04',
    status: 'committed / pushed',
    tone: 'success',
    note: '工票 register / reversal / batch 浏览器验收修复已提交并推送。',
    detail: 'W001A-04 已完成，首页只读取状态结论，不再回流 workshop 写链路。',
  },
  {
    key: 'cand05',
    label: 'WRITE-CAND-05',
    status: 'committed / pushed / REG PASS',
    tone: 'success',
    note: '基础资料客户/供应商 local draft 写闭环已提交并补齐回归证据。',
    detail: 'detail.last_synced_at 风险已标记 unrelated_to_w001a_05，不阻断当前首页状态面板收口。',
  },
  {
    key: 'cand01',
    label: 'WRITE-CAND-01',
    status: 'parked non-blocking',
    tone: 'warning',
    note: '质检写闭环 allowlist 命中现有 dirty overlap，保持 parked。',
    detail: '不释放 parked blocker，不把 quality dirty 伪装成已完成。',
  },
  {
    key: 'cand02',
    label: 'WRITE-CAND-02',
    status: 'parked non-blocking',
    tone: 'warning',
    note: '外发前端写闭环存在 SubcontractOrderList.vue 与后端 dirty 前置未处置。',
    detail: '当前只保留 parked 说明，不进入新的实现或证据循环。',
  },
  {
    key: 'cand03',
    label: 'WRITE-CAND-03',
    status: 'parked non-blocking',
    tone: 'warning',
    note: 'WarehouseDashboard.vue 当前 dirty，且命中 CAND550 warehouse residual。',
    detail: '首页状态面板不得吸收、还原或复活仓库/dashboard residual。',
  },
  {
    key: 'home-host',
    label: 'Home status panel',
    status: 'clean host = /home',
    tone: 'info',
    note: '当前宿主固定为 HomePage.vue，明确排除 DashboardOverview.vue 和 dashboard 壳。',
    detail: '后续如进入回归或收口，只允许沿 /home clean host 推进，不得回流 dashboard。',
  },
]

export const homeModuleShortcutWorkflowFlags: HomeModuleShortcutWorkflowFlag[] = [
  {
    key: 'no-new-candidate-pool',
    label: '新候选池',
    value: 'disabled',
    reason: 'W001A 收口阶段不再生成新候选池，首页面板只反映既有 committed/parked 状态。',
  },
  {
    key: 'no-w002a',
    label: 'W002A',
    value: 'not started',
    reason: '未收到 TASK-W002A-PRODUCTION-READINESS 裁决文件前，不自动启动下一主线。',
  },
  {
    key: 'no-release-parked',
    label: 'parked blockers',
    value: 'kept',
    reason: 'WRITE-CAND-01/02/03 继续保持 parked non-blocking，不在首页状态面板阶段释放。',
  },
  {
    key: 'no-dashboard-absorb',
    label: 'dashboard residual',
    value: 'excluded',
    reason: 'DashboardOverview.vue 及 module-entry residual 只做排除说明，不吸收、不还原、不复用。',
  },
]

export const homeModuleShortcutRemainingGap =
  'W001A 仍停在 PARKED_BEFORE_SEAL；首页状态面板只做 /home clean host 收口，不开放新候选池、W002A、dashboard residual 吸收或 parked blocker 释放。'
