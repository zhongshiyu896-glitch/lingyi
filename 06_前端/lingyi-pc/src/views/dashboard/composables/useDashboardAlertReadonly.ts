import { computed, type ComputedRef, type Ref } from 'vue'
import type { DashboardHomeTodoItem, DashboardOverviewData, DashboardSourceStatus } from '@/api/dashboard'
import type { DashboardHealthSummaryData } from '@/api/dashboard_readonly'
import {
  DASHBOARD_ALERT_BLOCKED_REASON,
  DASHBOARD_ALERT_FIELDS,
  DASHBOARD_ALERT_READONLY_FOCUS,
  DASHBOARD_ALERT_READONLY_GUARD,
  DASHBOARD_ALERT_READONLY_PARITY,
  DASHBOARD_ALERT_READONLY_TAB,
  DASHBOARD_ALERT_READONLY_ACTIONS,
  DASHBOARD_ALERT_REMAINING_GAP,
  DASHBOARD_READONLY_SOURCE_LAYER,
  type DashboardAlertFieldConfig,
} from '../constants/dashboardAlertFields'
import type { DashboardRouteAliasSummary } from './useDashboardWorkbenchReadonly'

type GuardTone = 'success' | 'warning' | 'danger' | 'info'

export interface DashboardAlertReadonlyItem {
  key: string
  title: string
  statusLabel: string
  statusTone: GuardTone
  sourceModule: string
  sourceRoute: string
  sourceDescription: string
  evidenceSummary: string
  auditSummary: string
  processingStatus: string
  processingTone: GuardTone
  remainingGap: string
}

export interface DashboardAlertAuditItem {
  key: string
  label: string
  sourceRoute: string
  sourceTag: string
  statusLabel: string
  statusTone: GuardTone
  note: string
}

export interface DashboardAlertReadonlyActionItem {
  key: string
  label: string
  disabled: true
  reason: string
}

export interface DashboardAlertReadonlySectionSummary {
  queryStateLabel: string
  parityLabel: string
  focusLabel: string
  blockedReason: string
  readonlyGuard: string
  remainingGap: string
}

interface UseDashboardAlertReadonlyOptions {
  overviewData: Ref<DashboardOverviewData | null>
  healthSummary: Ref<DashboardHealthSummaryData | null>
  routeAliasSummary: ComputedRef<DashboardRouteAliasSummary>
  queryTab: ComputedRef<string>
  queryParity: ComputedRef<string>
  queryFocus: ComputedRef<string>
}

const toTone = (status: string): GuardTone => {
  if (status === 'ok' || status === 'ready') return 'success'
  if (status === 'blocked') return 'danger'
  if (status === 'warning' || status === 'warn') return 'warning'
  return 'info'
}

const toTodoMap = (rows: DashboardHomeTodoItem[]) => new Map(rows.map((item) => [item.key, item]))

const resolveSourceStatus = (module: string, rows: DashboardSourceStatus[]): string => {
  return rows.find((item) => item.module === module)?.status || 'warn'
}

const resolveAlertMetric = (
  config: DashboardAlertFieldConfig,
  overview: DashboardOverviewData,
  todoMap: Map<string, DashboardHomeTodoItem>,
): {
  statusLabel: string
  statusTone: GuardTone
  evidenceSummary: string
} => {
  const warnings = overview.home_overview?.warnings || []
  const summaries = overview.home_overview?.business_summary || []
  const warningText = config.warningIndex !== undefined ? warnings[config.warningIndex] : undefined
  const summaryText = config.summaryIndex !== undefined ? summaries[config.summaryIndex] : undefined

  if (config.sourceModule === 'quality') {
    const defectCount = Number(overview.quality.defect_count)
    return {
      statusLabel: defectCount > 0 ? '需复核' : '只读正常',
      statusTone: defectCount > 0 ? 'warning' : 'success',
      evidenceSummary:
        warningText ||
        summaryText ||
        `质检缺陷 ${defectCount} 条，通过率 ${overview.quality.pass_rate}% 。`,
    }
  }

  if (config.sourceModule === 'sales_inventory') {
    const overdueCount = config.todoKey ? todoMap.get(config.todoKey)?.count ?? 0 : 0
    const safetyCount = Number(overview.sales_inventory.below_safety_count)
    const statusTone: GuardTone = overdueCount > 0 || safetyCount > 0 ? 'warning' : 'success'
    return {
      statusLabel: overdueCount > 0 ? '超期待核对' : safetyCount > 0 ? '库存预警' : '只读正常',
      statusTone,
      evidenceSummary:
        warningText ||
        summaryText ||
        `订单超期 ${overdueCount} 项，低于安全库存 ${safetyCount} 项。`,
    }
  }

  const critical = Number(overview.warehouse.critical_alert_count)
  const warning = Number(overview.warehouse.warning_alert_count)
  return {
    statusLabel: critical > 0 ? '高危告警' : warning > 0 ? '预警待核对' : '只读正常',
    statusTone: critical > 0 ? 'danger' : warning > 0 ? 'warning' : 'success',
    evidenceSummary:
      warningText ||
      summaryText ||
      `仓储高危 ${critical} 条，普通预警 ${warning} 条。`,
  }
}

