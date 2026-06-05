import { computed, type Ref } from 'vue'
import type {
  SystemConfigCatalogItem,
  SystemDictionaryCatalogItem,
  SystemHealthSummaryItem,
} from '@/api/system_management'
import {
  systemFoundationSubjectExpectedDictionarySources,
  systemFoundationSubjectExpectedHealthChecks,
  systemFoundationSubjectReadonlyGuardActions,
  systemFoundationSubjectRemainingGap,
  type SystemFoundationSubjectRow,
  type SystemFoundationSubjectRouteItem,
} from '../constants/systemFoundationSubjectFields'

interface UseSystemFoundationSubjectReadonlyOptions {
  configItems: Ref<SystemConfigCatalogItem[]>
  dictionaryItems: Ref<SystemDictionaryCatalogItem[]>
  healthItems: Ref<SystemHealthSummaryItem[]>
  routeParity: Ref<string>
  routeTab: Ref<string>
  canReadConfig: Ref<boolean>
  canReadDictionary: Ref<boolean>
  canReadHealthSummary: Ref<boolean>
}

const statusWeight: Record<SystemFoundationSubjectRow['status'], number> = {
  ok: 0,
  warn: 1,
  blocked: 2,
}

const getHigherStatus = (
  left: SystemFoundationSubjectRow['status'],
  right: SystemFoundationSubjectRow['status'],
): SystemFoundationSubjectRow['status'] => (statusWeight[left] >= statusWeight[right] ? left : right)

