import { computed, unref, type ComputedRef, type MaybeRef } from 'vue'
import type {
  SalesInventoryAggregationItem,
  StockLedgerItem,
  StockSummaryItem,
} from '@/api/sales_inventory'
import type {
  SalesInventoryReferenceRow,
  SalesInventoryReferenceTab,
} from '@/api/sales_inventory_references'
import {
  SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_DISABLED_ACTIONS,
  SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_FOCUS_LABEL,
  SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_PARITY_LABEL,
  SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_READONLY_GUARD_REASON,
  SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_REMAINING_GAP,
  SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_STATE_LABELS,
  SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_STATE_TAGS,
  SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_SUMMARY_FIELDS,
  SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_WRITE_BOUNDARY,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_DISABLED_ACTIONS,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_FOCUS_LABEL,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_PARITY_LABEL,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_READONLY_GUARD_REASON,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_REMAINING_GAP,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_LABELS,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_TAGS,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_SUMMARY_FIELDS,
  SALES_INVENTORY_STOCK_SOURCE_GUARD_WRITE_BOUNDARY,
  type SalesInventoryStockSourceGuardState,
  type SalesInventoryStockSourceGuardTagType,
} from '@/views/sales_inventory/constants/salesInventoryStockSourceGuardFields'

const FALLBACK_TEXT = '-'

export interface SalesInventoryStockSourceGuardReadonlyCard {
  key: string
  label: string
  value: string
}

export interface SalesInventoryStockSourceGuardReadonlyAction {
  label: string
  reason: string
}

export interface SalesInventoryStockSourceGuardReadonlyItem {
  subjectLabel: string
  statusLabel: string
  sourceLabel: string
  blockedReason: string
}

export interface SalesInventoryStockSourceGuardReadonlyViewSummary {
  titleLabel: string
  testIdPrefix: string
  emptyText: string
  queryStateLabel: string
  parityLabel: string
  parityTone: SalesInventoryStockSourceGuardTagType
  focusLabel: string
  focusTone: SalesInventoryStockSourceGuardTagType
  stateLabel: string
  stateTone: SalesInventoryStockSourceGuardTagType
  sourceStatusLabel: string
  sourceStatusTone: SalesInventoryStockSourceGuardTagType
  itemStatusLabel: string
  blockedReason: string
  readonlyGuardReason: string
  remainingGap: string
  writeBoundary: string
  cards: SalesInventoryStockSourceGuardReadonlyCard[]
  disabledActions: SalesInventoryStockSourceGuardReadonlyAction[]
  items: SalesInventoryStockSourceGuardReadonlyItem[]
}

interface ReferenceModeOptions {
  rows: MaybeRef<SalesInventoryReferenceRow[]>
  activeTab: MaybeRef<SalesInventoryReferenceTab>
  currentPath: MaybeRef<string>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  filterStateLabel: MaybeRef<string>
  usingFallback: MaybeRef<boolean>
  canRead: MaybeRef<boolean>
}

interface StockLedgerModeOptions {
  rows: MaybeRef<StockLedgerItem[]>
  summaryRows: MaybeRef<StockSummaryItem[]>
  aggregationRows: MaybeRef<SalesInventoryAggregationItem[]>
  tab?: MaybeRef<string | null | undefined>
  parity?: MaybeRef<string | null | undefined>
  focus?: MaybeRef<string | null | undefined>
  itemCode?: MaybeRef<string | null | undefined>
  canRead: MaybeRef<boolean>
  requiredItemCode: MaybeRef<boolean>
  lastError?: MaybeRef<string | null | undefined>
  droppedCount?: MaybeRef<number | null | undefined>
}

type UseSalesInventoryStockSourceGuardReadonlyOptions =
  | ReferenceModeOptions
  | StockLedgerModeOptions

const normalizeText = (value: unknown): string => {
  const raw = Array.isArray(value) ? value[0] : value
  return typeof raw === 'string' ? raw.trim() : ''
}

