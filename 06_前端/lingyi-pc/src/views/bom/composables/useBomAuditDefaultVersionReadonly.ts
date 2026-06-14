import type { BomDetailData } from '@/api/bom'
import {
  BOM_AUDIT_DEFAULT_VERSION_STATE_LABELS,
  BOM_AUDIT_DEFAULT_VERSION_STATE_TAGS,
  BOM_AUDIT_PARITY_SCOPE_LABELS,
  BOM_AUDIT_READONLY_GUARD_LABEL,
  BOM_AUDIT_REMAINING_GAP_LABEL,
  BOM_AUDIT_WRITE_BOUNDARY_LABEL,
  type BomAuditDefaultVersionState,
  type BomAuditReadonlyTagType,
} from '@/views/bom/constants/bomAuditDefaultVersionFields'

type SourceKind = 'detail-readback' | 'list-readback' | 'local-readback' | 'fallback-readonly'

interface BomAuditReadbackData {
  bom_main?: {
    bom_no?: string
    version_no?: string
    is_default?: boolean
  }
}

export interface BomAuditListRow {
  bomNo: string
  version: string
  status: string
  isDefault?: boolean
}

export interface BomAuditListReadonlySummary {
  parityScopeLabel: string
  readonlySourceTag: string
  readonlySourceType: BomAuditReadonlyTagType
  auditSourceLabel: string
  defaultVersionStatusLabel: string
  defaultVersionCoverageLabel: string
  versionSourceGapPrompt: string
  readonlyGuardReason: string
  writeBoundary: string
  remainingGap: string
  rowCountLabel: string
  parityReadonlyHint: string
}

export interface BomAuditDetailReadonlyRow {
  key: string
  label: string
  value: string
  note: string
}

export interface BomAuditDetailReadonlyView {
  parityScopeLabel: string
  readonlySourceTag: string
  readonlySourceType: BomAuditReadonlyTagType
  defaultVersionStatusLabel: string
  defaultVersionStatusType: BomAuditReadonlyTagType
  defaultVersionCoverageLabel: string
  versionSourceGapPrompt: string
  readonlyGuardReason: string
  writeBoundary: string
  remainingGap: string
  auditRows: BomAuditDetailReadonlyRow[]
}

const normalizeText = (value: unknown, fallback = '-'): string => {
  if (typeof value !== 'string') return fallback
  const trimmed = value.trim()
  return trimmed || fallback
}

const resolveParityScopeLabel = (parity: string): string =>
  BOM_AUDIT_PARITY_SCOPE_LABELS[parity] || BOM_AUDIT_PARITY_SCOPE_LABELS.default

const resolveSourceLabel = (sourceKind: SourceKind): string => {
  if (sourceKind === 'detail-readback') return 'BOM详情回读'
  if (sourceKind === 'list-readback') return 'BOM列表回读'
  if (sourceKind === 'local-readback') return '本地只读回读'
  return '静态只读回退'
}

const resolveSourceType = (sourceKind: SourceKind): BomAuditReadonlyTagType => {
  if (sourceKind === 'detail-readback' || sourceKind === 'list-readback') return 'success'
  if (sourceKind === 'local-readback') return 'warning'
  return 'info'
}

const resolveDefaultVersionState = (
  isDefault: boolean | null,
  sourceKind: SourceKind,
): BomAuditDefaultVersionState => {
  if (typeof isDefault === 'boolean') {
    return isDefault ? 'default-confirmed' : 'non-default'
  }
  if (sourceKind === 'detail-readback' || sourceKind === 'list-readback' || sourceKind === 'local-readback') {
    return 'fallback'
  }
  return 'missing'
}

const resolveListVersionGapPrompt = (
  sourceKind: SourceKind,
  parity: string,
  hasDefault: boolean,
): string => {
  if (parity === 'product-style') {
    return 'product-style parity 仅校验款式到 BOM 的默认版本映射，不开放真实版本切换。'
  }
  if (sourceKind === 'fallback-readonly') {
    return '当前默认版本状态来自静态只读回退，待真实 BOM 列表回读补齐。'
  }
  if (!hasDefault) {
    return '列表未命中默认版本标记，请结合详情只读确认版本来源是否断裂。'
  }
  return '默认版本状态已回读，但版本切换与审批仍保持只读。'
}

const resolveDetailVersionGapPrompt = (
  sourceKind: SourceKind,
  parity: string,
  isDefault: boolean | null,
): string => {
  if (parity === 'product-style') {
    return 'product-style parity 仅校验款式到 BOM 的默认版本映射，不开放真实版本切换。'
  }
  if (sourceKind === 'fallback-readonly') {
    return '当前仅静态回退，默认版本来源尚未建立真实详情只读映射。'
  }
  if (sourceKind === 'local-readback') {
    return '当前仅本地只读回读，默认版本来源仍待真实详情回读校验。'
  }
  if (isDefault === false) {
    return '当前展示版本不是默认版本，来源断裂提示仅用于只读确认。'
  }
  return '默认版本来源已回读，但真实版本切换与审批仍保持关闭。'
}

