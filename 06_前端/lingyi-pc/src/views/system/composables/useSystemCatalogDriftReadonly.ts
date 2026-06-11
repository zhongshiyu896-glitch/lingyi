import { computed, type Ref } from 'vue'
import type {
  SystemConfigCatalogItem,
  SystemDictionaryCatalogItem,
  SystemHealthSummaryItem,
} from '@/api/system_management'
import {
  systemCatalogBaselineRoute,
  systemCatalogExpectedConfigGroups,
  systemCatalogExpectedDictionarySources,
  systemCatalogExpectedHealthChecks,
  systemCatalogLegacyRouteAliases,
  systemCatalogReadonlyConfigCatalogRoute,
  systemCatalogReadonlyFocusRoute,
  systemCatalogReadonlyGuardActions,
  systemCatalogRemainingGap,
  type SystemCatalogDriftRow,
  type SystemCatalogDriftRouteItem,
} from '../constants/systemCatalogDriftFields'

interface UseSystemCatalogDriftReadonlyOptions {
  configItems: Ref<SystemConfigCatalogItem[]>
  dictionaryItems: Ref<SystemDictionaryCatalogItem[]>
  healthItems: Ref<SystemHealthSummaryItem[]>
  routeParity: Ref<string>
  routeTab: Ref<string>
  routeFocus: Ref<string>
  canReadConfig: Ref<boolean>
  canReadDictionary: Ref<boolean>
  canReadHealthSummary: Ref<boolean>
}

const statusWeight: Record<SystemCatalogDriftRow['status'], number> = {
  ok: 0,
  warn: 1,
  blocked: 2,
}

const getHigherStatus = (
  left: SystemCatalogDriftRow['status'],
  right: SystemCatalogDriftRow['status'],
): SystemCatalogDriftRow['status'] => (statusWeight[left] >= statusWeight[right] ? left : right)

