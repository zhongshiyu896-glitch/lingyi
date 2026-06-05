import { fetchFactoryStatementDetail, fetchFactoryStatements } from '@/api/factory_statement'
import type {
  FactoryStatementDetailData,
  FactoryStatementDetailItem,
  FactoryStatementLogItem,
} from '@/api/factory_statement'
import type { ApiResponse } from '@/api/request'

export interface FactoryStatementReadonlyAuditSummary {
  createdBy: string
  createdAt: string
  latestAction: string
  latestOperator: string
  latestOperatedAt: string
  latestRemark: string
}

export interface FactoryStatementReadonlySettlementSummary {
  periodText: string
  sourceCount: number
  itemCount: number
  logCount: number
  primarySubcontractNo: string
  primaryInspectionNo: string
  purchaseInvoiceName: string
  payableOutboxCount: number
  payableErrorCode: string
  payableErrorMessage: string
}

export interface FactoryStatementReadonlyAmountSummary {
  grossAmount: string | number | null | undefined
  deductionAmount: string | number | null | undefined
  netAmount: string | number | null | undefined
  inspectedQty: string | number | null | undefined
  rejectedQty: string | number | null | undefined
  rejectedRate: string | number | null | undefined
}

export interface FactoryStatementReadonlyRecord {
  raw: FactoryStatementDetailData
  items: FactoryStatementDetailItem[]
  logs: FactoryStatementLogItem[]
  auditSummary: FactoryStatementReadonlyAuditSummary
  settlementSummary: FactoryStatementReadonlySettlementSummary
  amountSummary: FactoryStatementReadonlyAmountSummary
}

const FALLBACK_TEXT = '-'

const pickLatestLog = (logs: FactoryStatementLogItem[]): FactoryStatementLogItem | null => {
  if (logs.length === 0) {
    return null
  }
  return logs.slice(1).reduce<FactoryStatementLogItem>((latest, current) => {
    const latestTime = Date.parse(latest.operated_at)
    const currentTime = Date.parse(current.operated_at)
    if (!Number.isNaN(latestTime) && !Number.isNaN(currentTime)) {
      return currentTime > latestTime ? current : latest
    }
    return current.operated_at > latest.operated_at ? current : latest
  }, logs[0])
}

const buildSettlementSummary = (
  detail: FactoryStatementDetailData,
  items: FactoryStatementDetailItem[],
  logs: FactoryStatementLogItem[],
): FactoryStatementReadonlySettlementSummary => {
  const firstItem = items[0]
  return {
    periodText: `${detail.from_date} ~ ${detail.to_date}`,
    sourceCount: detail.source_count,
    itemCount: items.length,
    logCount: logs.length,
    primarySubcontractNo: firstItem?.subcontract_no || FALLBACK_TEXT,
    primaryInspectionNo: firstItem?.inspection_no || FALLBACK_TEXT,
    purchaseInvoiceName: detail.purchase_invoice_name || FALLBACK_TEXT,
    payableOutboxCount: detail.payable_outboxes?.length || 0,
    payableErrorCode: detail.payable_error_code || FALLBACK_TEXT,
    payableErrorMessage: detail.payable_error_message || FALLBACK_TEXT,
  }
}

const buildAuditSummary = (detail: FactoryStatementDetailData, logs: FactoryStatementLogItem[]): FactoryStatementReadonlyAuditSummary => {
  const latestLog = pickLatestLog(logs)
  return {
    createdBy: detail.created_by || FALLBACK_TEXT,
    createdAt: detail.created_at || FALLBACK_TEXT,
    latestAction: latestLog?.action || '仅创建记录',
    latestOperator: latestLog?.operator || detail.created_by || FALLBACK_TEXT,
    latestOperatedAt: latestLog?.operated_at || detail.created_at || FALLBACK_TEXT,
    latestRemark: latestLog?.remark || FALLBACK_TEXT,
  }
}

export const buildFactoryStatementReadonlyRecord = (
  detail: FactoryStatementDetailData,
): FactoryStatementReadonlyRecord => {
  const items = detail.items || []
  const logs = detail.logs || []
  return {
    raw: detail,
    items,
    logs,
    auditSummary: buildAuditSummary(detail, logs),
    settlementSummary: buildSettlementSummary(detail, items, logs),
    amountSummary: {
      grossAmount: detail.gross_amount,
      deductionAmount: detail.deduction_amount,
      netAmount: detail.net_amount,
      inspectedQty: detail.inspected_qty,
      rejectedQty: detail.rejected_qty,
      rejectedRate: detail.rejected_rate,
    },
  }
}

export const fetchFactoryStatementReadonlyDetail = async (
  statementId: number,
): Promise<ApiResponse<FactoryStatementReadonlyRecord>> => {
  const result = await fetchFactoryStatementDetail(statementId)
  return {
    ...result,
    data: buildFactoryStatementReadonlyRecord(result.data),
  }
}

export const fetchFactoryStatementReadonlyFallbackId = async (): Promise<ApiResponse<number | null>> => {
  const result = await fetchFactoryStatements({
    page: 1,
    page_size: 1,
  })
  return {
    ...result,
    data: result.data.items[0]?.id ?? null,
  }
}
