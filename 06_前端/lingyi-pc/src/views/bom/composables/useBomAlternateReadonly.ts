import type { BomDetailData } from '@/api/bom'
import {
  BOM_ALTERNATE_FALLBACK_LINES,
  BOM_ALTERNATE_HINT_KEYWORDS,
  BOM_ALTERNATE_STATE_LABELS,
  BOM_ALTERNATE_STATE_TAGS,
  BOM_PARITY_SCOPE_LABELS,
  BOM_REMAINING_GAP_LABEL,
  BOM_WRITE_BOUNDARY_LABEL,
  type BomAlternateReadonlyState,
  type BomReadonlyTagType,
} from '@/views/bom/constants/bomAlternateMaterialFields'

type SourceKind = 'detail-readback' | 'local-readback' | 'fallback-readonly'

interface BomReadonlyReadbackLine {
  material_item_code: string
  material_name?: string
  color?: string
  size?: string
  qty_per_piece?: number | string
  remark?: string
}

interface BomReadonlyReadbackData {
  fabric_lines: BomReadonlyReadbackLine[]
  trim_lines: BomReadonlyReadbackLine[]
}

interface BomReadonlyLine {
  materialItemCode: string
  materialName: string
  color: string
  size: string
  qtyPerPiece: number
  remark: string
  sourceKind: SourceKind
}

export interface BomColorSizeUsageReadonlyRow {
  key: string
  color: string
  size: string
  totalUsage: number
  totalUsageLabel: string
  materialCount: number
  sourceTag: string
}

export interface BomAlternateMaterialReadonlyRow {
  materialKey: string
  materialLabel: string
  colorSizeLabel: string
  alternateMaterialLabel: string
  alternateState: BomAlternateReadonlyState
  alternateStateLabel: string
  sourceTag: string
  note: string
}

export interface BomAlternateReadonlyDetailView {
  skuCount: number
  materialCount: number
  alternateCount: number
  parityScopeLabel: string
  readonlySourceTag: string
  readonlySourceType: BomReadonlyTagType
  coverageLabel: string
  coverageType: BomReadonlyTagType
  colorSizeUsageRows: BomColorSizeUsageReadonlyRow[]
  alternateRows: BomAlternateMaterialReadonlyRow[]
  readonlyGuardReason: string
  missingAlternatePrompt: string
  writeBoundary: string
  remainingGap: string
}

export interface BomAlternateListReadonlySummary {
  parityScopeLabel: string
  readonlySourceTag: string
  parityReadonlyHint: string
  readonlyGuardReason: string
  usageSummaryLabel: string
  alternateStatusLabel: string
  writeBoundary: string
  remainingGap: string
  rowCountLabel: string
}

export interface BomAlternateReadonlySectionSummary {
  tags: Array<{ key: string; label: string; type: BomReadonlyTagType }>
  readonlySourceLabel: string
  readonlyModeLabel: string
  parityLabel: string
  focusStateLabel: string
  queryStateLabel: string
  itemStatusLabel: string
  itemStatusTone: BomReadonlyTagType
  sourceStatusLabel: string
  blockedReasonSummary: string
  guardMessage: string
  remainingGap: string
  writeBoundary: string
  metrics: Array<{ key: string; label: string; value: string }>
  items: Array<{
    key: string
    title: string
    scopeLabel: string
    statusLabel: string
    statusTone: BomReadonlyTagType
    sourceStatusLabel: string
    blockedReason: string
    note: string
  }>
  guardedActions: Array<{ key: string; label: string; reason: string }>
}

const normalizeText = (value: unknown, fallback = '-'): string => {
  if (typeof value !== 'string') return fallback
  const trimmed = value.trim()
  return trimmed || fallback
}

const toUsageNumber = (value: unknown): number => {
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric : 0
}

const formatUsage = (value: number): string =>
  value.toLocaleString('zh-CN', {
    minimumFractionDigits: value % 1 === 0 ? 0 : 2,
    maximumFractionDigits: 2,
  })

const parityScopeLabel = (parity: string): string =>
  BOM_PARITY_SCOPE_LABELS[parity] || BOM_PARITY_SCOPE_LABELS.default

const sourceTag = (sourceKind: SourceKind): string => {
  if (sourceKind === 'detail-readback') return 'BOM详情回读'
  if (sourceKind === 'local-readback') return '本地只读回读'
  return '静态只读回退'
}

const sourceTagType = (sourceKind: SourceKind): BomReadonlyTagType => {
  if (sourceKind === 'detail-readback') return 'success'
  if (sourceKind === 'local-readback') return 'warning'
  return 'info'
}

