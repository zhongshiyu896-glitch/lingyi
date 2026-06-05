import { computed, type ComputedRef, type Ref } from 'vue'
import type { DashboardHomeTodoItem, DashboardOverviewData } from '@/api/dashboard'
import type { DashboardHealthSummaryData } from '@/api/dashboard_readonly'
import {
  DASHBOARD_READONLY_SOURCE_LAYER,
  DASHBOARD_TODO_FIELDS,
  DASHBOARD_TODO_READONLY_ACTIONS,
  DASHBOARD_TODO_REMAINING_GAP,
  type DashboardTodoFieldConfig,
} from '../constants/dashboardTodoReadonlyFields'
import type { DashboardRouteAliasSummary } from './useDashboardWorkbenchReadonly'

type GuardTone = 'success' | 'warning' | 'danger' | 'info'

export interface DashboardTodoReadonlyItem {
  key: string
  title: string
  count: number
  statusLabel: string
  statusTone: GuardTone
  entrySource: string
  sourceModule: string
  sourceRoute: string
  sourceDescription: string
  overdueBucket: string
  agingStatus: string
  blockedReason: string
  note: string
}

export interface DashboardTodoReadonlyActionItem {
  key: string
  label: string
  disabled: true
  reason: string
}

interface UseDashboardTodoReadonlyOptions {
  overviewData: Ref<DashboardOverviewData | null>
  healthSummary: Ref<DashboardHealthSummaryData | null>
  routeAliasSummary: ComputedRef<DashboardRouteAliasSummary>
}

const toTodoMap = (rows: DashboardHomeTodoItem[]) => new Map(rows.map((item) => [item.key, item]))

const toTone = (status: string): GuardTone => {
  if (status === 'ok' || status === 'normal') return 'success'
  if (status === 'blocked') return 'danger'
  if (status === 'warning' || status === 'warn' || status === 'urgent') return 'warning'
  return 'info'
}

const resolveTodoStatusLabel = (todo: DashboardHomeTodoItem): string => {
  if (todo.status === 'urgent') return '超期待核对'
  if (todo.status === 'warning') return '待处理待核对'
  return '只读平稳'
}

const resolveOverdueBucket = (todo: DashboardHomeTodoItem): string => {
  if (todo.status === 'urgent') return 'urgent'
  if (todo.status === 'warning') return 'attention'
  return 'stable'
}

const resolveAgingStatus = (todo: DashboardHomeTodoItem, guardStatus: string): string => {
  if (guardStatus === 'blocked') return '入口阻断'
  if (todo.status === 'urgent') return '只读跟进'
  if (todo.status === 'warning') return '只读待核对'
  return '只读平稳'
}

const resolveSourceStatus = (
  field: DashboardTodoFieldConfig,
  sourceStatusMap: Record<string, string>,
  readonlyStatus: string,
): string => {
  if (field.sourceModule === 'dashboard') return readonlyStatus
  return sourceStatusMap[field.sourceModule] || 'warn'
}

const resolveEntrySource = (
  field: DashboardTodoFieldConfig,
  routeAliasSummary: DashboardRouteAliasSummary,
): string => {
  if (field.sourceModule === 'dashboard') return routeAliasSummary.sourceRoute
  return `${field.entrySource} -> ${field.sourceRoute}`
}

const resolveBlockedReason = (
  todo: DashboardHomeTodoItem,
  guardStatus: string,
  sourceStatus: string,
): string => {
  if (guardStatus === 'blocked') {
    return `blocked_reason=source_status_${sourceStatus}_blocked，首页仅保留只读 drilldown。`
  }
  if (todo.status === 'urgent') {
    return `blocked_reason=${todo.action_label} 仅保留导航语义，首页不触发催办写入。`
  }
  if (todo.status === 'warning') {
    return `blocked_reason=${todo.title} 需要业务核对，首页只保留只读入口。`
  }
  return 'blocked_reason=dashboard readonly drilldown only'
}

export const useDashboardTodoReadonly = ({
  overviewData,
  healthSummary,
  routeAliasSummary,
}: UseDashboardTodoReadonlyOptions) => {
  const sourceStatusMap = computed(() => {
    const rows = overviewData.value?.source_status || []
    return rows.reduce<Record<string, string>>((acc, row) => {
      acc[row.module] = row.status
      return acc
    }, {})
  })

  const healthCheckMap = computed(() => {
    const rows = healthSummary.value?.items || []
    return rows.reduce<Record<string, string>>((acc, row) => {
      acc[row.check_name] = row.status
      return acc
    }, {})
  })

  const dashboardTodoAgingItems = computed<DashboardTodoReadonlyItem[]>(() => {
    const overview = overviewData.value
    if (!overview) return []

    const readonlyStatus = healthCheckMap.value.readonly_contract || 'warn'
    const permissionStatus = healthCheckMap.value.permission_source || 'warn'
    const todoMap = toTodoMap(overview.home_overview?.todo_items || [])

    return DASHBOARD_TODO_FIELDS.map((field) => {
      const todo =
        todoMap.get(field.key) || {
          key: field.key,
          title: field.title,
          count: 0,
          status: 'normal',
          action_label: '只读查看',
        }
      const sourceStatus = resolveSourceStatus(field, sourceStatusMap.value, readonlyStatus)
      const guardStatus =
        readonlyStatus === 'blocked' || sourceStatus === 'blocked'
          ? 'blocked'
          : permissionStatus === 'ok' && sourceStatus === 'ok'
            ? 'ok'
            : 'warn'
      return {
        key: field.key,
        title: field.title,
        count: todo.count,
        statusLabel: resolveTodoStatusLabel(todo),
        statusTone: toTone(todo.status === 'normal' ? guardStatus : todo.status),
        entrySource: resolveEntrySource(field, routeAliasSummary.value),
        sourceModule: field.sourceModule,
        sourceRoute: field.sourceRoute,
        sourceDescription: field.sourceDescription,
        overdueBucket: resolveOverdueBucket(todo),
        agingStatus: resolveAgingStatus(todo, guardStatus),
        blockedReason: resolveBlockedReason(todo, guardStatus, sourceStatus),
        note: `${todo.action_label} / source.${field.sourceModule}=${sourceStatus} / final_path=${routeAliasSummary.value.finalPath}`,
      }
    })
  })

  const dashboardTodoReadonlyActions = computed<DashboardTodoReadonlyActionItem[]>(() => {
    return DASHBOARD_TODO_READONLY_ACTIONS.map((item) => ({
      key: item.key,
      label: item.label,
      disabled: true,
      reason: `${item.reason}${DASHBOARD_TODO_REMAINING_GAP}`,
    }))
  })

  return {
    dashboardTodoAgingItems,
    dashboardTodoReadonlyActions,
    dashboardTodoRemainingGap: computed(() => DASHBOARD_TODO_REMAINING_GAP),
    dashboardTodoSourceLayer: computed(() => DASHBOARD_READONLY_SOURCE_LAYER),
  }
}
