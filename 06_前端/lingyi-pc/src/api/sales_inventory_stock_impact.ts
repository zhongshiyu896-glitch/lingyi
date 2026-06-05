import {
  fetchSalesInventoryAggregation,
  fetchSalesInventoryStockSummary,
  type SalesInventoryAggregationItem,
  type StockSummaryItem,
} from '@/api/sales_inventory'

export interface StockLedgerImpactReadonlyQuery {
  itemCode: string
  company?: string
  warehouse?: string
}

export interface StockLedgerImpactReadonlySnapshot {
  itemCode: string
  company?: string
  warehouse?: string
  summaryRows: StockSummaryItem[]
  summaryDroppedCount: number
  aggregationRows: SalesInventoryAggregationItem[]
  warehouseCount: number
  belowSafetyCount: number
  batchRelationFallback: string
}

const normalizeText = (value?: string): string | undefined => {
  const normalized = value?.trim()
  return normalized ? normalized : undefined
}

const buildBatchRelationFallback = (itemCode: string, warehouseCount: number): string => {
  if (warehouseCount <= 0) {
    return `款号 ${itemCode || '-'} 当前无仓库聚合数据，批次关系保持只读回退。`
  }
  return `款号 ${itemCode || '-'} 当前按 ${warehouseCount} 个仓库聚合回读，批次关系待真实库存链路开放后补齐。`
}

export const fetchStockLedgerImpactReadonlySnapshot = async (
  query: StockLedgerImpactReadonlyQuery,
): Promise<StockLedgerImpactReadonlySnapshot> => {
  const itemCode = query.itemCode.trim()
  const company = normalizeText(query.company)
  const warehouse = normalizeText(query.warehouse)
  const [summaryResult, aggregationResult] = await Promise.all([
    fetchSalesInventoryStockSummary(itemCode, {
      company,
      warehouse,
    }),
    fetchSalesInventoryAggregation({
      company,
      item_code: itemCode,
      warehouse,
    }),
  ])

  const summaryRows = summaryResult.data.items
  const aggregationRows = aggregationResult.data.items
  const warehouses = new Set<string>()
  summaryRows.forEach((row) => {
    if (row.warehouse) warehouses.add(row.warehouse)
  })
  aggregationRows.forEach((row) => {
    if (row.warehouse) warehouses.add(row.warehouse)
  })
  const belowSafetyCount = aggregationRows.filter((row) => row.is_below_safety || row.is_below_reorder).length

  return {
    itemCode,
    company: summaryResult.data.company || aggregationResult.data.company || company,
    warehouse: summaryResult.data.warehouse || aggregationResult.data.warehouse || warehouse,
    summaryRows,
    summaryDroppedCount: summaryResult.data.dropped_count,
    aggregationRows,
    warehouseCount: warehouses.size,
    belowSafetyCount,
    batchRelationFallback: buildBatchRelationFallback(itemCode, warehouses.size),
  }
}
