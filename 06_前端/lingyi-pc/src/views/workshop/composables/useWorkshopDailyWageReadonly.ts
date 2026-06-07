import { computed, type ComputedRef, type Ref } from 'vue'
import type { WorkshopDailyWageRow } from '@/api/workshop'
import {
  WORKSHOP_DAILY_WAGE_GUARD_MESSAGE,
  WORKSHOP_DAILY_WAGE_GUARDED_ACTIONS,
  WORKSHOP_DAILY_WAGE_READONLY_GUARD,
  WORKSHOP_DAILY_WAGE_READONLY_METRICS,
  WORKSHOP_DAILY_WAGE_REMAINING_GAP,
  WORKSHOP_DAILY_WAGE_ROUTE_LABELS,
  type WorkshopDailyWageGuardedAction,
  type WorkshopDailyWageReadonlyTag,
} from '../constants/workshopDailyWageReadonlyFields'

export interface WorkshopDailyWageReadonlyQueryState {
  employee: string
  from_date: string
  to_date: string
  process_name: string
  item_code: string
  page: number
  page_size: number
}

export interface WorkshopDailyWageReadonlyMetric {
  key: string
  label: string
  value: string
}

export interface WorkshopDailyWageReadonlyIssue {
  key: string
  title: string
  message: string
  type: 'info' | 'warning' | 'error'
}

export interface WorkshopDailyWageReadonlySummary {
  tags: WorkshopDailyWageReadonlyTag[]
  metrics: WorkshopDailyWageReadonlyMetric[]
  issues: WorkshopDailyWageReadonlyIssue[]
  guardedActions: WorkshopDailyWageGuardedAction[]
  currentPathLabel: string
  parityLabel: string
  focusLabel: string
  sourceStatusLabel: string
  itemStatusSummary: string
  blockedReason: string
  readonlyGuard: string
  remainingGap: string
}

const toNumber = (value: string | number | null | undefined): number => {
  if (value === '' || value === null || value === undefined) return 0
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : 0
}

const toIntegerLabel = (value: number): string => `${Math.round(value)}`

const toMoneyLabel = (value: string | number): string => {
  const parsed = toNumber(value)
  return parsed.toFixed(2)
}

const resolveParityLabel = (parity: string): string => (
  parity === 'production-order' ? 'production-order parity' : 'production-order parity (default)'
)

const resolveFocusLabel = (focus: string): string => (
  focus === 'daily-wage-source' ? 'daily-wage-source focus' : 'daily-wage-source focus (default)'
)

