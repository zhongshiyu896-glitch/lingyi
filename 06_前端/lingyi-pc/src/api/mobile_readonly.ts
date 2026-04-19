import {
  fetchProductionPlanDetail,
  fetchProductionPlans,
  type ProductionPlanDetailData,
  type ProductionPlanListItem,
} from '@/api/production'
import {
  fetchStyleProfitSnapshotDetail,
  fetchStyleProfitSnapshots,
  type StyleProfitSnapshotDetailData,
  type StyleProfitSnapshotListItem,
} from '@/api/style_profit'
import {
  fetchSubcontractOrderDetail,
  fetchSubcontractOrders,
  type SubcontractOrderDetailData,
  type SubcontractOrderListItem,
} from '@/api/subcontract'
import {
  fetchQualityInspectionDetail,
  fetchQualityInspections,
  fetchQualityStatistics,
  type QualityInspectionDetailData,
  type QualityInspectionListItem,
  type QualityStatisticsData,
} from '@/api/quality'
import {
  fetchSalesInventorySalesOrders,
  fetchSalesInventoryStockSummary,
  type SalesOrderListItem,
  type StockSummaryData,
} from '@/api/sales_inventory'

const DEFAULT_PAGE_SIZE = 20
const PREVIEW_LIMIT = 5

type ProjectionSource = 'production' | 'cost' | 'subcontract' | 'quality' | 'inventory'
type PriorityLevel = 'high' | 'medium' | 'low'
type MessageLevel = 'critical' | 'warning' | 'info'

const ATTENTION_KEYWORDS = ['pending', 'queued', 'draft', 'failed', 'error', 'blocked', 'unresolved', 'not_enabled']

const normalizeStatus = (status?: string | null): string => (status || '').trim().toLowerCase()

const isAttentionStatus = (status?: string | null): boolean => {
  const normalized = normalizeStatus(status)
  return ATTENTION_KEYWORDS.some((keyword) => normalized.includes(keyword))
}

const resolvePageSize = (value?: number): number => {
  if (!value || value <= 0) {
    return DEFAULT_PAGE_SIZE
  }
  return Math.min(value, 100)
}

const toIso = (value?: string | null): string => value || new Date().toISOString()

const toPriority = (status?: string | null): PriorityLevel => {
  if (isAttentionStatus(status)) {
    return 'high'
  }
  const normalized = normalizeStatus(status)
  if (normalized.includes('review') || normalized.includes('processing')) {
    return 'medium'
  }
  return 'low'
}

const toMessageLevel = (priority: PriorityLevel): MessageLevel => {
  if (priority === 'high') {
    return 'critical'
  }
  if (priority === 'medium') {
    return 'warning'
  }
  return 'info'
}

export interface MobileReadonlyProjectionQuery {
  company?: string
  item_code?: string
  sales_order?: string
  supplier?: string
  customer?: string
  warehouse?: string
  status?: string
  from_date?: string
  to_date?: string
  page_size?: number
}

export interface MobileReadonlyTodoItem {
  id: string
  source: ProjectionSource
  title: string
  status: string
  priority: PriorityLevel
  updated_at: string
  detail_hint?: string | null
}

export interface MobileReadonlyMessageItem {
  id: string
  source: ProjectionSource
  title: string
  content: string
  level: MessageLevel
  created_at: string
}

export interface MobileReadonlyReminderItem {
  id: string
  source: ProjectionSource
  reminder_type: 'todo' | 'status' | 'projection'
  text: string
  created_at: string
}

export interface MobileReadonlyFrozenAction {
  action: string
  state: 'frozen'
  reason: string
}

export interface MobileReadonlyProductionBoardData {
  total: number
  attention_count: number
  items: ProductionPlanListItem[]
}

export interface MobileReadonlyCostBoardData {
  available: boolean
  total: number
  unresolved_count: number
  items: StyleProfitSnapshotListItem[]
  note?: string
}

export interface MobileReadonlySubcontractBoardData {
  total: number
  attention_count: number
  items: SubcontractOrderListItem[]
}

export interface MobileReadonlyQualityBoardData {
  total: number
  attention_count: number
  items: QualityInspectionListItem[]
  statistics: QualityStatisticsData
}

export interface MobileReadonlyInventoryBoardData {
  sales_order_total: number
  stock_summary: StockSummaryData | null
  sales_orders: SalesOrderListItem[]
}

export interface MobileReadonlyOverviewData {
  generated_at: string
  todos: MobileReadonlyTodoItem[]
  messages: MobileReadonlyMessageItem[]
  reminders: MobileReadonlyReminderItem[]
  boards: {
    production: MobileReadonlyProductionBoardData
    cost: MobileReadonlyCostBoardData
    subcontract: MobileReadonlySubcontractBoardData
    quality: MobileReadonlyQualityBoardData
    inventory: MobileReadonlyInventoryBoardData
  }
  frozen_actions: MobileReadonlyFrozenAction[]
}

