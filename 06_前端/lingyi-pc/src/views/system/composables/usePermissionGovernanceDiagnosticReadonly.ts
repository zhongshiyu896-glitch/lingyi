import { computed, type ComputedRef, type Ref } from 'vue'
import type { PermissionGovernanceDiagnosticData, PermissionMenuManagementData } from '@/api/permission_governance'
import {
  permissionGovernanceDiagnosticCheckMetaMap,
  permissionGovernanceExpectedMenus,
  permissionGovernanceRemainingGap,
} from '@/views/system/constants/permissionGovernanceDiagnosticFields'

type HealthStatus = 'ok' | 'warn' | 'blocked'

export interface PermissionGovernanceDiagnosticCheckRow {
  name: string
  label: string
  group: string
  status: string
  message: string
  severity: 'success' | 'warning' | 'danger'
}

export interface PermissionGovernanceHealthSummaryRow {
  checkName: string
  label: string
  status: HealthStatus
  checkResult: string
  source: string
}

export interface PermissionGovernanceMenuStatusDriftRow {
  menuKey: string
  menuName: string
  expectedRoute: string
  actualRoute: string
  status: HealthStatus
  message: string
}

interface UsePermissionGovernanceDiagnosticReadonlyOptions {
  diagnosticData: Ref<PermissionGovernanceDiagnosticData>
  menuManagement: Ref<PermissionMenuManagementData>
  canRead: ComputedRef<boolean>
  canAuditRead: ComputedRef<boolean>
  canDiagnostic: ComputedRef<boolean>
  canExport: ComputedRef<boolean>
}

const toSeverity = (status: string): 'success' | 'warning' | 'danger' => {
  if (status === 'pass' || status === 'ok') return 'success'
  if (status === 'warn') return 'warning'
  return 'danger'
}

const toHealthStatus = (statuses: HealthStatus[]): HealthStatus => {
  if (statuses.includes('blocked')) return 'blocked'
  if (statuses.includes('warn')) return 'warn'
  return 'ok'
}

