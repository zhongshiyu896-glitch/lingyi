import { computed, type ComputedRef, type Ref } from 'vue'
import type { DashboardHealthSummaryData } from '@/api/dashboard_readonly'
import {
  DASHBOARD_READONLY_SOURCE_LAYER,
  DASHBOARD_WORKBENCH_READONLY_FIELDS,
  DASHBOARD_WORKBENCH_REMAINING_GAP,
} from '../constants/dashboardWorkbenchFields'
import type { DashboardRouteAliasSummary, DashboardWorkbenchCard } from './useDashboardWorkbenchReadonly'

type GuardTone = 'success' | 'warning' | 'danger' | 'info'

export interface DashboardCrossModuleReadonlyItem {
  key: string
  label: string
  routeLabel: string
  sourceTag: string
  statusLabel: string
  statusTone: GuardTone
  guardLabel: string
  guardTone: GuardTone
  summary: string
}

interface UseDashboardCrossModuleReadonlyOptions {
  workbenchCards: Ref<DashboardWorkbenchCard[]>
  healthSummary: Ref<DashboardHealthSummaryData | null>
  routeAliasSummary: ComputedRef<DashboardRouteAliasSummary>
}

const toTone = (status: string): GuardTone => {
  if (status === 'ok') return 'success'
  if (status === 'blocked') return 'danger'
  if (status === 'warning' || status === 'warn') return 'warning'
  return 'info'
}

const resolveGuardLabel = (status: string): string => {
  if (status === 'blocked') return 'guard=blocked'
  if (status === 'ok') return 'guard=readonly'
  return 'guard=review'
}

export const useDashboardCrossModuleReadonly = ({
  workbenchCards,
  healthSummary,
  routeAliasSummary,
}: UseDashboardCrossModuleReadonlyOptions) => {
  const healthCheckMap = computed(() => {
    const rows = healthSummary.value?.items || []
    return rows.reduce<Record<string, string>>((acc, row) => {
      acc[row.check_name] = row.status
      return acc
    }, {})
  })

  const crossModuleReadonlyItems = computed<DashboardCrossModuleReadonlyItem[]>(() => {
    const fieldMap = new Map(DASHBOARD_WORKBENCH_READONLY_FIELDS.map((item) => [item.key, item]))
    const readonlyContractStatus = healthCheckMap.value.readonly_contract || 'warn'
    return workbenchCards.value.map((card) => {
      const field = fieldMap.get(card.key)
      const routeStatus =
        routeAliasSummary.value.finalPath === routeAliasSummary.value.expectedFinalPath ? 'ok' : 'warn'
      const guardStatus =
        readonlyContractStatus === 'blocked' || card.entryDisabled
          ? 'blocked'
          : routeStatus === 'ok'
            ? 'ok'
            : 'warn'
      return {
        key: card.key,
        label: field?.label || card.title,
        routeLabel: field?.routeLabel || card.path,
        sourceTag: `source=${field?.sourceTag || `${DASHBOARD_READONLY_SOURCE_LAYER}.${card.sourceModule}`}`,
        statusLabel: card.guardLabel,
        statusTone: card.guardTone,
        guardLabel: resolveGuardLabel(guardStatus),
        guardTone: toTone(guardStatus),
        summary: `${card.metricLabel} ${card.metricValue}；${card.detail}`,
      }
    })
  })

  const remainingGap = computed(() => DASHBOARD_WORKBENCH_REMAINING_GAP)
  const sourceLayer = computed(() => DASHBOARD_READONLY_SOURCE_LAYER)

  return {
    crossModuleReadonlyItems,
    remainingGap,
    sourceLayer,
  }
}
