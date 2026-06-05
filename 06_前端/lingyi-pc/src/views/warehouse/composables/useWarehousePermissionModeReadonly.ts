import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  WarehouseManagementItem,
  WarehouseMaterialInventoryItem,
  WarehouseStockSummaryItem,
} from '@/api/warehouse'
import {
  WAREHOUSE_PERMISSION_MODE_ACTIONS,
  WAREHOUSE_PERMISSION_MODE_CARD_FIELDS,
  WAREHOUSE_PERMISSION_MODE_GUARD_MESSAGE,
  WAREHOUSE_PERMISSION_MODE_METRIC_FIELDS,
  WAREHOUSE_PERMISSION_MODE_REMAINING_GAP,
  WAREHOUSE_PERMISSION_MODE_ROUTE_LABELS,
  WAREHOUSE_PERMISSION_MODE_WRITE_BOUNDARY,
  type WarehousePermissionModeGuardedAction,
  type WarehousePermissionModeTagType,
} from '@/views/warehouse/constants/warehousePermissionModeFields'

type GuardTone = WarehousePermissionModeTagType

export interface WarehousePermissionModeReadonlyMetric {
  key: string
  label: string
  value: string
}

export interface WarehousePermissionModeReadonlyCard {
  key: string
  title: string
  count: number
  statusLabel: string
  statusTone: GuardTone
  sourceRoute: string
  sourceModule: string
  sourceDescription: string
  blockedReason: string
  note: string
}

export interface WarehousePermissionModeReadonlySummary {
  tags: Array<{
    key: string
    label: string
    type: GuardTone
  }>
  metrics: WarehousePermissionModeReadonlyMetric[]
  cards: WarehousePermissionModeReadonlyCard[]
  guardedActions: Array<WarehousePermissionModeGuardedAction & { disabled: true }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  permissionModeStatusLabel: string
  permissionModeStatusTone: GuardTone
  permissionModeSummary: string
  readonlyBaselineLabel: string
  readonlyBaselineSummary: string
  parityLabel: string
  parityTone: GuardTone
  blockedReason: string
  blockedReasonDetail: string
  guardMessage: string
  remainingGap: string
  writeBoundary: string
}

interface UseWarehousePermissionModeReadonlyOptions {
  summaryRows: MaybeRef<WarehouseStockSummaryItem[]>
  managementRows: MaybeRef<WarehouseManagementItem[]>
  materialRows: MaybeRef<WarehouseMaterialInventoryItem[]>
  canRead: MaybeRef<boolean>
  parity: MaybeRef<string>
  currentPath: MaybeRef<string>
}

const normalizeRouteLabel = (currentPath: string, parity: string): string => {
  if (currentPath.includes('tab=readonly-baseline')) return WAREHOUSE_PERMISSION_MODE_ROUTE_LABELS.readonlyBaseline
  if (parity === 'foundation-material') return WAREHOUSE_PERMISSION_MODE_ROUTE_LABELS.foundationMaterial
  return WAREHOUSE_PERMISSION_MODE_ROUTE_LABELS.permissionMode
}

const resolveParityLabel = (parity: string): string => {
  if (parity === 'foundation-material') return 'foundation-material parity'
  if (parity === 'foundation-warehouse') return 'foundation-warehouse parity'
  if (parity === 'product-stock') return 'product-stock parity'
  return 'warehouse permission readonly'
}

const resolveParityTone = (parity: string): GuardTone => {
  if (parity === 'foundation-material') return 'warning'
  if (parity === 'foundation-warehouse') return 'info'
  if (parity === 'product-stock') return 'info'
  return 'success'
}

const toNumber = (value: string | number | null | undefined): number => {
  const numeric = Number(value ?? 0)
  return Number.isFinite(numeric) ? numeric : 0
}

const toSampleNote = (values: string[], emptyNote: string): string => {
  if (values.length === 0) return emptyNote
  return `sample=${values.slice(0, 3).join(' ; ')}`
}