export const usePermissionGovernanceDiagnosticReadonly = ({
  diagnosticData,
  menuManagement,
  canRead,
  canAuditRead,
  canDiagnostic,
  canExport,
}: UsePermissionGovernanceDiagnosticReadonlyOptions) => {
  const diagnosticCheckRows = computed<PermissionGovernanceDiagnosticCheckRow[]>(() =>
    diagnosticData.value.checks.map((check) => {
      const meta = permissionGovernanceDiagnosticCheckMetaMap[check.name]
      return {
        name: check.name,
        label: meta?.label || check.name,
        group: meta?.group || '治理诊断',
        status: check.status,
        message: check.message || meta?.passHint || 'pass',
        severity: toSeverity(check.status),
      }
    }),
  )

  const menuStatusDriftRows = computed<PermissionGovernanceMenuStatusDriftRow[]>(() =>
    permissionGovernanceExpectedMenus.map((expected) => {
      const item = menuManagement.value.items.find((entry) => entry.menu_key === expected.menuKey)
      if (!item) {
        return {
          menuKey: expected.menuKey,
          menuName: expected.menuName,
          expectedRoute: expected.expectedRoute,
          actualRoute: '-',
          status: 'blocked',
          message: '缺少只读菜单节点，无法确认菜单状态与 guard contract。',
        }
      }

      const issues: { level: HealthStatus; message: string }[] = []
      if (item.route !== expected.expectedRoute) {
        issues.push({ level: 'warn', message: `route drift: ${item.route}` })
      }
      if (item.status !== expected.expectedStatus) {
        issues.push({ level: 'warn', message: `状态应为 ${expected.expectedStatus}，当前为 ${item.status}` })
      }
      if (item.permission_action !== expected.expectedPermissionAction) {
        issues.push({
          level: 'blocked',
          message: `权限动作应为 ${expected.expectedPermissionAction}，当前为 ${item.permission_action}`,
        })
      }

      expected.requiredGuardedActionKeys.forEach((actionKey) => {
        const action = item.actions.find((entry) => entry.action_key === actionKey)
        if (!action) {
          issues.push({ level: 'blocked', message: `缺少 guarded 动作 ${actionKey}` })
          return
        }
        if (!action.guarded) {
          issues.push({ level: 'blocked', message: `${actionKey} 未保持 guarded_readonly` })
        }
      })

      return {
        menuKey: expected.menuKey,
        menuName: expected.menuName,
        expectedRoute: expected.expectedRoute,
        actualRoute: item.route,
        status: issues.length ? toHealthStatus(issues.map((issue) => issue.level)) : 'ok',
        message: issues.map((issue) => issue.message).join('；') || '菜单状态与只读 contract 一致。',
      }
    }),
  )

  const blockedCheckCount = computed<number>(
    () => diagnosticCheckRows.value.filter((row) => row.status !== 'pass').length,
  )

  const menuDriftCount = computed<number>(
    () => menuStatusDriftRows.value.filter((row) => row.status !== 'ok').length,
  )

  const readonlyGuardStatus = computed<HealthStatus>(() => {
    if (!canRead.value || !canAuditRead.value) return 'warn'
    if (!canExport.value) return 'warn'
    return menuDriftCount.value > 0 ? toHealthStatus(menuStatusDriftRows.value.map((row) => row.status)) : 'ok'
  })

  const healthSummaryRows = computed<PermissionGovernanceHealthSummaryRow[]>(() => {
    const diagnosticStatus: HealthStatus =
      blockedCheckCount.value === 0 && diagnosticData.value.status === 'ok'
        ? 'ok'
        : blockedCheckCount.value > 0
          ? 'warn'
          : 'warn'
    const menuStatus = menuDriftCount.value > 0 ? toHealthStatus(menuStatusDriftRows.value.map((row) => row.status)) : 'ok'
    return [
      {
        checkName: 'system_health_summary_fallback',
        label: 'system health summary fallback',
        status: canDiagnostic.value ? 'ok' : 'warn',
        checkResult: canDiagnostic.value ? 'diagnostic_api_active' : 'local_fallback_active',
        source: 'permission-governance-local',
      },
      {
        checkName: 'diagnostic_checks',
        label: 'diagnostic checks',
        status: diagnosticStatus,
        checkResult: blockedCheckCount.value ? `${blockedCheckCount.value} checks need attention` : 'all_pass',
        source: 'permission-diagnostic',
      },
      {
        checkName: 'menu_status_drift',
        label: 'menu status drift',
        status: menuStatus,
        checkResult: menuDriftCount.value ? `${menuDriftCount.value} drift rows` : 'menu_contract_aligned',
        source: 'menu-management-readonly',
      },
      {
        checkName: 'readonly_guard_boundary',
        label: 'readonly guard boundary',
        status: readonlyGuardStatus.value,
        checkResult: readonlyGuardStatus.value === 'ok' ? 'guarded_readonly_active' : 'guard_review_required',
        source: 'permission-governance-guard',
      },
    ]
  })

  const healthStatus = computed<HealthStatus>(() => toHealthStatus(healthSummaryRows.value.map((row) => row.status)))

  const blockingHints = computed<string[]>(() => {
    const checkHints = diagnosticCheckRows.value
      .filter((row) => row.status !== 'pass')
      .map((row) => `${row.label}: ${row.message}`)
    const menuHints = menuStatusDriftRows.value
      .filter((row) => row.status !== 'ok')
      .map((row) => `${row.menuName}: ${row.message}`)
    return [...menuHints, ...checkHints].slice(0, 4)
  })

  return {
    diagnosticCheckRows,
    menuStatusDriftRows,
    blockedCheckCount,
    menuDriftCount,
    healthSummaryRows,
    healthStatus,
    blockingHints,
    remainingGap: permissionGovernanceRemainingGap,
    fallbackSource: 'permission-governance-local',
  }
}
