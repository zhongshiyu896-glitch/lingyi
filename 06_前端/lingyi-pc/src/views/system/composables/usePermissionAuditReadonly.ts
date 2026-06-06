import { computed, type ComputedRef, type Ref } from 'vue'
import type {
  PermissionMenuManagementData,
  PermissionOperationAuditData,
  PermissionSecurityAuditData,
} from '@/api/permission_governance'
import type {
  PermissionGovernanceDiagnosticCheckRow,
  PermissionGovernanceHealthSummaryRow,
} from '@/views/system/composables/usePermissionGovernanceDiagnosticReadonly'
import {
  permissionAuditReadonlyDisabledActions,
  permissionAuditReadonlyFallbackBlockedReasons,
  type PermissionAuditReadonlyEntry,
  type PermissionAuditReadonlyLineItem,
  type PermissionAuditReadonlySummaryCard,
  type PermissionAuditReadonlyTone,
} from '@/views/system/constants/permissionAuditFields'

interface UsePermissionAuditReadonlyOptions {
  currentRouteLabel: ComputedRef<string>
  routeTab: ComputedRef<string>
  routeParity: ComputedRef<string>
  canRead: ComputedRef<boolean>
  canAuditRead: ComputedRef<boolean>
  canDiagnostic: ComputedRef<boolean>
  canExport: ComputedRef<boolean>
  healthSummaryRows: ComputedRef<PermissionGovernanceHealthSummaryRow[]>
  diagnosticCheckRows: ComputedRef<PermissionGovernanceDiagnosticCheckRow[]>
  blockingHints: ComputedRef<string[]>
  remainingGap: string
  fallbackSource: string
  menuManagement: Ref<PermissionMenuManagementData>
  securityAudit: Ref<PermissionSecurityAuditData>
  operationAudit: Ref<PermissionOperationAuditData>
}

const toTone = (status: string): PermissionAuditReadonlyTone => {
  if (status === 'ok' || status === 'pass' || status === 'success') return 'success'
  if (status === 'warn') return 'warning'
  if (status === 'blocked' || status === 'failed') return 'danger'
  return 'info'
}