export const useSystemCatalogDriftReadonly = ({
  configItems,
  dictionaryItems,
  healthItems,
  routeParity,
  routeTab,
  routeFocus,
  canReadConfig,
  canReadDictionary,
  canReadHealthSummary,
}: UseSystemCatalogDriftReadonlyOptions) => {
  const activeParity = computed(() =>
    routeParity.value === 'system-catalog'
      ? routeParity.value
      : routeParity.value === 'foundation-dictionary'
        ? routeParity.value
        : 'default',
  )
  const activeTab = computed(() =>
    routeTab.value === 'catalog-drift-readonly'
      ? routeTab.value
      : routeTab.value === 'catalog-drift'
        ? routeTab.value
        : 'default',
  )
  const activeFocus = computed(() => (routeFocus.value === 'config-catalog' ? routeFocus.value : 'default'))
  const isReadonlyRoute = computed(() => activeTab.value === 'catalog-drift-readonly')
  const effectiveRoute = computed(() =>
    isReadonlyRoute.value && activeFocus.value === 'config-catalog'
      ? systemCatalogReadonlyFocusRoute
      : isReadonlyRoute.value
        ? systemCatalogReadonlyConfigCatalogRoute
        : systemCatalogBaselineRoute,
  )
  const effectiveParity = computed(() =>
    activeParity.value === 'system-catalog'
      ? 'system-catalog'
      : activeParity.value === 'foundation-dictionary'
        ? 'foundation-dictionary (legacy alias)'
        : '/system/management',
  )
  const effectiveTab = computed(() =>
    activeTab.value === 'catalog-drift-readonly'
      ? 'catalog-drift-readonly'
      : activeTab.value === 'catalog-drift'
        ? 'catalog-drift (legacy alias)'
        : 'default',
  )
  const effectiveFocus = computed(() => (activeFocus.value === 'config-catalog' ? activeFocus.value : 'none'))

  const configGroupsPresent = computed(() => new Set(configItems.value.map((item) => item.config_group)))
  const dictionarySourcesPresent = computed(() => new Set(dictionaryItems.value.map((item) => item.source)))
  const dictionaryTypeCount = computed(() => new Set(dictionaryItems.value.map((item) => item.dict_type)).size)
  const healthCheckMap = computed(() => new Map(healthItems.value.map((item) => [item.check_name, item])))

  const missingConfigGroups = computed(() =>
    systemCatalogExpectedConfigGroups.filter((group) => !configGroupsPresent.value.has(group)),
  )
  const missingDictionarySources = computed(() =>
    systemCatalogExpectedDictionarySources.filter((source) => !dictionarySourcesPresent.value.has(source)),
  )
  const missingHealthChecks = computed(() =>
    systemCatalogExpectedHealthChecks.filter((checkName) => !healthCheckMap.value.has(checkName)),
  )

  const blockedHealthChecks = computed(() =>
    healthItems.value.filter((item) => item.status === 'blocked').map((item) => item.check_name),
  )
  const warnedHealthChecks = computed(() =>
    healthItems.value.filter((item) => item.status === 'warn').map((item) => item.check_name),
  )

  const driftRows = computed<SystemCatalogDriftRow[]>(() => {
    const rows: SystemCatalogDriftRow[] = []

    rows.push({
      key: 'config-group-coverage',
      label: '系统配置分组覆盖',
      status: !canReadConfig.value
        ? 'blocked'
        : !configItems.value.length
          ? 'warn'
          : missingConfigGroups.value.length
            ? 'warn'
            : 'ok',
      summary: !canReadConfig.value
        ? '缺少 system:config_read 权限，无法核对配置分组覆盖。'
        : !configItems.value.length
          ? '当前无配置目录数据，无法确认 ui/security/audit/integration 覆盖。'
          : missingConfigGroups.value.length
            ? `缺少配置分组：${missingConfigGroups.value.join(' / ')}`
            : `已覆盖 ${systemCatalogExpectedConfigGroups.join(' / ')} 四类配置分组。`,
      recommendation: '配置目录差异仅作只读核对，真实配置维护需走受控写链路。',
    })

    rows.push({
      key: 'dictionary-source-coverage',
      label: '基础资料字典来源覆盖',
      status: !canReadDictionary.value
        ? 'blocked'
        : !dictionaryItems.value.length
          ? 'warn'
          : missingDictionarySources.value.length
            ? 'warn'
            : 'ok',
      summary: !canReadDictionary.value
        ? '缺少 system:dictionary_read 权限，无法核对基础资料字典来源。'
        : !dictionaryItems.value.length
          ? '当前无字典目录数据，无法确认 static/policy 来源覆盖。'
          : missingDictionarySources.value.length
            ? `缺少字典来源：${missingDictionarySources.value.join(' / ')}`
            : `已覆盖 ${systemCatalogExpectedDictionarySources.join(' / ')}，字典类型数 ${dictionaryTypeCount.value}。`,
      recommendation: '基础资料 parity 仅说明来源差异，不在本切片内触发字典维护。',
    })

    const healthStatus = !canReadHealthSummary.value
      ? 'blocked'
      : !healthItems.value.length
        ? 'warn'
        : missingHealthChecks.value.length || blockedHealthChecks.value.length
          ? 'blocked'
          : warnedHealthChecks.value.length
            ? 'warn'
            : 'ok'

    rows.push({
      key: 'health-drift-summary',
      label: '系统健康差异',
      status: healthStatus,
      summary: !canReadHealthSummary.value
        ? '缺少 system:diagnostic 权限，无法读取健康差异。'
        : !healthItems.value.length
          ? '当前无健康摘要数据，无法核对目录漂移对应的系统差异。'
          : blockedHealthChecks.value.length
            ? `存在 blocked 检查：${blockedHealthChecks.value.join(' / ')}`
            : warnedHealthChecks.value.length
              ? `存在 warn 检查：${warnedHealthChecks.value.join(' / ')}`
              : missingHealthChecks.value.length
                ? `缺少健康检查：${missingHealthChecks.value.join(' / ')}`
                : '健康摘要与只读契约一致，未发现 blocked 差异。',
      recommendation: '健康差异只作只读提示，后台修复和报告生成未开放。',
    })

    rows.push({
      key: 'foundation-parity-scope',
      label: '基础资料 parity 路由上下文',
      status:
        activeParity.value === 'system-catalog' ||
        activeParity.value === 'foundation-dictionary' ||
        activeTab.value === 'catalog-drift-readonly' ||
        activeTab.value === 'catalog-drift' ||
        (!routeParity.value && !routeTab.value)
          ? 'ok'
          : 'warn',
      summary:
        activeParity.value === 'system-catalog'
          ? '当前处于 system-catalog parity 上下文。'
          : activeParity.value === 'foundation-dictionary'
            ? '当前处于 foundation-dictionary legacy parity 上下文。'
          : activeTab.value === 'catalog-drift-readonly'
            ? '当前处于 catalog-drift-readonly 只读核对上下文。'
            : activeTab.value === 'catalog-drift'
              ? '当前处于 catalog-drift legacy 只读核对上下文。'
              : '当前处于 /system/management 基线路由，只读展示基础资料目录漂移摘要。',
      recommendation: '仅允许路由可达性说明与只读核对，不开放真实目录写入或报表动作。',
    })

    rows.push({
      key: 'config-catalog-focus',
      label: 'config-catalog focus',
      status:
        activeFocus.value === 'config-catalog' ||
        (!routeFocus.value && !isReadonlyRoute.value)
          ? 'ok'
          : 'warn',
      summary:
        activeFocus.value === 'config-catalog'
          ? '当前 focus 已锁定 config-catalog。'
          : !routeFocus.value && !isReadonlyRoute.value
            ? '基线路由未要求 config-catalog focus。'
            : '当前处于 /system/management 基线路由，只读展示基础资料目录漂移摘要。',
      recommendation: 'focus 仅用于只读定位，不触发目录维护、报表生成或后台修复。',
    })

    return rows
  })

  const driftStatusSummary = computed(() => {
    const counts = driftRows.value.reduce<Record<SystemCatalogDriftRow['status'], number>>(
      (acc, row) => {
        acc[row.status] += 1
        return acc
      },
      { ok: 0, warn: 0, blocked: 0 },
    )
    return `ok:${counts.ok} / warn:${counts.warn} / blocked:${counts.blocked}`
  })

  const overallStatus = computed<SystemCatalogDriftRow['status']>(() =>
    driftRows.value.reduce<SystemCatalogDriftRow['status']>((status, row) => getHigherStatus(status, row.status), 'ok'),
  )

  const parityRoutes = computed<SystemCatalogDriftRouteItem[]>(() => [
    {
      key: 'baseline-route',
      label: '系统管理基线路由',
      route: systemCatalogBaselineRoute,
      active: !routeParity.value && !routeTab.value,
      note: '默认只读目录与健康摘要入口。',
    },
    {
      key: 'system-catalog',
      label: 'system-catalog parity',
      route: systemCatalogReadonlyConfigCatalogRoute,
      active: activeParity.value === 'system-catalog' && activeTab.value === 'catalog-drift-readonly',
      note: `聚焦基础资料目录来源差异，不释放真实字典维护。兼容旧路由：${systemCatalogLegacyRouteAliases[0]}`,
    },
    {
      key: 'config-catalog-focus',
      label: 'config-catalog focus',
      route: systemCatalogReadonlyFocusRoute,
      active:
        activeParity.value === 'system-catalog' &&
        activeTab.value === 'catalog-drift-readonly' &&
        activeFocus.value === 'config-catalog',
      note: `聚焦目录漂移与健康差异，只读修复建议不可执行。兼容旧路由：${systemCatalogLegacyRouteAliases[1]}`,
    },
  ])

  const readonlyRecommendations = computed(() => {
    const dynamic = driftRows.value
      .filter((row) => row.status !== 'ok')
      .map((row) => `${row.label}：${row.recommendation}`)

    return dynamic.length
      ? dynamic
      : [
          '当前目录与健康摘要未发现 blocked 差异，后续仍需通过受控链路执行真实目录维护或配置写入。',
          '基础资料 parity 仅用于说明来源差异和健康状态，不替代后台修复。',
        ]
  })

  const blockedReason = computed(() => {
    if (!canReadConfig.value || !canReadDictionary.value || !canReadHealthSummary.value) {
      return '缺少系统目录只读核对权限，当前仅保留 readonly guard、query state 与 parity/focus 说明。'
    }
    if (blockedHealthChecks.value.length) {
      return `存在 blocked 健康检查：${blockedHealthChecks.value.join(' / ')}；目录维护、配置写入、报表生成、导出、remediation、outbox/worker 与 production write 保持禁用。`
    }
    if (missingConfigGroups.value.length || missingDictionarySources.value.length || missingHealthChecks.value.length) {
      return '检测到目录覆盖或健康检查缺项；当前只读切片仅输出差异说明，不触发真实 catalog write/export/remediation。'
    }
    return '未发现新的 blocked 差异，但 catalog write/export/remediation/outbox/worker/production write 仍保持 readonly guard。'
  })

  return {
    driftRows,
    driftStatusSummary,
    overallStatus,
    effectiveFocus,
    effectiveParity,
    effectiveRoute,
    effectiveTab,
    blockedReason,
    legacyRouteAliases: systemCatalogLegacyRouteAliases,
    parityRoutes,
    readonlyRecommendations,
    readonlyGuardActions: systemCatalogReadonlyGuardActions,
    remainingGap: systemCatalogRemainingGap,
  }
}
