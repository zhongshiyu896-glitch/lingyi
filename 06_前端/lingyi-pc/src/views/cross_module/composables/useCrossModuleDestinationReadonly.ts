import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import {
  CROSS_MODULE_DESTINATION_ACTIONS,
  CROSS_MODULE_DESTINATION_GUARD_MESSAGE,
  CROSS_MODULE_DESTINATION_MATRIX_FIELDS,
  CROSS_MODULE_DESTINATION_REMAINING_GAP,
  CROSS_MODULE_DESTINATION_ROUTE_LABELS,
  type CrossModuleDestinationGuardedAction,
  type CrossModuleDestinationTagType,
} from '../constants/crossModuleDestinationFields'

type GuardTone = CrossModuleDestinationTagType

export interface CrossModuleDestinationReadonlyRow {
  key: string
  title: string
  routeLabel: string
  modules: string[]
  sourceDescription: string
  blockedReason: string
  note: string
  statusLabel: string
  statusTone: GuardTone
  queryStateLabel: string
}

export interface CrossModuleDestinationReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  matrixRows: CrossModuleDestinationReadonlyRow[]
  guardedActions: Array<CrossModuleDestinationGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  queryStateLabel: string
  activeTabLabel: string
  blockedReason: string
  blockedReasonDetail: string
  guardMessage: string
  remainingGap: string
}

interface UseCrossModuleDestinationReadonlyOptions {
  canRead: MaybeRef<boolean>
  queryTab: MaybeRef<string>
  activeTab: MaybeRef<'work_order' | 'sales_order'>
}

const resolveQueryStateLabel = (queryTab: string): string => {
  if (queryTab === 'module-availability') return CROSS_MODULE_DESTINATION_ROUTE_LABELS.moduleAvailabilityRoute
  return CROSS_MODULE_DESTINATION_ROUTE_LABELS.defaultRoute
}

const resolveActiveTabLabel = (activeTab: 'work_order' | 'sales_order'): string => {
  return activeTab === 'sales_order' ? '销售-库存-质量' : '生产-库存-质量'
}

export const useCrossModuleDestinationReadonly = ({
  canRead,
  queryTab,
  activeTab,
}: UseCrossModuleDestinationReadonlyOptions): {
  crossModuleDestinationReadonlySummary: ComputedRef<CrossModuleDestinationReadonlySummary>
} => {
  const crossModuleDestinationReadonlySummary = computed<CrossModuleDestinationReadonlySummary>(() => {
    const readable = Boolean(unref(canRead))
    const normalizedQueryTab = String(unref(queryTab) || '').trim()
    const currentActiveTab = unref(activeTab)
    const queryStateLabel = resolveQueryStateLabel(normalizedQueryTab)
    const activeTabLabel = resolveActiveTabLabel(currentActiveTab)

    const tags = [
      {
        key: 'source',
        label: `${CROSS_MODULE_DESTINATION_ROUTE_LABELS.sourceLabel}: ${queryStateLabel}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: CROSS_MODULE_DESTINATION_ROUTE_LABELS.readonlyMode,
        type: 'success' as GuardTone,
      },
      {
        key: 'query',
        label:
          normalizedQueryTab === 'module-availability'
            ? 'module-availability query'
            : 'cross-module default route',
        type: normalizedQueryTab === 'module-availability' ? ('warning' as GuardTone) : ('info' as GuardTone),
      },
      {
        key: 'active',
        label: `active_tab=${activeTabLabel}`,
        type: 'success' as GuardTone,
      },
    ]

    const matrixRows = CROSS_MODULE_DESTINATION_MATRIX_FIELDS.map((field) => ({
      key: field.key,
      title: field.title,
      routeLabel: field.routeLabel,
      modules: field.modules,
      sourceDescription: field.sourceDescription,
      blockedReason: field.blockedReason,
      note: field.note,
      statusLabel: !readable
        ? '权限受限，只读回退'
        : field.key === currentActiveTab
          ? '当前只读查看'
          : '只读可切换',
      statusTone: !readable
        ? ('danger' as GuardTone)
        : field.key === currentActiveTab
          ? ('success' as GuardTone)
          : ('warning' as GuardTone),
      queryStateLabel:
        normalizedQueryTab === 'module-availability'
          ? CROSS_MODULE_DESTINATION_ROUTE_LABELS.queryStateLabel
          : 'default',
    }))

    return {
      tags,
      matrixRows,
      guardedActions: CROSS_MODULE_DESTINATION_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: queryStateLabel,
      readonlyModeLabel: CROSS_MODULE_DESTINATION_ROUTE_LABELS.readonlyMode,
      queryStateLabel,
      activeTabLabel,
      blockedReason: !readable
        ? 'blocked_reason=当前账号缺少 sales_inventory:read 或 quality:read，仅允许 cross-module 只读回退。'
        : 'blocked_reason=真实跨模块执行、导出、同步、后台修复与 ERPNext/outbox/worker 全部保持关闭。',
      blockedReasonDetail:
        normalizedQueryTab === 'module-availability'
          ? `dashboard alias 预期落点=${CROSS_MODULE_DESTINATION_ROUTE_LABELS.moduleAvailabilityRoute}`
          : '当前切片仅展示 CrossModuleView 去向矩阵，不承接 dashboard 六模块入口 guard 语义。',
      guardMessage: CROSS_MODULE_DESTINATION_GUARD_MESSAGE,
      remainingGap: CROSS_MODULE_DESTINATION_REMAINING_GAP,
    }
  })

  return {
    crossModuleDestinationReadonlySummary,
  }
}