const buildDetailLines = (detail: BomDetailData | null): BomReadonlyLine[] => {
  if (!detail?.items?.length) return []
  return detail.items.map((item) => ({
    materialItemCode: normalizeText(item.material_item_code),
    materialName: normalizeText(item.remark, normalizeText(item.material_item_code)),
    color: normalizeText(item.color, '未标色'),
    size: normalizeText(item.size, '均码'),
    qtyPerPiece: toUsageNumber(item.qty_per_piece),
    remark: normalizeText(item.remark, ''),
    sourceKind: 'detail-readback',
  }))
}

const buildLocalLines = (readback: BomReadonlyReadbackData | null): BomReadonlyLine[] => {
  if (!readback) return []
  const fabricLines = readback.fabric_lines.map((line) => ({
    materialItemCode: normalizeText(line.material_item_code),
    materialName: normalizeText(line.material_name, normalizeText(line.material_item_code)),
    color: normalizeText(line.color, '未标色'),
    size: normalizeText(line.size, '均码'),
    qtyPerPiece: toUsageNumber(line.qty_per_piece),
    remark: normalizeText(line.remark, ''),
    sourceKind: 'local-readback' as const,
  }))
  const trimLines = readback.trim_lines.map((line) => ({
    materialItemCode: normalizeText(line.material_item_code),
    materialName: normalizeText(line.material_name, normalizeText(line.material_item_code)),
    color: normalizeText(line.color, '未标色'),
    size: normalizeText(line.size, '均码'),
    qtyPerPiece: toUsageNumber(line.qty_per_piece),
    remark: normalizeText(line.remark, ''),
    sourceKind: 'local-readback' as const,
  }))
  return [...fabricLines, ...trimLines]
}

const buildFallbackLines = (): BomReadonlyLine[] =>
  BOM_ALTERNATE_FALLBACK_LINES.map((line) => ({
    materialItemCode: line.materialItemCode,
    materialName: line.materialName,
    color: line.color,
    size: line.size,
    qtyPerPiece: line.qtyPerPiece,
    remark: line.remark,
    sourceKind: 'fallback-readonly',
  }))

const resolveReadonlyLines = (
  detail: BomDetailData | null,
  readback: BomReadonlyReadbackData | null,
): BomReadonlyLine[] => {
  const detailLines = buildDetailLines(detail)
  if (detailLines.length) return detailLines
  const localLines = buildLocalLines(readback)
  if (localLines.length) return localLines
  return buildFallbackLines()
}

const extractAlternateMaterialLabel = (remark: string): string => {
  const patterns = [
    /替代(?:料)?[:：]\s*([A-Za-z0-9._/-]+)/i,
    /备用(?:料)?[:：]\s*([A-Za-z0-9._/-]+)/i,
    /代用(?:料)?[:：]\s*([A-Za-z0-9._/-]+)/i,
  ]
  for (const pattern of patterns) {
    const matched = remark.match(pattern)
    if (matched?.[1]) {
      return matched[1].trim()
    }
  }
  return ''
}

const buildAlternateState = (
  line: BomReadonlyLine,
): Pick<BomAlternateMaterialReadonlyRow, 'alternateState' | 'alternateStateLabel' | 'alternateMaterialLabel' | 'note'> => {
  const remark = normalizeText(line.remark, '')
  const explicitAlternate = extractAlternateMaterialLabel(remark)
  if (explicitAlternate) {
    return {
      alternateState: 'verified',
      alternateStateLabel: BOM_ALTERNATE_STATE_LABELS.verified,
      alternateMaterialLabel: explicitAlternate,
      note: '已从回读备注解析替代料',
    }
  }

  const hasKeyword = BOM_ALTERNATE_HINT_KEYWORDS.some((keyword) => remark.toUpperCase().includes(keyword))
  if (hasKeyword) {
    return {
      alternateState: 'fallback',
      alternateStateLabel: BOM_ALTERNATE_STATE_LABELS.fallback,
      alternateMaterialLabel: '本地回退待确认',
      note: remark || '检测到替代料提示，但未命中可确认编码',
    }
  }

  return {
    alternateState: 'missing',
    alternateStateLabel: BOM_ALTERNATE_STATE_LABELS.missing,
    alternateMaterialLabel: '待补齐',
    note: '未检测到替代料标记',
  }
}

