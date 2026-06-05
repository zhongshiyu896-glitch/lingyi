import { computed, type Ref } from 'vue'
import type { RouteLocationNormalizedLoaded } from 'vue-router'
import type { DashboardOverviewData, DashboardHomeTodoItem, DashboardSourceStatus } from '@/api/dashboard'
import type { DashboardHealthSummaryData, DashboardHealthSummaryItem } from '@/api/dashboard_readonly'
import {
  DASHBOARD_HEALTH_CHECK_LABELS,
  DASHBOARD_READONLY_ACTIONS,
  DASHBOARD_WORKBENCH_CARD_CONFIGS,
  type DashboardWorkbenchCardConfig,
} from '../constants/dashboardOverviewCards'

type GuardTone = 'success' | 'warning' | 'danger' | 'info'

export interface DashboardSummaryCard {
  key: string
  label: string
  value: string
  note: string
}

export interface DashboardFlowNode {
  name: string
  pending: number
  overdue: number
  owner: string
  flowType: string
}

export interface DashboardExceptionRow {
  code: string
  module: string
  desc: string
  severity: string
  updatedAt: string
}

export interface DashboardWorkbenchCard {
  key: string
  title: string
  description: string
  sourceModule: DashboardWorkbenchCardConfig['sourceModule']
  path: string
  sourceLabel: string
  metricLabel: string
  metricValue: string
  detail: string
  guardLabel: string
  guardTone: GuardTone
  entryDisabled: boolean
  disabledReason: string
  writeGuardLabel: string
}

export interface DashboardTodoSummaryItem {
  key: string
  title: string
  count: number
  statusLabel: string
  tone: GuardTone
  note: string
}

export interface DashboardHealthGuardItem {
  key: string
  label: string
  status: string
  tone: GuardTone
  detail: string
}

export interface DashboardReadonlyActionItem {
  key: string
  label: string
  disabled: true
  reason: string
}

export interface DashboardRouteAliasSummary {
  sourceRoute: string
  finalPath: string
  expectedFinalPath: string
  aliasReason: string
  isAlias: boolean
}

interface UseDashboardWorkbenchReadonlyOptions {
  overviewData: Ref<DashboardOverviewData | null>
  healthSummary: Ref<DashboardHealthSummaryData | null>
  route: RouteLocationNormalizedLoaded
}

const toGuardTone = (status: string): GuardTone => {
  if (status === 'ok' || status === 'ready') return 'success'
  if (status === 'blocked') return 'danger'
  if (status === 'warning' || status === 'warn') return 'warning'
  return 'info'
}

const toTodoTone = (status: string): GuardTone => {
  if (status === 'urgent') return 'danger'
  if (status === 'warning') return 'warning'
  return 'success'
}

const inferFlowType = (label: string): string => {
  if (label.includes('仓') || label.includes('库存')) return '库存'
  if (label.includes('采购')) return '采购'
  if (label.includes('外协')) return '外协'
  return '生产'
}

const resolveStatusLabel = (status: string): string => {
  if (status === 'ok') return '只读可进'
  if (status === 'blocked') return '入口阻断'
  return '受控查看'
}

const resolveTodoNote = (item: DashboardHomeTodoItem): string => {
  if (item.status === 'urgent') {
    return `${item.action_label} 仅保留导航语义，首页不触发催办写入。`
  }
  if (item.status === 'warning') {
    return `${item.title} 需要业务核对，首页仅展示只读提示。`
  }
  return `${item.title} 当前平稳，仅保留只读摘要。`
}