const toNumber = (value: unknown): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const formatAmount = (value: unknown): string => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : FALLBACK_TEXT
}

const stockLedgerStatusLabel = (row: StockLedgerItem): '缺货' | '低库存' | '正常' => {
  const balanceQty = toNumber(row.qty_after_transaction)
  if (balanceQty <= 0) return '缺货'
  if (balanceQty < 20) return '低库存'
  return '正常'
}

const buildStockLedgerFallbackReason = (
  canRead: boolean,
  requiredItemCode: boolean,
  errorMessage: string,
): string => {
  if (errorMessage) return errorMessage
  if (!canRead) return '当前账号无库存台账读取权限，source guard 仅保留只读壳层。'
  if (requiredItemCode) return '缺少款号，当前只保留 stock-source guard/query state 用于只读验证。'
  return '真实库存来源链路冻结，仅开放 stock-source/source status 只读核对。'
}

const buildBlockedReason = (
  canRead: boolean,
  hasRows: boolean,
  usingFallbackValue: boolean,
  missingCount: number,
  activeTabValue: SalesInventoryReferenceTab,
): string => {
  if (!canRead) return '当前账号无引用档案读取权限，stock-source guard 仅保留只读壳层。'
  if (!hasRows) return '当前筛选未命中 stock-source 条目，仍保留 foundation-reference parity 与 stock-source focus 只读壳层。'
  if (missingCount > 0) {
    return activeTabValue === 'suppliers'
      ? '供应商 stock-source 当前缺少直连来源，只保留 foundation-reference parity 与本地只读守卫。'
      : '当前 stock-source 存在缺失，仅保留 source guard readonly 与 blocked reason 核对。'
  }
  if (usingFallbackValue) {
    return '当前引用来源已切换到本地只读回退视图，不开放真实客户/供应商维护、导入、导出、库存写入或 ERPNext 联动。'
  }
  return '当前仅开放 stock-source / foundation-reference 只读核对，不开放客户/供应商真实维护、导入、导出、库存写入或跨模块执行。'
}

const buildLedgerItems = (
  rows: StockLedgerItem[],
  blockedReason: string,
): SalesInventoryStockSourceGuardReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `${stockLedgerStatusLabel(row)} / Δ${formatAmount(row.actual_qty)} / 结存 ${formatAmount(row.qty_after_transaction)}`,
    sourceLabel: `${row.voucher_type || FALLBACK_TEXT} / ${row.voucher_no || FALLBACK_TEXT}`,
    blockedReason,
  }))

const buildSummaryItems = (
  rows: StockSummaryItem[],
  blockedReason: string,
): SalesInventoryStockSourceGuardReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `结存 ${formatAmount(row.balance_qty)}`,
    sourceLabel: `${row.latest_posting_date || FALLBACK_TEXT} ${row.latest_posting_time || ''}`.trim(),
    blockedReason,
  }))

