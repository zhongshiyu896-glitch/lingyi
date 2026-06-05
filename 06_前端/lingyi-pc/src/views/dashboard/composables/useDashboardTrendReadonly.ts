import { computed, type ComputedRef, type Ref } from 'vue'
import type { DashboardHomeTrendPoint, DashboardOverviewData } from '@/api/dashboard'
import type { DashboardHealthSummaryData } from '@/api/dashboard_readonly'
import {
  DASHBOARD_READONLY_SOURCE_LAYER,
  DASHBOARD_TREND_FIELDS,
  DASHBOARD_TREND_READONLY_ACTIONS,
  DASHBOARD_TREND_REMAINING_GAP,
  type DashboardTrendFieldConfig,
} from '../constants/dashboardTrendReadonlyFields'
import type { DashboardRouteAliasSummary } from './useDashboardWorkbenchReadonly'

type GuardTone = 'success' | 'warning' | 'danger' | 'info'

export interface DashboardTrendWindowItem {
  key: string
  label: string
  value: string
  note: string
}

export interface DashboardTrendFreshnessItem {
  key: string
  label: string
  statusLabel: string
  statusTone: GuardTone
  latestRefresh: string
  staleIndicator: string
  note: string
  freshnessExplanation: string
}

export interface DashboardTrendReadonlyActionItem {
  key: string
  label: string
  disabled: true
  reason: string
}

interface UseDashboardTrendReadonlyOptions {
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

const resolveStatusLabel = (status: string): string => {
  if (status === 'ok') return '新鲜'
  if (status === 'blocked') return '陈旧阻断'
  return '待核对'
}

const resolveStaleIndicator = (status: string): string => {
  if (status === 'ok') return 'stale_indicator=fresh'
  if (status === 'blocked') return 'stale_indicator=blocked'
  return 'stale_indicator=review'
}

const resolveTrendRange = (overview: DashboardOverviewData): string => {
  const points = overview.home_overview?.trend_points || []
  const firstPoint = points[0]
  const lastPoint = points[points.length - 1]
  const start = overview.from_date || firstPoint?.period || overview.generated_at
  const end = overview.to_date || lastPoint?.period || overview.generated_at
  return `${start} ~ ${end}`
}

const resolveTrendSampleNote = (points: DashboardHomeTrendPoint[]): string => {
  if (points.length === 0) return 'trend_points=0，当前以 overview.generated_at 展示只读时窗。'
  return `trend_points=${points.length}，趋势窗口保持只读钻取。`
}

const resolveLatestRefresh = (
  field: DashboardTrendFieldConfig,
  overview: DashboardOverviewData,
  healthSummary: DashboardHealthSummaryData | null,
): string => {
  if (field.sourceModule === 'system') {
    return healthSummary?.generated_at || overview.generated_at
  }
  return overview.generated_at
}

export const useDashboardTrendReadonly = ({
  overviewData,
  healthSummary,
  routeAliasSummary,
}: UseDashboardTrendReadonlyOptions) => {
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

  const dashboardTrendWindowItems = computed<DashboardTrendWindowItem[]>(() => {
    const overview = overviewData.value
    if (!overview) return []
    const points = overview.home_overview?.trend_points || []
    const healthRefresh = healthSummary.value?.generated_at || 'health summary unavailable'
    const freshnessGap =
      healthSummary.value?.generated_at && healthSummary.value.generated_at === overview.generated_at
        ? '双源同步'
        : '双源需核对'

    return [
      {
        key: 'trend_window',
        label: '趋势时窗',
        value: resolveTrendRange(overview),
        note: resolveTrendSampleNote(points),
      },
      {
        key: 'overview_refresh',
        label: '业务刷新时间',
        value: overview.generated_at,
        note: `company=${overview.company} / final_path=${routeAliasSummary.value.finalPath}`,
      },
      {
        key: 'health_refresh',
        label: '健康刷新时间',
        value: healthRefresh,
        note: '来源：/api/system/health/summary，只读核对 dashboard 读侧健康时间。',
      },
      {
        key: 'freshness_gap',
        label: '来源时效',
        value: freshnessGap,
        note: '当 source_status 非 ok 时，仅允许只读核对，不启用业务动作。',
      },
    ]
  })

  const dashboardTrendFreshnessItems = computed<DashboardTrendFreshnessItem[]>(() => {
    const overview = overviewData.value
    if (!overview) return []

    return DASHBOARD_TREND_FIELDS.map((field) => {
      const sourceStatus =
        field.sourceModule === 'system'
          ? healthCheckMap.value[field.healthCheckName || 'readonly_contract'] || 'warn'
          : sourceStatusMap.value[field.sourceModule] || 'warn'
      const latestRefresh = resolveLatestRefresh(field, overview, healthSummary.value)
      return {
        key: field.key,
        label: field.label,
        statusLabel: resolveStatusLabel(sourceStatus),
        statusTone: toTone(sourceStatus),
        latestRefresh,
        staleIndicator: resolveStaleIndicator(sourceStatus),
        note: field.sourceDescription,
        freshnessExplanation:
          sourceStatus === 'ok'
            ? `latest_refresh=${latestRefresh}，当前来源仅开放只读钻取。`
            : `latest_refresh=${latestRefresh}，来源状态=${sourceStatus}，请在业务模块内复核。`,
      }
    })
  })

  const dashboardTrendRefreshExplanation = computed(() => {
    const overview = overviewData.value
    const trendRange = overview ? resolveTrendRange(overview) : 'overview pending'
    const healthRefresh = healthSummary.value?.generated_at || 'health summary unavailable'
    return `趋势窗口使用 ${trendRange}，业务刷新时间以 ${overview?.generated_at || 'overview pending'} 为准，系统健康时间以 ${healthRefresh} 为准。若来源状态为 warn/blocked，则仅允许只读核对，不启用审批、导出或跨模块执行。`
  })

  const dashboardTrendReadonlyActions = computed<DashboardTrendReadonlyActionItem[]>(() => {
    return DASHBOARD_TREND_READONLY_ACTIONS.map((item) => ({
      key: item.key,
      label: item.label,
      disabled: true,
      reason: `${item.reason}${DASHBOARD_TREND_REMAINING_GAP}`,
    }))
  })

  return {
    dashboardTrendWindowItems,
    dashboardTrendFreshnessItems,
    dashboardTrendRefreshExplanation,
    dashboardTrendReadonlyActions,
    dashboardTrendRemainingGap: computed(() => DASHBOARD_TREND_REMAINING_GAP),
    dashboardTrendSourceLayer: computed(() => DASHBOARD_READONLY_SOURCE_LAYER),
  }
}