export const MOBILE_READONLY_FROZEN_ACTIONS: MobileReadonlyFrozenAction[] = [
  {
    action: 'message_ack',
    state: 'frozen',
    reason: 'TASK-024C keeps mobile message acknowledgement as candidate semantics only.',
  },
  {
    action: 'notification_read_receipt',
    state: 'frozen',
    reason: 'Read receipt writeback remains frozen in TASK-024C.',
  },
  {
    action: 'collaboration_confirm',
    state: 'frozen',
    reason: 'Collaboration confirmation write flow is not part of this read-only task.',
  },
  {
    action: 'scan_upload_offline_cache',
    state: 'frozen',
    reason: 'Scan/upload/offline-cache write semantics remain frozen by design.',
  },
]

export const fetchMobileReadonlyProductionBoard = async (
  query: MobileReadonlyProjectionQuery,
): Promise<MobileReadonlyProductionBoardData> => {
  const response = await fetchProductionPlans({
    sales_order: query.sales_order,
    item_code: query.item_code,
    status: query.status,
    page: 1,
    page_size: resolvePageSize(query.page_size),
  })
  const items = response.data.items
  const attentionCount = items.filter(
    (item) => isAttentionStatus(item.status) || isAttentionStatus(item.latest_work_order_outbox?.status),
  ).length
  return {
    total: response.data.total,
    attention_count: attentionCount,
    items,
  }
}

export const fetchMobileReadonlyCostBoard = async (
  query: MobileReadonlyProjectionQuery,
): Promise<MobileReadonlyCostBoardData> => {
  if (!query.company || !query.item_code) {
    return {
      available: false,
      total: 0,
      unresolved_count: 0,
      items: [],
      note: 'company and item_code are required for style profit projection.',
    }
  }
  const response = await fetchStyleProfitSnapshots({
    company: query.company,
    item_code: query.item_code,
    sales_order: query.sales_order,
    from_date: query.from_date,
    to_date: query.to_date,
    page: 1,
    page_size: resolvePageSize(query.page_size),
  })
  const unresolvedCount = response.data.items.reduce((sum, item) => sum + item.unresolved_count, 0)
  return {
    available: true,
    total: response.data.total,
    unresolved_count: unresolvedCount,
    items: response.data.items,
  }
}

export const fetchMobileReadonlySubcontractBoard = async (
  query: MobileReadonlyProjectionQuery,
): Promise<MobileReadonlySubcontractBoardData> => {
  const response = await fetchSubcontractOrders({
    supplier: query.supplier,
    status: query.status,
    from_date: query.from_date,
    to_date: query.to_date,
    page: 1,
    page_size: resolvePageSize(query.page_size),
  })
  const items = response.data.items
  const attentionCount = items.filter(
    (item) =>
      isAttentionStatus(item.status) ||
      isAttentionStatus(item.latest_issue_sync_status) ||
      isAttentionStatus(item.latest_receipt_sync_status),
  ).length
  return {
    total: response.data.total,
    attention_count: attentionCount,
    items,
  }
}

export const fetchMobileReadonlyQualityBoard = async (
  query: MobileReadonlyProjectionQuery,
): Promise<MobileReadonlyQualityBoardData> => {
  const [listResponse, statisticsResponse] = await Promise.all([
    fetchQualityInspections({
      company: query.company,
      item_code: query.item_code,
      supplier: query.supplier,
      warehouse: query.warehouse,
      status: query.status,
      from_date: query.from_date,
      to_date: query.to_date,
      page: 1,
      page_size: resolvePageSize(query.page_size),
    }),
    fetchQualityStatistics({
      company: query.company,
      item_code: query.item_code,
      supplier: query.supplier,
      warehouse: query.warehouse,
      status: query.status,
      from_date: query.from_date,
      to_date: query.to_date,
    }),
  ])
  const items = listResponse.data.items
  const attentionCount = items.filter((item) => isAttentionStatus(item.status)).length
  return {
    total: listResponse.data.total,
    attention_count: attentionCount,
    items,
    statistics: statisticsResponse.data,
  }
}

export const fetchMobileReadonlyInventoryBoard = async (
  query: MobileReadonlyProjectionQuery,
): Promise<MobileReadonlyInventoryBoardData> => {
  const ordersResponse = await fetchSalesInventorySalesOrders({
    company: query.company,
    customer: query.customer,
    item_code: query.item_code,
    page: 1,
    page_size: resolvePageSize(query.page_size),
  })

  let stockSummary: StockSummaryData | null = null
  if (query.item_code) {
    const stockResponse = await fetchSalesInventoryStockSummary(query.item_code, {
      company: query.company,
      warehouse: query.warehouse,
    })
    stockSummary = stockResponse.data
  }

  return {
    sales_order_total: ordersResponse.data.total,
    sales_orders: ordersResponse.data.items,
    stock_summary: stockSummary,
  }
}

