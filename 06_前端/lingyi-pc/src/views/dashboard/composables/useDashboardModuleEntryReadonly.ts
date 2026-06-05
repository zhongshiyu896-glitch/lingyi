import { computed, type ComputedRef, type Ref } from 'vue'
import type { DashboardOverviewData } from '@/api/dashboard'
import type { DashboardHealthSummaryData } from '@/api/dashboard_readonly'
import {
  DASHBOARD_MODULE_ENTRY_FIELDS,
  DASHBOARD_MODULE_ENTRY_READONLY_ACTIONS,
  DASHBOARD_MODULE_ENTRY_REMAINING_GAP,
  DASHBOARD_READONLY_SOURCE_LAYER,
  type DashboardModuleEntryFieldConfig,
} from '../constants/dashboardModuleEntryFields'
import type { DashboardRouteAliasSummary } from './useDashboardWorkbenchReadonly'

type GuardTone = 'success' | 'warning' | 'danger' | 'info'

export interface DashboardModuleEntryReadonlyItem {
  key: string
  label: string
  path: string
  sourceModule: string
  sourceRoute: string
  sourceDescription: string
  entrySemantic: string
  reachabilityLabel: string
  reachabilityTone: GuardTone
  guardLabel: string
  guardTone: GuardTone
  entryDisabled: boolean
  blockedReason: string
  note: string
}

export interface DashboardModuleEntryReadonlyActionItem {
  key: string
  label: string
  disabled: true
  reason: string
}

interface UseDashboardModuleEntryReadonlyOptions {
  overviewData: Ref<DashboardOverviewData | null>
  healthSummary: Ref<DashboardHealthSummaryData | null>
  routeAliasSummary: ComputedRef<DashboardRouteAliasSummary>
}

const toTone = (status: string): GuardTone => {
  if (status === 'ok') return 'success'
  if (status === 'blocked') return 'danger'
  if (status === 'warning' || status === 'warn') return 'warning'
  return 'info'
}

const resolveStatus = (
  field: DashboardModuleEntryFieldConfig,
  sourceStatusMap: Record<string, string>,
  healthCheckMap: Record<string, string>,
): string => {
  if (field.statusSource === 'system') {
    return healthCheckMap[field.healthCheckName || 'ui_route_present'] || 'warn'
  }
  return sourceStatusMap[field.statusSource] || 'warn'
}

const resolveReachabilityLabel = (routeStatus: string): string => {
  if (routeStatus === 'ok') return 'reachable'
  if (routeStatus === 'blocked') return 'route_blocked'
  return 'route_guarded'
}

const resolveGuardLabel = (guardStatus: string): string => {
  if (guardStatus === 'ok') return 'readonly_enter'
  if (guardStatus === 'blocked') return 'entry_blocked'
  return 'guarded_readonly'
}

const resolveBlockedReason = (
  field: DashboardModuleEntryFieldConfig,
  guardStatus: string,
  sourceStatus: string,
  routeStatus: string,
): string => {
  if (guardStatus === 'blocked') {
    return `blocked_reason=${field.key}_${sourceStatus}_${routeStatus}_blocked，仅保留只读入口说明。`
  }
  return `blocked_reason=${field.key}_readonly_guard，${field.blockedReasonHint}`
}

export const useDashboardModuleEntryReadonly = ({
  overviewData,
  healthSummary,
  routeAliasSummary,
}: UseDashboardModuleEntryReadonlyOptions) => {
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

  const dashboardModuleEntryItems = computed<DashboardModuleEntryReadonlyItem[]>(() => {
    const readonlyStatus = healthCheckMap.value.readonly_contract || 'warn'
    const permissionStatus = healthCheckMap.value.permission_source || 'warn'
    const routeStatus =
      healthCheckMap.value.ui_route_present || healthCheckMap.value.system_router_mapping || 'warn'

    return DASHBOARD_MODULE_ENTRY_FIELDS.map((field) => {
      const sourceStatus = resolveStatus(field, sourceStatusMap.value, healthCheckMap.value)
      const guardStatus =
        readonlyStatus === 'blocked' || permissionStatus === 'blocked' || sourceStatus === 'blocked'
          ? 'blocked'
          : readonlyStatus === 'ok' && permissionStatus === 'ok' && routeStatus === 'ok'
            ? 'ok'
            : 'warn'

      return {
        key: field.key,
        label: field.label,
        path: field.path,
        sourceModule: field.sourceModule,
        sourceRoute: field.sourceRoute,
        sourceDescription: field.sourceDescription,
        entrySemantic: field.entrySemantic,
        reachabilityLabel: resolveReachabilityLabel(routeStatus),
        reachabilityTone: toTone(routeStatus),
        guardLabel: resolveGuardLabel(guardStatus),
        guardTone: toTone(guardStatus),
        entryDisabled: guardStatus === 'blocked',
        blockedReason: resolveBlockedReason(field, guardStatus, sourceStatus, routeStatus),
        note: `path=${field.path} / source_route=${field.sourceRoute} / final_path=${routeAliasSummary.value.finalPath}`,
      }
    })
  })

  const dashboardModuleEntryReadonlyActions = computed<DashboardModuleEntryReadonlyActionItem[]>(() => {
    return DASHBOARD_MODULE_ENTRY_READONLY_ACTIONS.map((item) => ({
      key: item.key,
      label: item.label,
      disabled: true,
      reason: `${item.reason}${DASHBOARD_MODULE_ENTRY_REMAINING_GAP}`,
    }))
  })

  return {
    dashboardModuleEntryItems,
    dashboardModuleEntryReadonlyActions,
    dashboardModuleEntryRemainingGap: computed(() => DASHBOARD_MODULE_ENTRY_REMAINING_GAP),
    dashboardModuleEntrySourceLayer: computed(() => DASHBOARD_READONLY_SOURCE_LAYER),
  }
}