export const useWorkshopDailyWageReadonly = (params: {
  rows: Ref<WorkshopDailyWageRow[]>
  totalAmount: Ref<string | number>
  query: WorkshopDailyWageReadonlyQueryState
  canRead: ComputedRef<boolean>
  currentPath: ComputedRef<string>
  parity: ComputedRef<string>
  focus: ComputedRef<string>
}): ComputedRef<WorkshopDailyWageReadonlySummary> =>
  computed<WorkshopDailyWageReadonlySummary>(() => {
    const rows = params.rows.value
    const currentPathLabel = params.currentPath.value || WORKSHOP_DAILY_WAGE_ROUTE_LABELS.defaultRoute
    const parityLabel = resolveParityLabel(params.parity.value)
    const focusLabel = resolveFocusLabel(params.focus.value)
    const employeeCount = new Set(rows.map((row) => row.employee).filter(Boolean)).size
    const reversalRows = rows.filter((row) => toNumber(row.reversal_qty) > 0)
    const missingItemRows = rows.filter((row) => !String(row.item_code || '').trim())
    const zeroWageRows = rows.filter((row) => toNumber(row.net_qty) > 0 && toNumber(row.wage_amount) <= 0)
    const invalidNetRows = rows.filter((row) => toNumber(row.net_qty) <= 0)
    const netQty = rows.reduce((sum, row) => sum + toNumber(row.net_qty), 0)
    const sourceReadyCount = rows.filter((row) => (
      Boolean(String(row.employee || '').trim()) &&
      Boolean(String(row.process_name || '').trim()) &&
      Boolean(String(row.work_date || '').trim())
    )).length
    const sourceStatusLabel = !params.canRead.value
      ? 'daily-wage-source guarded'
      : sourceReadyCount > 0
        ? 'daily-wage-source ready'
        : 'daily-wage-source pending'
    const itemStatusSummary = !params.canRead.value
      ? 'wage item/status 仅保留 guarded fallback。'
      : `rows=${rows.length} / reversal=${reversalRows.length} / source=${sourceReadyCount}`

    const tags: WorkshopDailyWageReadonlyTag[] = [
      {
        key: 'source',
        label: `${WORKSHOP_DAILY_WAGE_ROUTE_LABELS.sourceLabel}: ${focusLabel}`,
        type: 'info',
      },
      {
        key: 'mode',
        label: WORKSHOP_DAILY_WAGE_ROUTE_LABELS.readonlyMode,
        type: 'success',
      },
      {
        key: 'reversal',
        label: reversalRows.length > 0 ? `存在回流工票 ${reversalRows.length} 条` : '当前无回流工票',
        type: reversalRows.length > 0 ? 'warning' : 'success',
      },
      {
        key: 'missing',
        label: missingItemRows.length > 0 ? `缺失款式 ${missingItemRows.length} 条` : '来源信息完整',
        type: missingItemRows.length > 0 ? 'warning' : 'success',
      },
      {
        key: 'parity',
        label: parityLabel,
        type: 'warning',
      },
    ]

    const metrics = WORKSHOP_DAILY_WAGE_READONLY_METRICS.map((field) => {
      switch (field.key) {
        case 'employeeCount':
          return { key: field.key, label: field.label, value: toIntegerLabel(employeeCount) }
        case 'reversalCount':
          return { key: field.key, label: field.label, value: toIntegerLabel(reversalRows.length) }
        case 'netQty':
          return { key: field.key, label: field.label, value: toMoneyLabel(netQty) }
        case 'totalAmount':
          return { key: field.key, label: field.label, value: toMoneyLabel(params.totalAmount.value) }
        default:
          return { key: field.key, label: field.label, value: '-' }
      }
    })

    const issues: WorkshopDailyWageReadonlyIssue[] = []
    if (!params.query.from_date || !params.query.to_date) {
      issues.push({
        key: 'date-range',
        title: '统计区间未完整',
        message: '建议补齐起止日期后再核对异常摘要，当前仅展示只读回退统计。',
        type: 'warning',
      })
    }
    if (missingItemRows.length > 0) {
      issues.push({
        key: 'missing-item',
        title: '存在缺失款式信息',
        message: `共有 ${missingItemRows.length} 条日工资记录缺少款式编码，需回到日工资来源核对映射。`,
        type: 'warning',
      })
    }
    if (zeroWageRows.length > 0) {
      issues.push({
        key: 'zero-wage',
        title: '存在工资金额缺失',
        message: `共有 ${zeroWageRows.length} 条净数量大于 0 的记录工资金额为 0，当前仅允许只读诊断。`,
        type: 'warning',
      })
    }
    if (invalidNetRows.length > 0) {
      issues.push({
        key: 'invalid-net',
        title: '存在净数量异常',
        message: `共有 ${invalidNetRows.length} 条记录净数量小于等于 0，请回到工票来源核对登记/撤销差异。`,
        type: 'error',
      })
    }
    if (params.canRead.value && rows.length === 0) {
      issues.push({
        key: 'empty-readback',
        title: '当前筛选暂无回读记录',
        message: '日工资来源和异常摘要保持只读占位，不触发真实确认、导入或同步动作。',
        type: 'info',
      })
    }

    return {
      tags,
      metrics,
      issues,
      guardedActions: WORKSHOP_DAILY_WAGE_GUARDED_ACTIONS,
      currentPathLabel,
      parityLabel,
      focusLabel,
      sourceStatusLabel,
      itemStatusSummary,
      blockedReason: WORKSHOP_DAILY_WAGE_GUARD_MESSAGE,
      readonlyGuard: WORKSHOP_DAILY_WAGE_READONLY_GUARD,
      remainingGap: WORKSHOP_DAILY_WAGE_REMAINING_GAP,
    }
  })