export const useBomAuditDefaultVersionReadonly = () => {
  const bomAuditDefaultVersionStateType = (state: BomAuditDefaultVersionState): BomAuditReadonlyTagType =>
    BOM_AUDIT_DEFAULT_VERSION_STATE_TAGS[state]

  const buildBomAuditListSummary = (
    rows: BomAuditListRow[],
    parity: string,
    loadedFromApi: boolean,
  ): BomAuditListReadonlySummary => {
    const sourceKind: SourceKind = loadedFromApi && rows.length ? 'list-readback' : 'fallback-readonly'
    const defaultCount = rows.filter((row) => row.isDefault === true).length
    const defaultState = resolveDefaultVersionState(defaultCount > 0 ? true : null, sourceKind)
    return {
      parityScopeLabel: resolveParityScopeLabel(parity),
      readonlySourceTag: resolveSourceLabel(sourceKind),
      readonlySourceType: resolveSourceType(sourceKind),
      auditSourceLabel: resolveSourceLabel(sourceKind),
      defaultVersionStatusLabel: BOM_AUDIT_DEFAULT_VERSION_STATE_LABELS[defaultState],
      defaultVersionCoverageLabel: `${defaultCount}/${rows.length || 0} 命中默认版本`,
      versionSourceGapPrompt: resolveListVersionGapPrompt(sourceKind, parity, defaultCount > 0),
      readonlyGuardReason: BOM_AUDIT_READONLY_GUARD_LABEL,
      writeBoundary: BOM_AUDIT_WRITE_BOUNDARY_LABEL,
      remainingGap: BOM_AUDIT_REMAINING_GAP_LABEL,
      rowCountLabel: `${rows.length} 条只读记录`,
      parityReadonlyHint:
        parity === 'product-style' ? 'product-style parity 入口仅回读默认版本状态与来源，不开放真实切换。' : '',
    }
  }

  const buildBomAuditDetailView = (
    detail: BomDetailData | null,
    readback: BomAuditReadbackData | null,
    parity: string,
  ): BomAuditDetailReadonlyView => {
    const sourceKind: SourceKind = detail?.bom
      ? 'detail-readback'
      : readback?.bom_main
        ? 'local-readback'
        : 'fallback-readonly'
    const isDefault =
      typeof detail?.bom?.is_default === 'boolean'
        ? detail.bom.is_default
        : typeof readback?.bom_main?.is_default === 'boolean'
          ? readback.bom_main.is_default
          : null
    const defaultState = resolveDefaultVersionState(isDefault, sourceKind)
    const versionNo = normalizeText(detail?.bom?.version_no ?? readback?.bom_main?.version_no, '-')
    const auditSourceLabel = resolveSourceLabel(sourceKind)
    const defaultVersionCoverageLabel =
      sourceKind === 'detail-readback'
        ? `详情版本 ${versionNo}`
        : sourceKind === 'local-readback'
          ? `本地回读版本 ${versionNo}`
          : '静态回退版本待确认'
    const versionSourceGapPrompt = resolveDetailVersionGapPrompt(sourceKind, parity, isDefault)
    return {
      parityScopeLabel: resolveParityScopeLabel(parity),
      readonlySourceTag: auditSourceLabel,
      readonlySourceType: resolveSourceType(sourceKind),
      defaultVersionStatusLabel: BOM_AUDIT_DEFAULT_VERSION_STATE_LABELS[defaultState],
      defaultVersionStatusType: bomAuditDefaultVersionStateType(defaultState),
      defaultVersionCoverageLabel,
      versionSourceGapPrompt,
      readonlyGuardReason: BOM_AUDIT_READONLY_GUARD_LABEL,
      writeBoundary: BOM_AUDIT_WRITE_BOUNDARY_LABEL,
      remainingGap: BOM_AUDIT_REMAINING_GAP_LABEL,
      auditRows: [
        {
          key: 'audit-source',
          label: '审计来源',
          value: auditSourceLabel,
          note: sourceKind === 'detail-readback' ? '优先使用详情回读' : '回退到只读来源',
        },
        {
          key: 'default-version-status',
          label: '默认版本状态',
          value: BOM_AUDIT_DEFAULT_VERSION_STATE_LABELS[defaultState],
          note: `version_no=${versionNo}`,
        },
        {
          key: 'default-version-coverage',
          label: '版本覆盖',
          value: defaultVersionCoverageLabel,
          note: `scope=${resolveParityScopeLabel(parity)}`,
        },
        {
          key: 'version-source-gap',
          label: '版本来源断裂提示',
          value: versionSourceGapPrompt,
          note: 'readonly prompt',
        },
      ],
    }
  }

  return {
    bomAuditDefaultVersionStateType,
    buildBomAuditListSummary,
    buildBomAuditDetailView,
  }
}