const resolveCardMetric = (
  config: DashboardWorkbenchCardConfig,
  overview: DashboardOverviewData,
  todoMap: Map<string, DashboardHomeTodoItem>,
): { metricLabel: string; metricValue: string; detail: string } => {
  switch (config.metricKind) {
    case 'todo': {
      const todo = config.todoKey ? todoMap.get(config.todoKey) : undefined
      const count = todo?.count ?? 0
      return {
        metricLabel: todo?.title || '待办数',
        metricValue: String(count),
        detail: todo ? `${todo.action_label} 保持只读入口，首页不直接处理业务单据。` : config.description,
      }
    }
    case 'quality_defect':
      return {
        metricLabel: '质检缺陷数',
        metricValue: String(overview.quality.defect_count),
        detail: `质检通过率 ${overview.quality.pass_rate}% ，仅供工作台只读复核。`,
      }
    case 'warehouse_alert':
      return {
        metricLabel: '仓储预警数',
        metricValue: String(overview.warehouse.alert_count),
        detail: `高危 ${overview.warehouse.critical_alert_count} / 警告 ${overview.warehouse.warning_alert_count}，仅开放只读查看。`,
      }
    case 'inventory_warning':
      return {
        metricLabel: '低库存款号',
        metricValue: String(overview.sales_inventory.below_safety_count),
        detail: `补货线 ${overview.sales_inventory.below_reorder_count} 项，仅做补货风险提示。`,
      }
  }
}

