export type BomReadonlyTagType = 'success' | 'warning' | 'danger' | 'info'
export type BomAlternateReadonlyState = 'verified' | 'fallback' | 'missing'

export interface BomAlternateFallbackLine {
  materialItemCode: string
  materialName: string
  color: string
  size: string
  qtyPerPiece: number
  remark: string
}

export const BOM_ALTERNATE_STATE_TAGS: Record<BomAlternateReadonlyState, BomReadonlyTagType> = {
  verified: 'success',
  fallback: 'warning',
  missing: 'danger',
}

export const BOM_ALTERNATE_STATE_LABELS: Record<BomAlternateReadonlyState, string> = {
  verified: '替代料已回读',
  fallback: '替代料本地回退',
  missing: '替代料待补齐',
}

export const BOM_PARITY_SCOPE_LABELS: Record<string, string> = {
  'material-fabric': 'material-fabric parity',
  default: 'bom-readonly',
}

export const BOM_COLOR_SIZE_SUMMARY_FIELDS = [
  { key: 'skuCount', label: '颜色尺码组合' },
  { key: 'materialCount', label: '物料行' },
  { key: 'alternateCount', label: '替代料状态' },
  { key: 'parityScopeLabel', label: '当前入口' },
] as const

export const BOM_ALTERNATE_HINT_KEYWORDS = ['替代', '替换', '备用', '代用', 'ALT']

export const BOM_ALTERNATE_FALLBACK_LINES: BomAlternateFallbackLine[] = [
  {
    materialItemCode: 'FAB-CT-0021',
    materialName: '32支精梳棉汗布',
    color: '米白',
    size: 'M',
    qtyPerPiece: 1.28,
    remark: '替代料: FAB-CT-0021-B',
  },
  {
    materialItemCode: 'FAB-RB-0012',
    materialName: '1x1 罗纹',
    color: '米白',
    size: 'L',
    qtyPerPiece: 0.11,
    remark: '袖口罗纹，替代料待确认',
  },
  {
    materialItemCode: 'TRM-LB-1022',
    materialName: '主唛+洗水唛套组',
    color: '标准',
    size: 'SET',
    qtyPerPiece: 1,
    remark: '本地只读回退',
  },
]

export const BOM_WRITE_BOUNDARY_LABEL = 'create / update / delete / export disabled'
export const BOM_REMAINING_GAP_LABEL =
  '未开放真实物料保存、导出、库存影响、ERPNext、outbox、worker。'
