import { computed, type ComputedRef } from 'vue'
import type { DashboardSourceStatus } from '@/api/dashboard'
import {
  homeModuleShortcutOwnerByGroup,
  homeModuleShortcutReadonlyGuardActions,
  homeModuleShortcutRemainingGap,
  homeModuleShortcutSourceByGroup,
  homeModuleShortcutWorkflowFlags,
  homeModuleShortcutWorkflowRows,
  type HomeModuleShortcutRouteItem,
  type HomeModuleShortcutStatus,
} from '../constants/homeModuleShortcutFields'

interface ModuleEntryLike {
  name: string
  path: string
  group: string
  desc: string
  status: string
}

interface UseHomeModuleShortcutReadonlyOptions {
  moduleEntries: ComputedRef<ModuleEntryLike[]>
  routePath: ComputedRef<string>
  routeTab: ComputedRef<string>
  sourceStatuses: ComputedRef<DashboardSourceStatus[]>
}

export interface HomeModuleShortcutReadonlyItem {
  key: string
  label: string
  route: string
  group: string
  status: HomeModuleShortcutStatus
  statusLabel: string
  statusTone: 'success' | 'warning'
  sourceBadge: string
  ownerSourceLine: string
  note: string
  blockedReason: string
  actionReason: string
}

export interface HomeModuleShortcutReadonlySummary {
  routeItems: HomeModuleShortcutRouteItem[]
  shortcutItems: HomeModuleShortcutReadonlyItem[]
  workflowRows: typeof homeModuleShortcutWorkflowRows
  workflowFlags: typeof homeModuleShortcutWorkflowFlags
  workflowState: string
  hostBoundary: string
  nextAction: string
  readinessSummary: string
  sourceBadgeSummary: string
  ownerSourceReadonlyLine: string
  blockedReason: string
  guardMessage: string
  remainingGap: string
  activeTabLabel: string
  guardedActions: typeof homeModuleShortcutReadonlyGuardActions
}

const resolveRouteItems = (
  routePath: string,
  routeTab: string,
): HomeModuleShortcutRouteItem[] => [
  {
    key: 'home-baseline',
    label: '首页基线路由',
    route: '/home',
    note: '保留既有首页只读摘要区，W001A 状态面板在同页补齐。',
    active: routePath === '/home' && routeTab !== 'module-shortcuts',
  },
  {
    key: 'module-shortcuts',
    label: 'module-shortcuts 查询态',
    route: '/home?tab=module-shortcuts',
    note: '聚焦 W001A 状态收口、六模块快捷 strip 与 readonly guard。',
    active: routePath === '/home' && routeTab === 'module-shortcuts',
  },
  {
    key: 'dashboard-excluded',
    label: 'dashboard residual 排除',
    route: 'excluded: /dashboard/**',
    note: '明确排除 DashboardOverview.vue 与 module-entry residual，不回流 dashboard 壳。',
    active: false,
  },
]

export const useHomeModuleShortcutReadonly = ({
  moduleEntries,
  routePath,
  routeTab,
  sourceStatuses,
}: UseHomeModuleShortcutReadonlyOptions) => {
  const sourceStatusMap = computed(
    () => new Map(sourceStatuses.value.map((item) => [item.module, item.status])),
  )

  const shortcutItems = computed<HomeModuleShortcutReadonlyItem[]>(() =>
    moduleEntries.value.map((entry) => {
      const owner = homeModuleShortcutOwnerByGroup[entry.group] || '首页只读组'
      const sourceModule = homeModuleShortcutSourceByGroup[entry.group] || 'dashboard_readonly'
      const sourceStatus = sourceStatusMap.value.get(sourceModule) || 'missing'
      const status: HomeModuleShortcutStatus = sourceStatus === 'ok' ? 'ok' : 'warn'
      const sourceBadge = `source:${sourceModule}`
      const blockedReason =
        status === 'ok'
          ? '当前快捷入口仅开放本地只读页面，真实执行链路保持关闭。'
          : `source.${sourceModule}=${sourceStatus}，当前仅保留快捷入口只读说明。`

      return {
        key: entry.path,
        label: entry.name,
        route: entry.path,
        group: entry.group,
        status,
        statusLabel: status === 'ok' ? '只读就绪' : '只读守卫',
        statusTone: status === 'ok' ? 'success' : 'warning',
        sourceBadge,
        ownerSourceLine: `owner=${owner}｜source=${sourceModule}｜entry=${entry.status}`,
        note: entry.desc,
        blockedReason,
        actionReason: '打开 / 执行动作固定禁用，入口仅作为六模块本地可试用只读导航说明。',
      }
    }),
  )

  const routeItems = computed(() => resolveRouteItems(routePath.value, routeTab.value))

  const readinessSummary = computed(() => {
    const readyCount = shortcutItems.value.filter((item) => item.status === 'ok').length
    return `ready=${readyCount}/${shortcutItems.value.length}｜tab=${routeTab.value || 'default'}`
  })

  const sourceBadgeSummary = computed(() => {
    const badges = Array.from(new Set(shortcutItems.value.map((item) => item.sourceBadge)))
    return badges.join(' / ') || 'source:dashboard_readonly'
  })

  const ownerSourceReadonlyLine = computed(() => {
    const owners = Array.from(
      new Set(shortcutItems.value.map((item) => item.ownerSourceLine.split('｜')[0])),
    )
    const sources = Array.from(new Set(shortcutItems.value.map((item) => item.sourceBadge)))
    return `${owners.join(' / ')}｜${sources.join(' / ')}`
  })

  const blockedReason = computed(() => {
    const warnedReasons = shortcutItems.value
      .filter((item) => item.status === 'warn')
      .map((item) => `${item.label}:${item.blockedReason}`)
    const workflowReason =
      'W001A 停在 PARKED_BEFORE_SEAL；DashboardOverview.vue dirty 且与 dashboard module-entry residual 同壳，当前仅允许 /home clean host 收口。'
    if (warnedReasons.length > 0) {
      return `${workflowReason}；${warnedReasons.join('；')}`
    }
    return `${workflowReason} 首页 module shortcuts 仅作六模块只读快捷说明，不开放真实打开 / 执行动作。`
  })

  const activeTabLabel = computed(() =>
    routeTab.value === 'module-shortcuts' ? 'module-shortcuts' : 'home-baseline',
  )

  const guardMessage = computed(
    () =>
      `readonly guard：当前 tab=${activeTabLabel.value}，只允许查看 W001A 状态、模块快捷条、source badges 与 owner/source 说明。`,
  )

  const summary = computed<HomeModuleShortcutReadonlySummary>(() => ({
    routeItems: routeItems.value,
    shortcutItems: shortcutItems.value,
    workflowRows: homeModuleShortcutWorkflowRows,
    workflowFlags: homeModuleShortcutWorkflowFlags,
    workflowState: 'PARKED_BEFORE_SEAL',
    hostBoundary: 'route=/home ｜ host=HomePage.vue ｜ dashboard residual=excluded',
    nextAction: '等待用户裁决 dashboard residual 吸收/还原或另给干净首页宿主边界；W002A 不自动启动。',
    readinessSummary: readinessSummary.value,
    sourceBadgeSummary: sourceBadgeSummary.value,
    ownerSourceReadonlyLine: ownerSourceReadonlyLine.value,
    blockedReason: blockedReason.value,
    guardMessage: guardMessage.value,
    remainingGap: homeModuleShortcutRemainingGap,
    activeTabLabel: activeTabLabel.value,
    guardedActions: homeModuleShortcutReadonlyGuardActions,
  }))

  return {
    homeModuleShortcutReadonlySummary: summary,
  }
}
