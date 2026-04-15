import type { FactoryStatementDetailData, FactoryStatementDetailItem } from '@/api/factory_statement'

const FORMULA_INJECTION_PREFIX = /^[=+\-@\t\r\n]/

const CSV_HEADERS = [
  'statement_no',
  'company',
  'supplier',
  'from_date',
  'to_date',
  'status',
  'gross_amount',
  'deduction_amount',
  'net_amount',
  'inspection_no',
  'subcontract_no',
  'subcontract_id',
  'accepted_qty',
  'rejected_qty',
  'rejected_rate',
  'item_gross_amount',
  'item_deduction_amount',
  'item_net_amount',
]

const toText = (value: unknown): string => {
  if (value === null || value === undefined) {
    return ''
  }
  return String(value)
}

const neutralizeCsvFormula = (value: string): string => {
  if (FORMULA_INJECTION_PREFIX.test(value)) {
    return `'${value}`
  }
  return value
}

const escapeCsvCell = (value: unknown): string => {
  const text = neutralizeCsvFormula(toText(value))
  if (text.includes('"')) {
    return `"${text.replace(/"/g, '""')}"`
  }
  if (text.includes(',') || text.includes('\n') || text.includes('\r')) {
    return `"${text}"`
  }
  return text
}

const statementRow = (detail: FactoryStatementDetailData, item: FactoryStatementDetailItem | null): string[] => {
  return [
    detail.statement_no,
    detail.company,
    detail.supplier,
    detail.from_date,
    detail.to_date,
    detail.statement_status,
    detail.gross_amount,
    detail.deduction_amount,
    detail.net_amount,
    item?.inspection_no || '',
    item?.subcontract_no || '',
    item?.subcontract_id || '',
    item?.accepted_qty || '',
    item?.rejected_qty || '',
    item?.rejected_rate || '',
    item?.gross_amount || '',
    item?.deduction_amount || '',
    item?.net_amount || '',
  ].map((cell) => escapeCsvCell(cell))
}

const sanitizeFilePart = (raw: string): string => {
  const trimmed = raw.trim()
  if (!trimmed) {
    return 'unknown'
  }
  return trimmed.replace(/[^a-zA-Z0-9_-]+/g, '_')
}

const downloadCsv = (filename: string, content: string): void => {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' })
  const objectUrl = URL.createObjectURL(blob)
  const anchor = document.createElement('a')
  anchor.href = objectUrl
  anchor.download = filename
  document.body.appendChild(anchor)
  anchor.click()
  document.body.removeChild(anchor)
  URL.revokeObjectURL(objectUrl)
}

export const exportFactoryStatementDetailCsv = (detail: FactoryStatementDetailData): string => {
  const rows: string[] = [CSV_HEADERS.join(',')]
  const detailItems = detail.items || []
  if (detailItems.length === 0) {
    rows.push(statementRow(detail, null).join(','))
  } else {
    for (const item of detailItems) {
      rows.push(statementRow(detail, item).join(','))
    }
  }

  const filename = `factory_statement_${sanitizeFilePart(detail.statement_no)}.csv`
  downloadCsv(filename, `${rows.join('\n')}\n`)
  return filename
}
