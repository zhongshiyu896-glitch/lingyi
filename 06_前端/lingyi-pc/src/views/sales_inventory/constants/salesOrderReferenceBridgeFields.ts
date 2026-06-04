export type SalesOrderReferenceBridgeCompletenessState = 'ready' | 'factory-pending' | 'customer-missing'

export const SALES_ORDER_REFERENCE_BRIDGE_COMPLETENESS_LABELS: Record<
  SalesOrderReferenceBridgeCompletenessState,
  string
> = {
  ready: '来源链完整',
  'factory-pending': '待补工厂映射',
  'customer-missing': '待补客户引用链',
}

export const SALES_ORDER_REFERENCE_BRIDGE_COMPLETENESS_TAGS: Record<
  SalesOrderReferenceBridgeCompletenessState,
  'success' | 'warning' | 'danger'
> = {
  ready: 'success',
  'factory-pending': 'warning',
  'customer-missing': 'danger',
}

export const SALES_ORDER_REFERENCE_BRIDGE_SUMMARY_FIELDS = [
  { key: 'customerNodeCount', label: '客户节点' },
  { key: 'factoryNodeCount', label: '工厂节点' },
  { key: 'sourceDocumentCount', label: '来源单据' },
  { key: 'mappingModeLabel', label: '映射模式' },
  { key: 'completenessLabel', label: '桥接完整度' },
] as const