export const useWarehousePermissionModeReadonly = ({
  summaryRows,
  managementRows,
  materialRows,
  canRead,
  parity,
  currentPath,
}: UseWarehousePermissionModeReadonlyOptions): {
  warehousePermissionModeReadonlySummary: ComputedRef<WarehousePermissionModeReadonlySummary>
} => {
  const warehousePermissionModeReadonlySummary = computed<WarehousePermissionModeReadonlySummary>(() => {
    const readable = Boolean(unref(canRead))
    const normalizedParity = String(unref(parity) || '').trim().toLowerCase()
    const normalizedCurrentPath = String(unref(currentPath) || '').trim()
    const currentSummaryRows = unref(summaryRows)
    const currentManagementRows = unref(managementRows)
    const currentMaterialRows = unref(materialRows)

    const warningManagementRows = currentManagementRows.filter((row) => (
      row.status !== 'normal' || toNumber(row.utilization_rate) >= 80
    ))
    const warningMaterialRows = currentMaterialRows.filter((row) => row.status !== 'normal')
    const warningCount = warningManagementRows.length + warningMaterialRows.length
    const readonlyBaselineCount = currentSummaryRows.length + currentManagementRows.length + currentMaterialRows.length
    const routeLabel = normalizeRouteLabel(normalizedCurrentPath, normalizedParity)

    const permissionModeStatusLabel = !readable
      ? '仓库权限模式只读守卫'
      : readonlyBaselineCount === 0
        ? '仓库权限模式待真实核对'
        : warningCount > 0
          ? '仓库权限模式存在预警'
          : '仓库权限模式已回读'
    const permissionModeStatusTone: GuardTone = !readable
      ? 'danger'
      : readonlyBaselineCount === 0
        ? 'info'
        : warningCount > 0
          ? 'warning'
          : 'success'

    const permissionModeSummary = !readable
      ? '当前账号仅允许仓库 permission mode 的 guarded readonly 回退。'
      : `${routeLabel} 已回读仓库目录 ${currentManagementRows.length} 条、物料基线 ${currentMaterialRows.length} 条、库存摘要 ${currentSummaryRows.length} 条。`

    const readonlyBaselineSummary = !readable
      ? 'readonly baseline 保持守卫态，仅保留 blocked reason 和 parity 提示。'
      : readonlyBaselineCount === 0
        ? 'readonly baseline 尚未命中真实回读结果，当前使用只读回退占位。'
        : `readonly baseline 已覆盖 ${readonlyBaselineCount} 条目录/物料/库存只读记录。`

    const blockedReason = !readable
      ? 'blocked_reason=当前账号缺少 warehouse:read，仅允许 parity 只读回退。'
      : 'blocked_reason=真实入库、出库、调拨、盘点、导出、ERPNext 动作全部保持关闭。'
    const blockedReasonDetail = normalizedParity === 'foundation-material'
      ? 'foundation-material parity 仅用于基础资料与仓库权限模式核对，不开放任何库存写入。'
      : '当前切片仅核对仓库权限模式、readonly baseline 与 blocked reason，不进入真实库存执行链。'

    const tags = [
      {
        key: 'source',
        label: `${WAREHOUSE_PERMISSION_MODE_ROUTE_LABELS.sourceLabel}: ${routeLabel}`,
        type: 'info' as GuardTone,
      },
      {
        key: 'mode',
        label: WAREHOUSE_PERMISSION_MODE_ROUTE_LABELS.readonlyMode,
        type: 'success' as GuardTone,
      },
      {
        key: 'parity',
        label: resolveParityLabel(normalizedParity),
        type: resolveParityTone(normalizedParity),
      },
      {
        key: 'status',
        label: permissionModeStatusLabel,
        type: permissionModeStatusTone,
      },
    ]

    const metrics = WAREHOUSE_PERMISSION_MODE_METRIC_FIELDS.map((field) => {
      switch (field.key) {
        case 'warehouseCount':
          return { key: field.key, label: field.label, value: String(currentManagementRows.length) }
        case 'materialCount':
          return { key: field.key, label: field.label, value: String(currentMaterialRows.length) }
        case 'blockedActionCount':
          return { key: field.key, label: field.label, value: String(WAREHOUSE_PERMISSION_MODE_ACTIONS.length) }
        case 'warningCount':
          return { key: field.key, label: field.label, value: String(warningCount) }
        default:
          return { key: field.key, label: field.label, value: '0' }
      }
    })

    const cards = WAREHOUSE_PERMISSION_MODE_CARD_FIELDS.map((field) => {
      if (field.key === 'permission_mode') {
        const sample = currentManagementRows.map((row) => `${row.warehouse_name} / ${row.status}`)
        return {
          key: field.key,
          title: field.title,
          count: currentManagementRows.length,
          statusLabel: warningManagementRows.length > 0 ? '权限模式存在预警' : '权限模式只读可见',
          statusTone: warningManagementRows.length > 0 ? ('warning' as GuardTone) : ('success' as GuardTone),
          sourceRoute: field.sourceRoute,
          sourceModule: field.sourceModule,
          sourceDescription: field.sourceDescription,
          blockedReason: field.blockedReason,
          note: toSampleNote(sample, '当前查询范围未出现仓库目录异常。'),
        }
      }

      if (field.key === 'readonly_baseline') {
        const sample = currentMaterialRows.map((row) => `${row.material_code} / ${row.status}`)
        return {
          key: field.key,
          title: field.title,
          count: readonlyBaselineCount,
          statusLabel: readonlyBaselineCount > 0 ? 'baseline 已回读' : 'baseline 待真实核对',
          statusTone: readonlyBaselineCount > 0 ? ('success' as GuardTone) : ('info' as GuardTone),
          sourceRoute: field.sourceRoute,
          sourceModule: field.sourceModule,
          sourceDescription: field.sourceDescription,
          blockedReason: field.blockedReason,
          note: toSampleNote(sample, '当前查询范围未回读到物料基线记录。'),
        }
      }

      return {
        key: field.key,
        title: field.title,
        count: WAREHOUSE_PERMISSION_MODE_ACTIONS.length,
        statusLabel: '写动作全部禁用',
        statusTone: 'warning' as GuardTone,
        sourceRoute: field.sourceRoute,
        sourceModule: field.sourceModule,
        sourceDescription: field.sourceDescription,
        blockedReason: field.blockedReason,
        note: blockedReasonDetail,
      }
    })

    return {
      tags,
      metrics,
      cards,
      guardedActions: WAREHOUSE_PERMISSION_MODE_ACTIONS.map((action) => ({
        ...action,
        disabled: true as const,
      })),
      readonlySourceLabel: routeLabel,
      readonlyModeLabel: WAREHOUSE_PERMISSION_MODE_ROUTE_LABELS.readonlyMode,
      permissionModeStatusLabel,
      permissionModeStatusTone,
      permissionModeSummary,
      readonlyBaselineLabel: readonlyBaselineCount > 0 ? 'readonly baseline 已回读' : 'readonly baseline 待真实核对',
      readonlyBaselineSummary,
      parityLabel: resolveParityLabel(normalizedParity),
      parityTone: resolveParityTone(normalizedParity),
      blockedReason,
      blockedReasonDetail,
      guardMessage: WAREHOUSE_PERMISSION_MODE_GUARD_MESSAGE,
      remainingGap: WAREHOUSE_PERMISSION_MODE_REMAINING_GAP,
      writeBoundary: WAREHOUSE_PERMISSION_MODE_WRITE_BOUNDARY,
    }
  })

  return {
    warehousePermissionModeReadonlySummary,
  }
}