const buildTodos = (
  production: MobileReadonlyProductionBoardData,
  cost: MobileReadonlyCostBoardData,
  subcontract: MobileReadonlySubcontractBoardData,
  quality: MobileReadonlyQualityBoardData,
): MobileReadonlyTodoItem[] => {
  const productionTodos: MobileReadonlyTodoItem[] = production.items.slice(0, PREVIEW_LIMIT).map((item) => ({
    id: `production-plan-${item.id}`,
    source: 'production',
    title: `Production plan ${item.plan_no}`,
    status: item.status,
    priority: toPriority(item.status),
    updated_at: toIso(item.created_at),
    detail_hint: item.latest_work_order_outbox?.status || null,
  }))

  const subcontractTodos: MobileReadonlyTodoItem[] = subcontract.items.slice(0, PREVIEW_LIMIT).map((item) => ({
    id: `subcontract-${item.id}`,
    source: 'subcontract',
    title: `Subcontract ${item.subcontract_no}`,
    status: item.status,
    priority: toPriority(item.status),
    updated_at: toIso(item.created_at),
    detail_hint: item.latest_issue_sync_status || item.latest_receipt_sync_status || null,
  }))

  const qualityTodos: MobileReadonlyTodoItem[] = quality.items.slice(0, PREVIEW_LIMIT).map((item) => ({
    id: `quality-${item.id}`,
    source: 'quality',
    title: `Quality inspection ${item.inspection_no}`,
    status: item.status,
    priority: toPriority(item.status),
    updated_at: toIso(item.created_at),
    detail_hint: item.result,
  }))

  const costTodos: MobileReadonlyTodoItem[] = cost.items
    .slice(0, PREVIEW_LIMIT)
    .filter((item) => item.unresolved_count > 0)
    .map((item) => ({
      id: `cost-snapshot-${item.id}`,
      source: 'cost',
      title: `Cost snapshot ${item.snapshot_no}`,
      status: item.snapshot_status,
      priority: item.unresolved_count > 0 ? 'high' : toPriority(item.snapshot_status),
      updated_at: toIso(item.created_at),
      detail_hint: `unresolved_count=${item.unresolved_count}`,
    }))

  return [...productionTodos, ...subcontractTodos, ...qualityTodos, ...costTodos]
}

const buildMessages = (todos: MobileReadonlyTodoItem[]): MobileReadonlyMessageItem[] => {
  return todos.slice(0, PREVIEW_LIMIT * 2).map((todo) => ({
    id: `message-${todo.id}`,
    source: todo.source,
    title: `${todo.source.toUpperCase()} projection update`,
    content: `${todo.title} is currently ${todo.status}.`,
    level: toMessageLevel(todo.priority),
    created_at: todo.updated_at,
  }))
}

const buildReminders = (todos: MobileReadonlyTodoItem[]): MobileReadonlyReminderItem[] => {
  return todos.slice(0, PREVIEW_LIMIT * 2).map((todo) => ({
    id: `reminder-${todo.id}`,
    source: todo.source,
    reminder_type: 'todo',
    text: `${todo.title} (${todo.status})`,
    created_at: todo.updated_at,
  }))
}

export const fetchMobileReadonlyOverview = async (
  query: MobileReadonlyProjectionQuery,
): Promise<MobileReadonlyOverviewData> => {
  const [production, cost, subcontract, quality, inventory] = await Promise.all([
    fetchMobileReadonlyProductionBoard(query),
    fetchMobileReadonlyCostBoard(query),
    fetchMobileReadonlySubcontractBoard(query),
    fetchMobileReadonlyQualityBoard(query),
    fetchMobileReadonlyInventoryBoard(query),
  ])

  const todos = buildTodos(production, cost, subcontract, quality)
  const messages = buildMessages(todos)
  const reminders = buildReminders(todos)

  return {
    generated_at: new Date().toISOString(),
    todos,
    messages,
    reminders,
    boards: {
      production,
      cost,
      subcontract,
      quality,
      inventory,
    },
    frozen_actions: MOBILE_READONLY_FROZEN_ACTIONS,
  }
}

export const fetchMobileReadonlyProductionPlanProjection = async (
  planId: number,
): Promise<ProductionPlanDetailData> => {
  const response = await fetchProductionPlanDetail(planId)
  return response.data
}

export const fetchMobileReadonlyStyleProfitSnapshotProjection = async (
  snapshotId: number,
): Promise<StyleProfitSnapshotDetailData> => {
  const response = await fetchStyleProfitSnapshotDetail(snapshotId)
  return response.data
}

export const fetchMobileReadonlySubcontractProjection = async (
  orderId: number,
): Promise<SubcontractOrderDetailData> => {
  const response = await fetchSubcontractOrderDetail(orderId)
  return response.data
}

export const fetchMobileReadonlyQualityProjection = async (
  inspectionId: number,
): Promise<QualityInspectionDetailData> => {
  const response = await fetchQualityInspectionDetail(inspectionId)
  return response.data
}