export const usePermissionAuditReadonly = ({
  currentRouteLabel,
  routeTab,
  routeParity,
  canRead,
  canAuditRead,
  canDiagnostic,
  canExport,
  healthSummaryRows,
  diagnosticCheckRows,
  blockingHints,
  remainingGap,
  fallbackSource,
  menuManagement,
  securityAudit,
  operationAudit,
}: UsePermissionAuditReadonlyOptions) => {
  const isAuditReadinessTab = computed<boolean>(() => routeTab.value === 'audit-readiness')
  const parityMode = computed<string>(() => (routeParity.value === 'permission-audit' ? 'foundation-owner linked' : 'permission-local'))
  const ownerRoles = computed<string[]>(() =>
    Array.from(new Set(menuManagement.value.items.map((item) => item.owner_role).filter(Boolean))),
  )
  const guardedActionCount = computed<number>(() =>
    menuManagement.value.items.reduce((count, item) => count + item.actions.filter((action) => action.guarded).length, 0),
  )
  const auditReadinessStatus = computed<string>(() => (canAuditRead.value ? 'GET_ONLY_READY' : 'LOCAL_FALLBACK'))
  const sourceStatus = computed<string>(() => (canDiagnostic.value ? 'diagnostic-api' : fallbackSource))
  const blockedReasons = computed<string[]>(() =>
    blockingHints.value.length ? blockingHints.value : permissionAuditReadonlyFallbackBlockedReasons,
  )
  const readonlyGuardText = computed<string>(() => {
    const reasons: string[] = []
    if (!canRead.value) {
      reasons.push('permission:read 缺失，目录与菜单状态使用本地只读 fallback')
    }
    if (!canAuditRead.value) {
      reasons.push('permission:audit_read 缺失，审计准备度仅展示 fallback 只读摘要')
    }
    reasons.push(canExport.value ? 'permission:export 仅保留 guarded UI，不触发下载' : 'permission:export 缺失，导出入口保持禁用')
    reasons.push('后台修复、报表生成、ERPNext/outbox/worker 与 production write path 继续关闭')
    return reasons.join('；')
  })

  const summaryCards = computed<PermissionAuditReadonlySummaryCard[]>(() => [
    {
      key: 'audit-readiness',
      label: 'audit readiness',
      value: auditReadinessStatus.value,
      hint: `security=${securityAudit.value.total} / operation=${operationAudit.value.total}`,
      tone: canAuditRead.value ? 'success' : 'warning',
    },
    {
      key: 'owner-source-parity',
      label: 'owner/source parity',
      value: parityMode.value,
      hint: ownerRoles.value.join(' / ') || 'permission_admin / auditor',
      tone: routeParity.value === 'permission-audit' ? 'success' : 'info',
    },
    {
      key: 'source-status',
      label: 'source status',
      value: sourceStatus.value,
      hint: `health=${healthSummaryRows.value.length} / checks=${diagnosticCheckRows.value.length}`,
      tone: canDiagnostic.value ? 'success' : 'warning',
    },
    {
      key: 'guarded-actions',
      label: 'guarded actions',
      value: String(guardedActionCount.value),
      hint: 'export / remediation / report generation remain disabled',
      tone: guardedActionCount.value > 0 ? 'warning' : 'info',
    },
  ])

  const parityLines = computed<PermissionAuditReadonlyLineItem[]>(() => [
    {
      key: 'query-state',
      label: 'query state',
      value: isAuditReadinessTab.value ? 'audit-readiness active' : 'governance baseline',
      tone: isAuditReadinessTab.value ? 'success' : 'info',
    },
    {
      key: 'route-label',
      label: 'route',
      value: currentRouteLabel.value,
      tone: 'info',
    },
    {
      key: 'owner-roles',
      label: 'owner roles',
      value: ownerRoles.value.join(' / ') || 'permission_admin / auditor',
      tone: 'info',
    },
    {
      key: 'source-parity',
      label: 'source parity',
      value: `${parityMode.value} / ${sourceStatus.value}`,
      tone: routeParity.value === 'permission-audit' ? 'success' : 'warning',
    },
  ])

  const auditItems = computed<PermissionAuditReadonlyEntry[]>(() => {
    const securityFirst = securityAudit.value.items[0]
    const operationFirst = operationAudit.value.items[0]
    const healthBlocked = healthSummaryRows.value.filter((row) => row.status !== 'ok')
    const diagnosticBlocked = diagnosticCheckRows.value.filter((row) => row.status !== 'pass')

    return [
      {
        key: 'security-audit',
        title: '安全审计回读',
        owner: 'auditor',
        source: 'permission:audit_read',
        status: canAuditRead.value ? 'ready' : 'fallback',
        tone: canAuditRead.value ? 'success' : 'warning',
        summary: `当前筛选命中 ${securityAudit.value.total} 条安全审计记录`,
        details: [
          `首条 request_id=${securityFirst?.request_id || '-'}`,
          `首条 event_type=${securityFirst?.event_type || '-'}`,
          `只读原因=${securityFirst?.deny_reason || '保持 GET-only 查询'}`,
        ],
      },
      {
        key: 'operation-audit',
        title: '操作审计回读',
        owner: 'permission_admin',
        source: 'permission:audit_read',
        status: canAuditRead.value ? 'ready' : 'fallback',
        tone: canAuditRead.value ? 'success' : 'warning',
        summary: `当前筛选命中 ${operationAudit.value.total} 条操作审计记录`,
        details: [
          `首条 request_id=${operationFirst?.request_id || '-'}`,
          `首条 result=${operationFirst?.result || '-'}`,
          `变更键=${operationFirst ? `${operationFirst.before_keys.join(',') || '-'} -> ${operationFirst.after_keys.join(',') || '-'}` : '-'}`,
        ],
      },
      {
        key: 'diagnostic-checks',
        title: '诊断与准备度',
        owner: 'permission-governance-local',
        source: sourceStatus.value,
        status: diagnosticBlocked.length ? 'attention' : 'aligned',
        tone: diagnosticBlocked.length ? 'warning' : 'success',
        summary: `${diagnosticBlocked.length || 0} 个 checks 需要注意，${healthBlocked.length || 0} 个 health rows 非 ok`,
        details: (diagnosticBlocked.length
          ? diagnosticBlocked.slice(0, 3).map((item) => `${item.label}: ${item.message}`)
          : ['diagnostic checks 与 health summary 当前无新增漂移']).concat(
          healthBlocked.slice(0, 2).map((item) => `${item.label}: ${item.checkResult}`),
        ),
      },
      {
        key: 'guarded-actions',
        title: 'guarded / disabled actions',
        owner: 'readonly_guard',
        source: 'permission-governance-guard',
        status: guardedActionCount.value > 0 ? 'guarded' : 'baseline',
        tone: guardedActionCount.value > 0 ? 'warning' : 'info',
        summary: `${guardedActionCount.value} 个 guarded actions 继续保持非执行态`,
        details: menuManagement.value.items
          .flatMap((item) =>
            item.actions
              .filter((action) => action.guarded)
              .map((action) => `${item.menu_name} / ${action.action_label}: ${action.guard_reason || '只读 guard'}`),
          )
          .slice(0, 4),
      },
    ]
  })

  return {
    isAuditReadinessTab,
    summaryCards,
    parityLines,
    auditItems,
    blockedReasons,
    readonlyGuardText,
    disabledActions: permissionAuditReadonlyDisabledActions,
    remainingGap,
  }
}