export const useDashboardWorkbenchReadonly = ({
  overviewData,
  healthSummary,
  route,
}: UseDashboardWorkbenchReadonlyOptions) => {
  const sourceStatusMap = computed(() => {
    const rows = overviewData.value?.source_status || []
    return rows.reduce<Record<string, DashboardSourceStatus>>((acc, row) => {
      acc[row.module] = row
      return acc
    }, {})
  })

  const healthCheckMap = computed(() => {
    const rows = healthSummary.value?.items || []
    return rows.reduce<Record<string, DashboardHealthSummaryItem>>((acc, row) => {
      acc[row.check_name] = row
      return acc
    }, {})
  })

  const todoMap = computed(() => {
    const rows = overviewData.value?.home_overview?.todo_items || []
    return new Map(rows.map((item) => [item.key, item]))
  })

  const routeAliasSummary = computed<DashboardRouteAliasSummary>(() => {
    const redirectedFrom = (route as RouteLocationNormalizedLoaded & {
      redirectedFrom?: { fullPath?: string } | null
    }).redirectedFrom
    const sourceRoute = redirectedFrom?.fullPath || route.path
    return {
      sourceRoute,
      finalPath: route.path,
      expectedFinalPath: '/dashboard/overview',
      aliasReason: redirectedFrom ? 'existing router alias redirect' : 'primary dashboard route',
      isAlias: sourceRoute !== route.path,
    }
  })

  const readbackSummaryModules = computed<DashboardSummaryCard[]>(() => {
    const overview = overviewData.value
    const statuses = overview?.source_status || []
    const todoCount = (overview?.home_overview?.todo_items || []).reduce((total, item) => total + item.count, 0)
    return [
      ...statuses.map((item) => ({
        key: item.module,
        label: item.module,
        value: item.status,
        note: 'dashboard/workbench 只读聚合',
      })),
      {
        key: 'todo',
        label: 'workbench_todo',
        value: String(todoCount),
        note: '来源：home_overview.todo_items',
      },
      {
        key: 'health',
        label: 'system_health',
        value: String(healthSummary.value?.total || 0),
        note: '来源：/api/system/health/summary',
      },
    ]
  })

  const kpiItems = computed(() => {
    const metricCards = overviewData.value?.home_overview?.metric_cards || []
    return metricCards.map((item) => ({
      label: item.label,
      value: item.unit ? `${item.value}${item.unit}` : item.value,
      trend: item.trend || '只读汇总',
    }))
  })

  const flowNodes = computed<DashboardFlowNode[]>(() => {
    const nodes = overviewData.value?.kanban?.flow_nodes || []
    return nodes.map((node) => ({
      name: node.label,
      pending: node.status === 'completed' ? 0 : 1,
      overdue: node.status === 'active' ? 1 : 0,
      owner: node.route || '只读聚合',
      flowType: inferFlowType(node.label),
    }))
  })

  const exceptionRows = computed<DashboardExceptionRow[]>(() => {
    const overview = overviewData.value
    if (!overview) return []
    const warnings = overview.home_overview?.warnings || []
    const summaries = overview.home_overview?.business_summary || []
    const rows: DashboardExceptionRow[] = warnings.map((item, index) => ({
      code: `WARN-${String(index + 1).padStart(2, '0')}`,
      module: '工作台',
      desc: item,
      severity: '中',
      updatedAt: overview.generated_at,
    }))
    rows.push(
      {
        code: 'INV-01',
        module: '库存',
        desc: summaries[1] || `低于安全库存款号 ${overview.sales_inventory.below_safety_count} 个`,
        severity: Number(overview.sales_inventory.below_safety_count) > 0 ? '高' : '低',
        updatedAt: overview.generated_at,
      },
      {
        code: 'WH-01',
        module: '仓储',
        desc: summaries[3] || `仓储高危预警 ${overview.warehouse.critical_alert_count} 条`,
        severity: Number(overview.warehouse.critical_alert_count) > 0 ? '高' : '低',
        updatedAt: overview.generated_at,
      },
    )
    return rows
  })

  const workbenchCards = computed<DashboardWorkbenchCard[]>(() => {
    const overview = overviewData.value
    if (!overview) return []
    const permissionStatus = healthCheckMap.value.permission_source?.status || 'warn'
    const readonlyStatus = healthCheckMap.value.readonly_contract?.status || 'warn'
    const todoLookup = todoMap.value
    return DASHBOARD_WORKBENCH_CARD_CONFIGS.map((config) => {
      const metric = resolveCardMetric(config, overview, todoLookup)
      const sourceStatus = config.sourceModule === 'system'
        ? healthCheckMap.value.ui_route_present?.status || 'warn'
        : sourceStatusMap.value[config.sourceModule]?.status || 'warn'
      const blocked = readonlyStatus === 'blocked' || sourceStatus === 'blocked'
      const guardStatus = blocked ? 'blocked' : permissionStatus === 'ok' && sourceStatus === 'ok' ? 'ok' : 'warn'
      return {
        key: config.key,
        title: config.title,
        description: config.description,
        sourceModule: config.sourceModule,
        path: config.path,
        sourceLabel: `source=${config.sourceModule} / permission=${permissionStatus}`,
        metricLabel: metric.metricLabel,
        metricValue: metric.metricValue,
        detail: metric.detail,
        guardLabel: resolveStatusLabel(guardStatus),
        guardTone: toGuardTone(guardStatus),
        entryDisabled: blocked,
        disabledReason: blocked
          ? '只读契约或数据源未就绪，入口保持阻断。'
          : '入口只允许只读查看，写动作继续禁用。',
        writeGuardLabel: '写动作禁用',
      }
    })
  })

  const todoSummaryItems = computed<DashboardTodoSummaryItem[]>(() => {
    const rows = overviewData.value?.home_overview?.todo_items || []
    return rows.map((item) => ({
      key: item.key,
      title: item.title,
      count: item.count,
      statusLabel: item.action_label,
      tone: toTodoTone(item.status),
      note: resolveTodoNote(item),
    }))
  })

  const healthGuardItems = computed<DashboardHealthGuardItem[]>(() => {
    const rows = healthSummary.value?.items || []
    return rows.map((item) => ({
      key: item.check_name,
      label: DASHBOARD_HEALTH_CHECK_LABELS[item.check_name] || item.check_name,
      status: item.status,
      tone: toGuardTone(item.status),
      detail: item.check_result,
    }))
  })

  const readonlyActions = computed<DashboardReadonlyActionItem[]>(() => {
    const permissionStatus = healthCheckMap.value.permission_source?.status || 'warn'
    const suffix = permissionStatus === 'ok' ? '当前只读链路正常。' : '当前权限来源为只读/受控模式。'
    return DASHBOARD_READONLY_ACTIONS.map((item) => ({
      key: item.key,
      label: item.label,
      disabled: true,
      reason: `${item.reason}${suffix}`,
    }))
  })

  const sourceReadback = computed(() => {
    const sourceRows = (overviewData.value?.source_status || []).map((item) => `source.${item.module}=${item.status}`)
    const healthRows = (healthSummary.value?.items || []).map((item) => `health.${item.check_name}=${item.status}`)
    const aliasRows = [
      `source_route=${routeAliasSummary.value.sourceRoute}`,
      `final_path=${routeAliasSummary.value.finalPath}`,
    ]
    return [...sourceRows, ...healthRows, ...aliasRows]
  })

  return {
    routeAliasSummary,
    readbackSummaryModules,
    kpiItems,
    flowNodes,
    exceptionRows,
    workbenchCards,
    todoSummaryItems,
    healthGuardItems,
    readonlyActions,
    sourceReadback,
  }
}