export const useDashboardAlertReadonly = ({
  overviewData,
  healthSummary,
  routeAliasSummary,
  queryTab,
  queryParity,
  queryFocus,
}: UseDashboardAlertReadonlyOptions) => {
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

  const dashboardAlertItems = computed<DashboardAlertReadonlyItem[]>(() => {
    const overview = overviewData.value
    if (!overview) return []

    const todoMap = toTodoMap(overview.home_overview?.todo_items || [])
    const readonlyStatus = healthCheckMap.value.readonly_contract || 'warn'
    const permissionStatus = healthCheckMap.value.permission_source || 'warn'

    return DASHBOARD_ALERT_FIELDS.map((field) => {
      const metric = resolveAlertMetric(field, overview, todoMap)
      const sourceStatus = sourceStatusMap.value[field.sourceModule] || 'warn'
      const guardStatus =
        readonlyStatus === 'blocked' || sourceStatus === 'blocked'
          ? 'blocked'
          : permissionStatus === 'ok' && sourceStatus === 'ok'
            ? 'ok'
            : 'warn'
      return {
        key: field.key,
        title: field.title,
        statusLabel: metric.statusLabel,
        statusTone: metric.statusTone,
        sourceModule: field.sourceModule,
        sourceRoute: field.sourceRoute,
        sourceDescription: field.sourceDescription,
        evidenceSummary: metric.evidenceSummary,
        auditSummary: `source.${field.sourceModule}=${sourceStatus} / final_path=${routeAliasSummary.value.finalPath}`,
        processingStatus: guardStatus === 'ok' ? '只读可钻取' : guardStatus === 'blocked' ? '入口阻断' : '受控查看',
        processingTone: toTone(guardStatus),
        remainingGap: DASHBOARD_ALERT_REMAINING_GAP,
      }
    })
  })

  const dashboardAlertAuditItems = computed<DashboardAlertAuditItem[]>(() => {
    const readonlyStatus = healthCheckMap.value.readonly_contract || 'warn'
    const permissionStatus = healthCheckMap.value.permission_source || 'warn'

    const sourceItems = DASHBOARD_ALERT_FIELDS.map((field) => {
      const sourceStatus = sourceStatusMap.value[field.sourceModule] || 'warn'
      return {
        key: field.key,
        label: field.title,
        sourceRoute: field.sourceRoute,
        sourceTag: `source=${DASHBOARD_READONLY_SOURCE_LAYER}.${field.sourceModule}`,
        statusLabel: sourceStatus,
        statusTone: toTone(sourceStatus),
        note: field.sourceDescription,
      }
    })

    sourceItems.push({
      key: 'dashboard_route_contract',
      label: 'dashboard route contract',
      sourceRoute: routeAliasSummary.value.finalPath,
      sourceTag: `source=${DASHBOARD_READONLY_SOURCE_LAYER}.route`,
      statusLabel: routeAliasSummary.value.finalPath === routeAliasSummary.value.expectedFinalPath ? 'ok' : 'warn',
      statusTone:
        routeAliasSummary.value.finalPath === routeAliasSummary.value.expectedFinalPath ? 'success' : 'warning',
      note: `permission_source=${permissionStatus} / readonly_contract=${readonlyStatus}`,
    })

    return sourceItems
  })

  const dashboardAlertReadonlyActions = computed<DashboardAlertReadonlyActionItem[]>(() => {
    return DASHBOARD_ALERT_READONLY_ACTIONS.map((item) => ({
      key: item.key,
      label: item.label,
      disabled: true,
      reason: `${item.reason}${DASHBOARD_ALERT_REMAINING_GAP}`,
    }))
  })

  const dashboardAlertReadonlySectionSummary = computed<DashboardAlertReadonlySectionSummary>(() => ({
    queryStateLabel: `tab=${queryTab.value || DASHBOARD_ALERT_READONLY_TAB}; parity=${queryParity.value || DASHBOARD_ALERT_READONLY_PARITY}; focus=${queryFocus.value || DASHBOARD_ALERT_READONLY_FOCUS}`,
    parityLabel: queryParity.value || DASHBOARD_ALERT_READONLY_PARITY,
    focusLabel: queryFocus.value || DASHBOARD_ALERT_READONLY_FOCUS,
    blockedReason: DASHBOARD_ALERT_BLOCKED_REASON,
    readonlyGuard: DASHBOARD_ALERT_READONLY_GUARD,
    remainingGap: DASHBOARD_ALERT_REMAINING_GAP,
  }))

  return {
    dashboardAlertItems,
    dashboardAlertAuditItems,
    dashboardAlertReadonlyActions,
    dashboardAlertReadonlySectionSummary,
    dashboardAlertRemainingGap: computed(() => DASHBOARD_ALERT_REMAINING_GAP),
    dashboardAlertSourceLayer: computed(() => DASHBOARD_READONLY_SOURCE_LAYER),
  }
}