const buildColorSizeUsageRows = (lines: BomReadonlyLine[]): BomColorSizeUsageReadonlyRow[] => {
  const grouped = new Map<string, BomColorSizeUsageReadonlyRow>()
  lines.forEach((line) => {
    const key = `${line.color}__${line.size}`
    const current = grouped.get(key)
    if (current) {
      current.totalUsage += line.qtyPerPiece
      current.totalUsageLabel = formatUsage(current.totalUsage)
      current.materialCount += 1
      return
    }
    grouped.set(key, {
      key,
      color: line.color,
      size: line.size,
      totalUsage: line.qtyPerPiece,
      totalUsageLabel: formatUsage(line.qtyPerPiece),
      materialCount: 1,
      sourceTag: sourceTag(line.sourceKind),
    })
  })
  return [...grouped.values()]
}

const buildAlternateRows = (lines: BomReadonlyLine[]): BomAlternateMaterialReadonlyRow[] =>
  lines.slice(0, 6).map((line) => {
    const alternate = buildAlternateState(line)
    return {
      materialKey: line.materialItemCode,
      materialLabel: `${line.materialItemCode} / ${line.materialName}`,
      colorSizeLabel: `${line.color} / ${line.size}`,
      alternateMaterialLabel: alternate.alternateMaterialLabel,
      alternateState: alternate.alternateState,
      alternateStateLabel: alternate.alternateStateLabel,
      sourceTag: sourceTag(line.sourceKind),
      note: alternate.note,
    }
  })

const coverageLabel = (lines: BomReadonlyLine[]): string => {
  const kinds = new Set(lines.map((line) => line.sourceKind))
  if (kinds.has('detail-readback')) return 'detail-items'
  if (kinds.has('local-readback')) return 'local-readback'
  return 'fallback-sample'
}

const coverageType = (lines: BomReadonlyLine[]): BomReadonlyTagType => {
  const label = coverageLabel(lines)
  if (label === 'detail-items') return 'success'
  if (label === 'local-readback') return 'warning'
  return 'info'
}

export const useBomAlternateReadonly = () => {
  const buildBomAlternateListSummary = (
    rowCount: number,
    parity: string,
  ): BomAlternateListReadonlySummary => ({
    parityScopeLabel: parityScopeLabel(parity),
    readonlySourceTag: parity === 'material-fabric' ? 'material-fabric 只读入口' : 'BOM 列表只读回读',
    parityReadonlyHint:
      parity === 'material-fabric' ? '当前 alias 已重定向到 /bom/list?parity=material-fabric' : '',
    readonlyGuardReason:
      '当前仅提供 BOM 列表只读回读、颜色尺码用量入口提示和替代料状态概览；真实物料保存与库存影响已冻结。',
    usageSummaryLabel: '颜色尺码用量请在详情页查看',
    alternateStatusLabel: '替代料状态请在详情页查看',
    writeBoundary: BOM_WRITE_BOUNDARY_LABEL,
    remainingGap: BOM_REMAINING_GAP_LABEL,
    rowCountLabel: `${rowCount} 条只读行`,
  })

  const buildBomAlternateDetailView = (
    detail: BomDetailData | null,
    readback: BomReadonlyReadbackData | null,
    parity: string,
  ): BomAlternateReadonlyDetailView => {
    const lines = resolveReadonlyLines(detail, readback)
    const usageRows = buildColorSizeUsageRows(lines)
    const alternateRows = buildAlternateRows(lines)
    const verifiedCount = alternateRows.filter((row) => row.alternateState === 'verified').length
    const fallbackCount = alternateRows.filter((row) => row.alternateState === 'fallback').length
    const missingCount = alternateRows.filter((row) => row.alternateState === 'missing').length
    const primarySourceKind = lines[0]?.sourceKind || 'fallback-readonly'

    return {
      skuCount: usageRows.length,
      materialCount: lines.length,
      alternateCount: alternateRows.length,
      parityScopeLabel: parityScopeLabel(parity),
      readonlySourceTag: sourceTag(primarySourceKind),
      readonlySourceType: sourceTagType(primarySourceKind),
      coverageLabel: coverageLabel(lines),
      coverageType: coverageType(lines),
      colorSizeUsageRows: usageRows,
      alternateRows,
      readonlyGuardReason:
        '当前仅提供 BOM 颜色尺码用量、替代料与 material-fabric parity 的只读回读；真实物料保存、导出与库存影响已冻结。',
      missingAlternatePrompt:
        missingCount > 0 ? `存在 ${missingCount} 条物料未配置替代料，仅显示只读提示，不触发真实物料保存。` : '',
      writeBoundary: BOM_WRITE_BOUNDARY_LABEL,
      remainingGap: BOM_REMAINING_GAP_LABEL,
    }
  }

  const bomAlternateStateType = (state: BomAlternateReadonlyState): BomReadonlyTagType =>
    BOM_ALTERNATE_STATE_TAGS[state]

  return {
    bomAlternateStateType,
    buildBomAlternateDetailView,
    buildBomAlternateListSummary,
  }
}