const buildAggregationItems = (
  rows: SalesInventoryAggregationItem[],
  blockedReason: string,
): SalesInventoryStockSourceGuardReadonlyItem[] =>
  rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.item_code || FALLBACK_TEXT} / ${row.warehouse || FALLBACK_TEXT}`,
    statusLabel: `实际 ${formatAmount(row.actual_qty)} / 占用 ${formatAmount(row.ordered_qty)}`,
    sourceLabel: `安全 ${formatAmount(row.safety_stock)} / 补货 ${formatAmount(row.reorder_level)}`,
    blockedReason,
  }))

const buildItems = (
  rows: SalesInventoryReferenceRow[],
  blockedReason: string,
): SalesInventoryStockSourceGuardReadonlyItem[] => {
  if (rows.length === 0) {
    return [
      {
        subjectLabel: 'partner-source / default',
        statusLabel: 'guarded / waiting',
        sourceLabel: 'stock-source / parity mirror',
        blockedReason,
      },
    ]
  }

  return rows.slice(0, 6).map((row) => ({
    subjectLabel: `${row.referenceType === 'customers' ? '客户' : '供应商'} / ${row.code || FALLBACK_TEXT}`,
    statusLabel: `${row.status || FALLBACK_TEXT} / ${row.name || FALLBACK_TEXT}`,
    sourceLabel: `${row.parityScope || FALLBACK_TEXT} / ${row.readonlySourceTag || FALLBACK_TEXT}`,
    blockedReason: row.missingSourcePrompt || blockedReason,
  }))
}

const isStockLedgerMode = (
  options: UseSalesInventoryStockSourceGuardReadonlyOptions,
): options is StockLedgerModeOptions => {
  return 'summaryRows' in options || 'aggregationRows' in options || 'requiredItemCode' in options
}

export const useSalesInventoryStockSourceGuardReadonly = (
  options: UseSalesInventoryStockSourceGuardReadonlyOptions,
): {
  stockSourceGuardReadonlySummary: ComputedRef<SalesInventoryStockSourceGuardReadonlyViewSummary>
} => {
  const stockSourceGuardReadonlySummary = computed<SalesInventoryStockSourceGuardReadonlyViewSummary>(() => {
    if (isStockLedgerMode(options)) {
      const ledgerRows = unref(options.rows) || []
      const sourceSummaryRows = unref(options.summaryRows) || []
      const sourceAggregationRows = unref(options.aggregationRows) || []
      const tabValue = normalizeText(unref(options.tab)) || 'source-guard-readonly'
      const parityValue = normalizeText(unref(options.parity)) || 'material-stock'
      const focusValue = normalizeText(unref(options.focus)) || 'stock-source'
      const normalizedItemCode = normalizeText(unref(options.itemCode))
      const readable = Boolean(unref(options.canRead))
      const itemCodeRequired = Boolean(unref(options.requiredItemCode))
      const errorMessage = normalizeText(unref(options.lastError))
      const dropped = Number(unref(options.droppedCount) || 0)

      const warehouseSet = new Set<string>()
      ledgerRows.forEach((row) => {
        if (row.warehouse) warehouseSet.add(row.warehouse)
      })
      sourceSummaryRows.forEach((row) => {
        if (row.warehouse) warehouseSet.add(row.warehouse)
      })
      sourceAggregationRows.forEach((row) => {
        if (row.warehouse) warehouseSet.add(row.warehouse)
      })

      const warningCount =
        ledgerRows.filter((row) => stockLedgerStatusLabel(row) !== '正常').length +
        sourceAggregationRows.filter((row) => row.is_below_safety || row.is_below_reorder).length

      const blockedReason = buildStockLedgerFallbackReason(readable, itemCodeRequired, errorMessage)
      const hasReadableSource =
        ledgerRows.length > 0 || sourceSummaryRows.length > 0 || sourceAggregationRows.length > 0

      let items = buildLedgerItems(ledgerRows, blockedReason)
      if (items.length === 0) items = buildSummaryItems(sourceSummaryRows, blockedReason)
      if (items.length === 0) items = buildAggregationItems(sourceAggregationRows, blockedReason)
      if (items.length === 0) {
        items = [
          {
            subjectLabel: `${normalizedItemCode || '待输入款号'} / stock-source`,
            statusLabel: itemCodeRequired ? '待输入款号' : '来源待回读',
            sourceLabel: `${parityValue || 'material-stock'} / ${focusValue || 'stock-source'}`,
            blockedReason,
          },
        ]
      }

      let state: SalesInventoryStockSourceGuardState = 'ready-readonly'
      if (!readable) {
        state = 'permission-guarded'
      } else if (itemCodeRequired) {
        state = 'query-guarded'
      } else if (errorMessage || warningCount > 0) {
        state = 'source-warning'
      }

      const cards: SalesInventoryStockSourceGuardReadonlyCard[] =
        SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_SUMMARY_FIELDS.map((field) => {
          const values: Record<string, string> = {
            sourceCoverageLabel: `${ledgerRows.length} 条流水 / ${sourceSummaryRows.length} 条摘要`,
            statusCoverageLabel: `${items.length} 条来源状态 / ${hasReadableSource ? 'ready' : 'pending'}`,
            warehouseCountLabel: String(warehouseSet.size),
            warningCountLabel: String(warningCount),
            droppedCountLabel: String(dropped),
          }
          return {
            key: field.key,
            label: field.label,
            value: values[field.key],
          }
        })

      let sourceStatusLabel = 'stock-source pending'
      let sourceStatusTone: SalesInventoryStockSourceGuardTagType = 'info'
      if (!readable) {
        sourceStatusLabel = 'stock-source permission guarded'
        sourceStatusTone = 'danger'
      } else if (itemCodeRequired) {
        sourceStatusLabel = 'stock-source query waiting for item_code'
        sourceStatusTone = 'warning'
      } else if (errorMessage) {
        sourceStatusLabel = 'stock-source readback blocked'
        sourceStatusTone = 'danger'
      } else if (hasReadableSource) {
        sourceStatusLabel = `stock-source readback ready / ${items.length} rows`
        sourceStatusTone = warningCount > 0 ? 'warning' : 'success'
      }

      return {
        titleLabel: '库存流水 stock-source guard 只读回读',
        testIdPrefix: 'cand472-stock-ledger-source-guard',
        emptyText: '暂无 stock-source 只读条目',
        queryStateLabel: `${tabValue} | parity=${parityValue} | focus=${focusValue} | item_code=${normalizedItemCode || FALLBACK_TEXT}`,
        parityLabel: SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_PARITY_LABEL,
        parityTone: parityValue === 'material-stock' ? 'success' : 'warning',
        focusLabel: SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_FOCUS_LABEL,
        focusTone: focusValue === 'stock-source' ? 'warning' : 'info',
        stateLabel: SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_STATE_LABELS[state],
        stateTone: SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_STATE_TAGS[state],
        sourceStatusLabel,
        sourceStatusTone,
        itemStatusLabel: `${items.length} 条来源状态 / 仓库 ${warehouseSet.size} / 预警 ${warningCount}`,
        blockedReason,
        readonlyGuardReason: SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_READONLY_GUARD_REASON,
        remainingGap: SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_REMAINING_GAP,
        writeBoundary: SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_WRITE_BOUNDARY,
        cards,
        disabledActions: SALES_INVENTORY_STOCK_LEDGER_SOURCE_GUARD_DISABLED_ACTIONS.map((action) => ({
          label: action.label,
          reason: action.reason,
        })),
        items,
      }
    }

    const currentRows = unref(options.rows) || []
    const activeTabValue = unref(options.activeTab) || 'customers'
    const currentPathValue = normalizeText(unref(options.currentPath)) || '/sales-inventory/references'
    const tabValue = normalizeText(unref(options.tab)) || 'stock-source-guard-readonly'
    const parityValue = normalizeText(unref(options.parity)) || 'foundation-reference'
    const focusValue = normalizeText(unref(options.focus)) || 'stock-source'
    const filterLabel = normalizeText(unref(options.filterStateLabel)) || 'keyword=-; status=all; source=all'
    const usingFallbackValue = Boolean(unref(options.usingFallback))
    const readable = Boolean(unref(options.canRead))
    const hasRows = currentRows.length > 0
    const activeCount = currentRows.filter((row) => row.status === 'active').length
    const issueCount = currentRows.filter((row) => row.sourceValidationState !== 'verified').length
    const missingCount = currentRows.filter((row) => row.sourceValidationState === 'missing').length
    const customerCount = currentRows.filter((row) => row.referenceType === 'customers').length
    const supplierCount = currentRows.filter((row) => row.referenceType === 'suppliers').length

    const blockedReason = buildBlockedReason(
      readable,
      hasRows,
      usingFallbackValue,
      missingCount,
      activeTabValue,
    )
    const items = buildItems(currentRows, blockedReason)

    let state: SalesInventoryStockSourceGuardState = 'ready-readonly'
    if (!readable) {
      state = 'permission-guarded'
    } else if (!hasRows) {
      state = 'query-guarded'
    } else if (issueCount > 0) {
      state = 'source-warning'
    }

    const cards: SalesInventoryStockSourceGuardReadonlyCard[] =
      SALES_INVENTORY_STOCK_SOURCE_GUARD_SUMMARY_FIELDS.map((field) => {
        const values: Record<string, string> = {
          referenceCountLabel: String(currentRows.length),
          activeReferenceCountLabel: String(activeCount),
          issueCountLabel: String(issueCount),
          guardedActionCountLabel: String(SALES_INVENTORY_STOCK_SOURCE_GUARD_DISABLED_ACTIONS.length),
        }
        return {
          key: field.key,
          label: field.label,
          value: values[field.key],
        }
      })

    let sourceStatusLabel = 'stock-source pending'
    let sourceStatusTone: SalesInventoryStockSourceGuardTagType = 'info'
    if (!readable) {
      sourceStatusLabel = 'stock-source permission guarded'
      sourceStatusTone = 'danger'
    } else if (!hasRows) {
      sourceStatusLabel = 'stock-source guarded / no rows'
      sourceStatusTone = 'warning'
    } else if (missingCount > 0) {
      sourceStatusLabel = `stock-source missing / ${missingCount} rows`
      sourceStatusTone = 'danger'
    } else if (issueCount > 0) {
      sourceStatusLabel = `stock-source fallback / ${issueCount} rows`
      sourceStatusTone = 'warning'
    } else {
      sourceStatusLabel = `stock-source readback ready / ${currentRows.length} rows`
      sourceStatusTone = 'success'
    }

    return {
      titleLabel: 'stock-source guard 只读核对',
      testIdPrefix: 'cand532-sales-inventory-reference-stock-source-guard',
      emptyText: '暂无 stock-source guard 只读条目',
      queryStateLabel: `tab=${tabValue}; active_tab=${activeTabValue}; route=${currentPathValue}; filters=${filterLabel}`,
      parityLabel:
        parityValue === 'foundation-reference'
          ? SALES_INVENTORY_STOCK_SOURCE_GUARD_PARITY_LABEL
          : `${parityValue || 'foundation-reference'} / fallback`,
      parityTone: parityValue === 'foundation-reference' ? 'success' : 'warning',
      focusLabel:
        focusValue === 'stock-source'
          ? SALES_INVENTORY_STOCK_SOURCE_GUARD_FOCUS_LABEL
          : `${focusValue || 'stock-source'} / fallback`,
      focusTone: focusValue === 'stock-source' ? 'warning' : 'info',
      stateLabel: SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_LABELS[state],
      stateTone: SALES_INVENTORY_STOCK_SOURCE_GUARD_STATE_TAGS[state],
      sourceStatusLabel,
      sourceStatusTone,
      itemStatusLabel: `${currentRows.length} rows / customers ${customerCount} / suppliers ${supplierCount}`,
      blockedReason,
      readonlyGuardReason: SALES_INVENTORY_STOCK_SOURCE_GUARD_READONLY_GUARD_REASON,
      remainingGap: SALES_INVENTORY_STOCK_SOURCE_GUARD_REMAINING_GAP,
      writeBoundary: SALES_INVENTORY_STOCK_SOURCE_GUARD_WRITE_BOUNDARY,
      cards,
      disabledActions: SALES_INVENTORY_STOCK_SOURCE_GUARD_DISABLED_ACTIONS.map((action) => ({
        label: action.label,
        reason: action.reason,
      })),
      items,
    }
  })

  return {
    stockSourceGuardReadonlySummary,
  }
}