export const useSystemFoundationSubjectReadonly = ({
  configItems,
  dictionaryItems,
  healthItems,
  routeParity,
  routeTab,
  canReadConfig,
  canReadDictionary,
  canReadHealthSummary,
}: UseSystemFoundationSubjectReadonlyOptions) => {
  const activeParity = computed(() => (routeParity.value === 'foundation-owner' ? routeParity.value : 'default'))
  const activeTab = computed(() => (routeTab.value === 'foundation-subjects' ? routeTab.value : 'default'))

  const configSourcesPresent = computed(() => new Set(configItems.value.map((item) => item.source)))
  const dictionarySourcesPresent = computed(() => new Set(dictionaryItems.value.map((item) => item.source)))
  const dictionaryTypeCount = computed(() => new Set(dictionaryItems.value.map((item) => item.dict_type)).size)
  const configModuleCount = computed(() => new Set(configItems.value.map((item) => item.module)).size)
  const healthCheckMap = computed(() => new Map(healthItems.value.map((item) => [item.check_name, item])))

  const missingDictionarySources = computed(() =>
    systemFoundationSubjectExpectedDictionarySources.filter((source) => !dictionarySourcesPresent.value.has(source)),
  )
  const missingHealthChecks = computed(() =>
    systemFoundationSubjectExpectedHealthChecks.filter((checkName) => !healthCheckMap.value.has(checkName)),
  )
  const blockedHealthChecks = computed(() =>
    healthItems.value.filter((item) => item.status === 'blocked').map((item) => item.check_name),
  )
  const warnedHealthChecks = computed(() =>
    healthItems.value.filter((item) => item.status === 'warn').map((item) => item.check_name),
  )

  const ownerParitySummary = computed(() => {
    if (activeParity.value === 'foundation-owner') {
      return 'foundation-owner parity active'
    }
    if (activeTab.value === 'foundation-subjects') {
      return 'foundation-subjects readonly view'
    }
    return 'system-management baseline'
  })

  const sourceStatusSummary = computed(() => {
    if (!canReadConfig.value || !canReadDictionary.value) {
      return 'source visibility blocked'
    }
    const configSources = [...configSourcesPresent.value].sort().join(' / ') || '-'
    const dictionarySources = [...dictionarySourcesPresent.value].sort().join(' / ') || '-'
    return `config:${configSources}｜dictionary:${dictionarySources}`
  })

  const subjectRows = computed<SystemFoundationSubjectRow[]>(() => {
    const rows: SystemFoundationSubjectRow[] = []

    rows.push({
      key: 'foundation-owner-parity',
      label: 'owner / foundation parity',
      status:
        activeParity.value === 'foundation-owner' ||
        activeTab.value === 'foundation-subjects' ||
        (!routeParity.value && !routeTab.value)
          ? 'ok'
          : 'warn',
      summary:
        activeParity.value === 'foundation-owner'
          ? '当前处于 foundation-owner parity 上下文。'
          : activeTab.value === 'foundation-subjects'
            ? '当前处于 foundation-subjects 只读视图。'
            : '当前处于 /system/management 基线路由，只读展示 foundation subject 摘要。',
      recommendation: '仅允许 foundation owner parity 说明与只读核对，不开放真实主体目录维护。',
    })

    rows.push({
      key: 'subject-catalog-readiness',
      label: 'subject catalog readiness',
      status: !canReadDictionary.value
        ? 'blocked'
        : !dictionaryItems.value.length
          ? 'warn'
          : missingDictionarySources.value.length
            ? 'warn'
            : 'ok',
      summary: !canReadDictionary.value
        ? '缺少 system:dictionary_read 权限，无法核对主体目录 readiness。'
        : !dictionaryItems.value.length
          ? '当前无字典目录数据，无法确认 foundation subjects 覆盖。'
          : missingDictionarySources.value.length
            ? `缺少字典来源：${missingDictionarySources.value.join(' / ')}`
            : `字典类型数 ${dictionaryTypeCount.value}，已覆盖 ${systemFoundationSubjectExpectedDictionarySources.join(' / ')}。`,
      recommendation: '主体目录 readiness 仅作只读核对，不在本切片内触发字典维护或配置变更。',
    })

    rows.push({
      key: 'source-status',
      label: 'source status',
      status: !canReadConfig.value
        ? 'blocked'
        : !configItems.value.length
          ? 'warn'
          : configSourcesPresent.value.size
            ? 'ok'
            : 'warn',
      summary: !canReadConfig.value
        ? '缺少 system:config_read 权限，无法读取 source status。'
        : !configItems.value.length
          ? '当前无系统配置目录数据，无法确认主体目录 source status。'
          : `配置模块数 ${configModuleCount.value}，source：${[...configSourcesPresent.value].sort().join(' / ') || '-'}`,
      recommendation: 'source status 只读展示系统配置来源，不开放真实 config/report 写链路。',
    })

    rows.push({
      key: 'subject-drift-readiness',
      label: 'subject drift / readiness summary',
      status: !canReadHealthSummary.value
        ? 'blocked'
        : blockedHealthChecks.value.length || missingHealthChecks.value.length
          ? 'blocked'
          : warnedHealthChecks.value.length
            ? 'warn'
            : 'ok',
      summary: !canReadHealthSummary.value
        ? '缺少 system:diagnostic 权限，无法读取 readiness 健康检查。'
        : blockedHealthChecks.value.length
          ? `存在 blocked 检查：${blockedHealthChecks.value.join(' / ')}`
          : missingHealthChecks.value.length
            ? `缺少健康检查：${missingHealthChecks.value.join(' / ')}`
            : warnedHealthChecks.value.length
              ? `存在 warn 检查：${warnedHealthChecks.value.join(' / ')}`
              : 'readiness 健康检查与只读契约一致。',
      recommendation: 'drift/readiness 摘要只作只读提示，后台 remediation 与报告生成未开放。',
    })

    return rows
  })

  const readinessSummary = computed(() => {
    const counts = subjectRows.value.reduce<Record<SystemFoundationSubjectRow['status'], number>>(
      (acc, row) => {
        acc[row.status] += 1
        return acc
      },
      { ok: 0, warn: 0, blocked: 0 },
    )
    return `ok:${counts.ok} / warn:${counts.warn} / blocked:${counts.blocked}`
  })

  const blockedReason = computed(() => {
    const blocked = subjectRows.value.filter((row) => row.status === 'blocked').map((row) => row.summary)
    const warned = subjectRows.value.filter((row) => row.status === 'warn').map((row) => row.summary)
    if (blocked.length) {
      return blocked.join('；')
    }
    if (warned.length) {
      return warned.join('；')
    }
    return '未发现 blocked reason，当前仅保留 readonly guard。'
  })

  const overallStatus = computed<SystemFoundationSubjectRow['status']>(() =>
    subjectRows.value.reduce<SystemFoundationSubjectRow['status']>((status, row) => getHigherStatus(status, row.status), 'ok'),
  )

  const parityRoutes = computed<SystemFoundationSubjectRouteItem[]>(() => [
    {
      key: 'baseline-route',
      label: '系统管理基线路由',
      route: '/system/management',
      active: !routeParity.value && !routeTab.value,
      note: '默认只读目录与主体 readiness 入口。',
    },
    {
      key: 'foundation-subjects',
      label: 'foundation-subjects 只读视图',
      route: '/system/management?tab=foundation-subjects',
      active: activeTab.value === 'foundation-subjects',
      note: '聚焦 foundation subject readiness，不开放真实目录维护。',
    },
    {
      key: 'foundation-owner-parity',
      label: 'foundation-owner parity',
      route: '/system/management?parity=foundation-owner&tab=foundation-subjects',
      active: activeParity.value === 'foundation-owner',
      note: '聚焦 owner/foundation parity 与 source status。',
    },
  ])

  const readonlyRecommendations = computed(() => {
    const dynamic = subjectRows.value
      .filter((row) => row.status !== 'ok')
      .map((row) => `${row.label}：${row.recommendation}`)

    return dynamic.length
      ? dynamic
      : [
          'foundation subject parity/readiness 当前未发现 blocked 差异，后续仍需通过受控链路执行真实目录维护与配置变更。',
          'owner/foundation parity 仅用于说明来源与 readiness，不替代后台 remediation 或报表生成。',
        ]
  })

  return {
    blockedReason,
    overallStatus,
    ownerParitySummary,
    parityRoutes,
    readonlyGuardActions: systemFoundationSubjectReadonlyGuardActions,
    readonlyRecommendations,
    readinessSummary,
    remainingGap: systemFoundationSubjectRemainingGap,
    sourceStatusSummary,
    subjectRows,
  }
}
