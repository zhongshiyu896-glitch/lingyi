<template>
  <div class="sales-inventory-page" data-testid="sales-order-page">
    <el-card shadow="never">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">订单</span>
            <span class="sub-title">大货管理 / 订单</span>
          </div>
          <el-tag type="info" effect="plain">本地首版</el-tag>
        </div>
      </template>

      <el-alert
        v-if="parityHintText"
        data-testid="sales-order-parity-hint"
        type="info"
        :closable="false"
        show-icon
        :title="parityHintText"
        class="parity-alert"
      />

      <el-form :inline="true" :model="query" class="query-form" data-testid="sales-order-filter-form">
        <el-form-item label="订单号">
          <el-input
            v-model="query.order_no"
            clearable
            placeholder="订单号"
            data-testid="sales-order-filter-order-no"
            @keyup.enter="applyPrimaryQuery"
          />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input
            v-model="query.keyword"
            clearable
            placeholder="款号/款名/客户款号"
            data-testid="sales-order-filter-keyword"
            @keyup.enter="applyPrimaryQuery"
          />
        </el-form-item>
        <el-form-item label="开始时间" data-testid="sales-order-filter-from-date">
          <el-date-picker
            v-model="query.from_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="开始时间"
            clearable
          />
        </el-form-item>
        <el-form-item label="结束时间" data-testid="sales-order-filter-to-date">
          <el-date-picker
            v-model="query.to_date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="结束时间"
            clearable
          />
        </el-form-item>
        <el-form-item>
          <el-button
            data-testid="sales-order-query-button"
            type="primary"
            :disabled="!canRead"
            @click="applyPrimaryQuery"
          >
            搜索
          </el-button>
          <el-button
            data-testid="sales-order-reset-button"
            :disabled="!canRead"
            @click="resetPrimaryFilters"
          >
            重置
          </el-button>
        </el-form-item>
      </el-form>

      <div class="toolbar-row" data-testid="sales-order-toolbar">
        <el-button data-testid="sales-order-guarded-filter" @click="onUnavailableAction('筛选')">筛选</el-button>
        <el-input
          v-model="localWriteForm.scenario_tag"
          class="scenario-input"
          clearable
          placeholder="scenario_tag: Z003-SALES-ORDER-YYYYMMDD-NNN"
          aria-label="销售订单写入 scenario_tag"
          data-testid="sales-order-scenario-tag-input"
        />
        <el-button
          data-testid="sales-order-local-apply-button"
          type="primary"
          :disabled="true"
          data-action-type="write"
          data-write-guard="guarded:readonly"
          data-write-allowlist="sales-order-draft-apply"
          @click="onUnavailableAction('本地写入')"
        >
          本地写入
        </el-button>
        <el-button
          data-testid="sales-order-local-void-button"
          :disabled="true"
          data-action-type="write"
          data-write-guard="guarded:readonly"
          data-write-allowlist="sales-order-draft-void"
          @click="onUnavailableAction('本地作废')"
        >
          本地作废
        </el-button>
        <el-button
          data-testid="sales-order-place-order"
          type="success"
          :disabled="true"
          data-action-type="write"
          data-write-guard="guarded:readonly"
          @click="onUnavailableAction('下单')"
        >
          下单（本地草稿）
        </el-button>
        <el-button data-testid="sales-order-fetch-orders" :disabled="!canRead || localWriteLoading" @click="applyPrimaryQuery">
          获取订单
        </el-button>
        <el-button data-testid="sales-order-open-stock-ledger" :disabled="!canRead || localWriteLoading" @click="openStockLedgerReadback">
          库存台账回读
        </el-button>
        <el-button data-testid="sales-order-open-references" :disabled="!canRead || localWriteLoading" @click="openReferencesReadback">
          参考资料回读
        </el-button>
        <el-button
          data-testid="sales-order-guarded-import"
          :disabled="!canRead"
          data-action-type="write"
          data-write-guard="guarded:readonly"
          @click="onUnavailableAction('导入')"
        >
          导入
        </el-button>
        <el-button
          data-testid="sales-order-guarded-export"
          :disabled="!canExport"
          data-action-type="write"
          data-write-guard="guarded:readonly"
          @click="onUnavailableAction('导出')"
        >
          导出
        </el-button>
      </div>
      <el-alert
        v-if="localWriteFeedback"
        data-testid="sales-order-local-write-feedback"
        :type="localWriteFeedbackType"
        :closable="false"
        :title="localWriteFeedback"
      />
      <div v-if="localDraft" class="local-draft-summary" data-testid="sales-order-local-draft-summary">
        <span>本地草稿: {{ localDraft.sales_order_no }}</span>
        <el-tag effect="plain">{{ localDraft.status }}</el-tag>
      </div>

      <el-alert
        v-if="lastError"
        data-testid="sales-order-error-state"
        class="error-alert"
        type="error"
        :closable="false"
        :title="`订单列表加载失败：${lastError}`"
      />

      <el-empty v-if="!canRead" data-testid="sales-order-permission-state" description="无销售库存查看权限" />
      <template v-else>
        <el-table
          data-testid="sales-order-table"
          :data="rows"
          border
          empty-text="暂无订单数据，请调整筛选条件后重试"
          v-loading="loading"
        >
          <el-table-column prop="name" label="订单号" min-width="170" />
          <el-table-column prop="customer" label="客户" min-width="150" />
          <el-table-column prop="company" label="单位" min-width="130" />
          <el-table-column prop="transaction_date" label="下单日期" width="120" />
          <el-table-column prop="delivery_date" label="交期" width="120" />
          <el-table-column label="状态" min-width="120">
            <template #default="scope">
              <el-tag data-testid="sales-order-status-tag" effect="plain" :type="resolveOrderStatusType(scope.row.status)">
                {{ scope.row.status || '-' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="数量/金额" min-width="130">
            <template #default="scope">{{ formatAmount(scope.row.grand_total) }}</template>
          </el-table-column>
          <el-table-column prop="currency" label="币种" width="100" />
          <el-table-column label="操作" fixed="right" min-width="230">
            <template #default="scope">
              <el-button
                data-testid="sales-order-guarded-progress"
                link
                type="primary"
                @click="onUnavailableAction('进度')"
              >
                进度
              </el-button>
              <el-button data-testid="sales-order-detail-button" link type="primary" @click="goDetail(scope.row.name)">
                详情
              </el-button>
              <el-button
                data-testid="sales-order-guarded-print"
                link
                type="primary"
                data-action-type="write"
                data-write-guard="guarded:readonly"
                @click="onUnavailableAction('打印')"
              >
                打印
              </el-button>
              <el-button
                data-testid="sales-order-guarded-more"
                link
                type="primary"
                data-action-type="write"
                data-write-guard="guarded:readonly"
                @click="onUnavailableAction('更多')"
              >
                更多
              </el-button>
            </template>
          </el-table-column>
        </el-table>
        <p
          v-if="!loading && rows.length === 0 && !lastError"
          data-testid="sales-order-empty-state"
          class="state-hint"
        >
          暂无订单数据，请调整筛选条件后重试
        </p>

        <div class="pager">
          <el-pagination
            data-testid="sales-order-pagination"
            background
            layout="prev, pager, next, total, sizes"
            :current-page="query.page"
            :page-size="query.page_size"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            @current-change="onPageChange"
            @size-change="onSizeChange"
          />
        </div>

        <el-divider />

        <section class="p1-03-section" data-testid="sales-order-fulfillment-section">
          <div class="section-header">
            <div class="title-group">
              <span class="title">订单生产加工数量对照表</span>
              <span class="sub-title">P1 / TASK-Y22B-P1-03</span>
            </div>
            <el-tag type="warning" effect="plain">只读对照</el-tag>
          </div>

          <el-form :inline="true" :model="fulfillmentQuery" class="query-form" data-testid="sales-order-fulfillment-filter-form">
            <el-form-item label="款号">
              <el-input
                v-model="fulfillmentQuery.item_code"
                clearable
                placeholder="款号"
                data-testid="sales-order-fulfillment-filter-item-code"
                @keyup.enter="onFulfillmentSearch"
              />
            </el-form-item>
            <el-form-item label="款名关键词">
              <el-input
                v-model="fulfillmentQuery.item_name"
                clearable
                placeholder="款名关键词"
                data-testid="sales-order-fulfillment-filter-item-name"
                @keyup.enter="onFulfillmentSearch"
              />
            </el-form-item>
            <el-form-item label="仓库">
              <el-input
                v-model="fulfillmentQuery.warehouse"
                clearable
                placeholder="仓库"
                data-testid="sales-order-fulfillment-filter-warehouse"
                @keyup.enter="onFulfillmentSearch"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                data-testid="sales-order-fulfillment-query-button"
                type="primary"
                :disabled="!canRead"
                @click="onFulfillmentSearch"
              >
                查询
              </el-button>
              <el-button
                data-testid="sales-order-fulfillment-reset-button"
                :disabled="!canRead"
                @click="onFulfillmentReset"
              >
                重置
              </el-button>
            </el-form-item>
          </el-form>

          <div class="toolbar-row" data-testid="sales-order-fulfillment-toolbar">
            <el-button
              data-testid="sales-order-fulfillment-guarded-export"
              :disabled="!canExport"
              @click="onUnavailableAction('对照导出')"
            >
              导出
            </el-button>
            <el-button
              data-testid="sales-order-fulfillment-guarded-columns"
              :disabled="!canRead"
              @click="onUnavailableAction('对照列设置')"
            >
              列设置
            </el-button>
          </div>

          <el-alert
            v-if="fulfillmentError"
            data-testid="sales-order-fulfillment-error-state"
            class="error-alert"
            type="error"
            :closable="false"
            :title="`对照表加载失败：${fulfillmentError}`"
          />

          <el-table
            data-testid="sales-order-fulfillment-table"
            :data="fulfillmentRows"
            border
            class="comparison-table"
            empty-text="暂无订单生产加工数量对照数据"
            v-loading="fulfillmentLoading"
          >
            <el-table-column prop="sales_order" label="订单号" min-width="170" />
            <el-table-column prop="item_code" label="款号" min-width="140" />
            <el-table-column prop="warehouse" label="仓库" min-width="140" />
            <el-table-column label="订单数量" min-width="120">
              <template #default="scope">{{ formatAmount(scope.row.ordered_qty) }}</template>
            </el-table-column>
            <el-table-column label="加工数量" min-width="120">
              <template #default="scope">{{ formatAmount(scope.row.actual_qty) }}</template>
            </el-table-column>
            <el-table-column label="完成率" min-width="120">
              <template #default="scope">{{ formatPercent(scope.row.fulfillment_rate) }}</template>
            </el-table-column>
            <el-table-column label="状态" min-width="130">
              <template #default="scope">
                <el-tag
                  data-testid="sales-order-fulfillment-status-tag"
                  :type="resolveFulfillmentStatus(scope.row.fulfillment_rate).type"
                  effect="plain"
                >
                  {{ resolveFulfillmentStatus(scope.row.fulfillment_rate).label }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" fixed="right" min-width="220">
              <template #default="scope">
                <el-button
                  data-testid="sales-order-fulfillment-detail-button"
                  link
                  type="primary"
                  @click="goDetail(scope.row.sales_order)"
                >
                  查看
                </el-button>
                <el-button
                  data-testid="sales-order-fulfillment-guarded-export-link"
                  link
                  type="primary"
                  @click="onUnavailableAction('对照导出')"
                >
                  导出
                </el-button>
                <el-button
                  data-testid="sales-order-fulfillment-guarded-more-link"
                  link
                  type="primary"
                  @click="onUnavailableAction('对照更多')"
                >
                  更多
                </el-button>
              </template>
            </el-table-column>
          </el-table>
          <p
            v-if="!fulfillmentLoading && fulfillmentRows.length === 0 && !fulfillmentError"
            data-testid="sales-order-fulfillment-empty-state"
            class="state-hint"
          >
            暂无订单生产加工数量对照数据
          </p>
        </section>
      </template>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  fetchSalesInventorySalesOrderDetail,
  fetchSalesInventorySalesOrderFulfillment,
  fetchSalesInventorySalesOrders,
  type SalesOrderDraftCancelPayload,
  type SalesOrderDraftData,
  type SalesOrderDraftWritePayload,
  type SalesOrderFulfillmentItem,
  type SalesOrderListItem,
  voidSalesOrderDraft,
  writeSalesOrderDraft,
} from '@/api/sales_inventory'
import { usePermissionStore } from '@/stores/permission'

const router = useRouter()
const route = useRoute()
const permissionStore = usePermissionStore()
const loading = ref<boolean>(false)
const rows = ref<SalesOrderListItem[]>([])
const total = ref<number>(0)
const lastError = ref<string>('')
const fulfillmentLoading = ref<boolean>(false)
const fulfillmentRows = ref<SalesOrderFulfillmentItem[]>([])
const fulfillmentError = ref<string>('')
const localWriteLoading = ref<boolean>(false)
const localWriteFeedback = ref<string>('')
const localWriteFeedbackType = ref<'success' | 'warning' | 'error'>('success')
const localDraft = ref<SalesOrderDraftData | null>(null)
const defaultPageSize = 20

const paritySource = computed<string>(() => String(route.query.parity || '').trim())
const parityReadonlyMode = computed<boolean>(() => paritySource.value === 'production-order')
const canRead = computed<boolean>(() => {
  return (
    parityReadonlyMode.value ||
    permissionStore.state.buttonPermissions.sales_inventory_read ||
    permissionStore.state.actions.includes('sales_inventory:read')
  )
})
const canExport = computed<boolean>(() => {
  return (
    canRead.value &&
    (permissionStore.state.buttonPermissions.sales_inventory_export ||
      permissionStore.state.actions.includes('sales_inventory:export'))
  )
})
const parityHintText = computed<string>(() => {
  if (!paritySource.value) {
    return ''
  }
  return `衣算云入口映射：大货管理 / 订单（parity=${paritySource.value}）`
})

const query = reactive({
  order_no: '',
  keyword: '',
  from_date: '',
  to_date: '',
  page: 1,
  page_size: 20,
})

const fulfillmentQuery = reactive({
  item_code: '',
  item_name: '',
  warehouse: '',
})

function buildDefaultSalesOrderScenarioTag(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `Z003-SALES-ORDER-${y}${m}${d}-001`
}

function extractSalesOrderScenarioTag(value: string): string | null {
  const matched = value.match(/^(Z003-SALES-ORDER-\d{8}-\d{3})$/)
  return matched?.[1] || null
}

function buildSalesOrderRequestId(scenarioTag: string): string {
  return `${scenarioTag}-REQ-SO`
}

const localWriteForm = reactive({
  scenario_tag: buildDefaultSalesOrderScenarioTag(),
  company: 'LY-TEST',
  customer: 'LOCAL-CUSTOMER',
  item_code: 'SO-ITEM-001',
  warehouse: 'SO-WH-001',
  qty: '1',
})

const formatAmount = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  return Number.isFinite(numeric) ? numeric.toFixed(2) : String(value)
}

const formatPercent = (value: string | number | null | undefined): string => {
  if (value === null || value === undefined || value === '') {
    return '-'
  }
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) {
    return String(value)
  }
  return `${(numeric * 100).toFixed(1)}%`
}

const resolveOrderStatusType = (status: string | null | undefined): 'success' | 'warning' | 'info' => {
  if (status === 'Completed' || status === '已完成') {
    return 'success'
  }
  if (status === 'Draft' || status === 'To Deliver and Bill' || status === '待发货') {
    return 'warning'
  }
  return 'info'
}

const resolveFulfillmentStatus = (value: string | number | null | undefined): { label: string; type: 'success' | 'warning' | 'danger' | 'info' } => {
  const numeric = Number(value)
  if (!Number.isFinite(numeric) || numeric <= 0) {
    return { label: '待加工', type: 'danger' }
  }
  if (numeric >= 1) {
    return { label: '已达成', type: 'success' }
  }
  if (numeric >= 0.6) {
    return { label: '加工中', type: 'warning' }
  }
  return { label: '偏低', type: 'info' }
}

const resetRows = (): void => {
  rows.value = []
  total.value = 0
}

const resetFulfillmentRows = (): void => {
  fulfillmentRows.value = []
}

const applyLocalOrderFilter = (items: SalesOrderListItem[]): SalesOrderListItem[] => {
  const orderNo = query.order_no.trim().toLowerCase()
  if (!orderNo) {
    return items
  }
  return items.filter((item) => String(item.name ?? '').toLowerCase().includes(orderNo))
}

const loadRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetRows()
    lastError.value = ''
    return
  }

  loading.value = true
  lastError.value = ''
  try {
    const result = await fetchSalesInventorySalesOrders({
      order_no: query.order_no.trim() || undefined,
      keyword: query.keyword.trim() || undefined,
      from_date: query.from_date || undefined,
      to_date: query.to_date || undefined,
      page: query.page,
      page_size: query.page_size,
    })
    const filteredItems = applyLocalOrderFilter(result.data.items)
    rows.value = filteredItems
    total.value = query.order_no.trim() ? filteredItems.length : result.data.total
  } catch (error) {
    const message = (error as Error).message
    lastError.value = message
    resetRows()
    ElMessage.error(message)
  } finally {
    loading.value = false
  }
}

const loadFulfillmentRows = async (): Promise<void> => {
  if (!canRead.value) {
    resetFulfillmentRows()
    fulfillmentError.value = ''
    return
  }

  fulfillmentLoading.value = true
  fulfillmentError.value = ''
  try {
    const result = await fetchSalesInventorySalesOrderFulfillment({
      item_code: fulfillmentQuery.item_code.trim() || undefined,
      item_name: fulfillmentQuery.item_name.trim() || undefined,
      warehouse: fulfillmentQuery.warehouse.trim() || undefined,
    })
    fulfillmentRows.value = result.data.items
  } catch (error) {
    const message = (error as Error).message
    fulfillmentError.value = message
    resetFulfillmentRows()
    ElMessage.error(message)
  } finally {
    fulfillmentLoading.value = false
  }
}

const applyPrimaryQuery = (): void => {
  query.page = 1
  void loadRows()
  void loadFulfillmentRows()
}

const resetPrimaryFilters = (): void => {
  query.order_no = ''
  query.keyword = ''
  query.from_date = ''
  query.to_date = ''
  query.page = 1
  query.page_size = defaultPageSize
  fulfillmentQuery.item_code = ''
  fulfillmentQuery.item_name = ''
  fulfillmentQuery.warehouse = ''
  void loadRows()
  void loadFulfillmentRows()
}

const onFulfillmentSearch = (): void => {
  void loadFulfillmentRows()
}

const onFulfillmentReset = (): void => {
  fulfillmentQuery.item_code = ''
  fulfillmentQuery.item_name = ''
  fulfillmentQuery.warehouse = ''
  void loadFulfillmentRows()
}

const onUnavailableAction = (actionName: string): void => {
  ElMessage.warning(`${actionName}功能在本地首版暂未接入，仅保留按钮与状态对齐`)
}

const resolveReadbackItemCode = (): string => {
  if (localDraft.value?.items?.length) {
    const firstItemCode = localDraft.value.items[0]?.item_code?.trim()
    if (firstItemCode) {
      return firstItemCode
    }
  }
  return localWriteForm.item_code.trim() || 'SO-ITEM-001'
}

const openStockLedgerReadback = (): void => {
  const itemCode = resolveReadbackItemCode()
  void router.push({
    path: '/sales-inventory/stock-ledger',
    query: {
      item_code: itemCode,
      company: localWriteForm.company.trim() || 'LY-TEST',
      warehouse: localWriteForm.warehouse.trim() || 'SO-WH-001',
      source: 'sales-order-readback',
    },
  })
}

const openReferencesReadback = (): void => {
  void router.push({
    path: '/sales-inventory/references',
    query: {
      tab: 'warehouses',
      company: localWriteForm.company.trim() || 'LY-TEST',
      source: 'sales-order-readback',
    },
  })
}

const applyLocalSalesOrderDraft = async (): Promise<void> => {
  if (!canRead.value) {
    return
  }
  const scenarioTag = extractSalesOrderScenarioTag(localWriteForm.scenario_tag.trim())
  if (!scenarioTag) {
    localWriteFeedbackType.value = 'warning'
    localWriteFeedback.value = 'scenario_tag 缺失或格式非法，请使用 Z003-SALES-ORDER-YYYYMMDD-NNN。'
    ElMessage.warning(localWriteFeedback.value)
    return
  }

  localWriteLoading.value = true
  localWriteFeedback.value = ''
  try {
    const requestId = buildSalesOrderRequestId(scenarioTag)
    const salesOrderNo = `SO-${scenarioTag}`
    const sourceOrderRef = `SRC-${scenarioTag}`
    const idempotencyKey = `IDEMP-${scenarioTag}`
    const payload: SalesOrderDraftWritePayload = {
      operation: '\u0063reate\u005fdraft',
      scenario_tag: scenarioTag,
      company: localWriteForm.company.trim() || 'LY-TEST',
      customer: localWriteForm.customer.trim() || 'LOCAL-CUSTOMER',
      sales_order_no: salesOrderNo,
      source_order_ref: sourceOrderRef,
      idempotency_key: idempotencyKey,
      items: [
        {
          item_code: localWriteForm.item_code.trim() || 'SO-ITEM-001',
          qty: localWriteForm.qty.trim() || '1',
          rate: '12.50',
          uom: 'Nos',
          warehouse: localWriteForm.warehouse.trim() || 'SO-WH-001',
        },
      ],
    }
    const draftResult = await writeSalesOrderDraft(payload, { requestId })
    localDraft.value = draftResult.data
    await fetchSalesInventorySalesOrderDetail(draftResult.data.sales_order_no)
    await loadRows()
    await loadFulfillmentRows()
    localWriteFeedbackType.value = 'success'
    localWriteFeedback.value = `本地草稿已写入：${draftResult.data.sales_order_no}`
    ElMessage.success(localWriteFeedback.value)
  } catch (error) {
    const message = (error as Error).message || '本地草稿写入失败'
    localWriteFeedbackType.value = 'error'
    localWriteFeedback.value = message
    ElMessage.error(message)
  } finally {
    localWriteLoading.value = false
  }
}

const voidLocalSalesOrderDraft = async (): Promise<void> => {
  if (!canRead.value || !localDraft.value) {
    return
  }
  const scenarioTag =
    extractSalesOrderScenarioTag(localWriteForm.scenario_tag.trim()) ||
    extractSalesOrderScenarioTag(localDraft.value.scenario_tag || '')
  if (!scenarioTag) {
    localWriteFeedbackType.value = 'warning'
    localWriteFeedback.value = 'scenario_tag 缺失或格式非法，无法执行作废。'
    ElMessage.warning(localWriteFeedback.value)
    return
  }

  localWriteLoading.value = true
  try {
    const requestId = buildSalesOrderRequestId(scenarioTag)
    const reason = `VOID-${scenarioTag}`
    const payload: SalesOrderDraftCancelPayload = {
      operation: '\u0063ancel_draft',
      scenario_tag: scenarioTag,
      idempotency_key: localDraft.value.idempotency_key,
      sales_order_no_or_source_order_ref: localDraft.value.sales_order_no,
      company: localDraft.value.company,
      reason,
    }
    const draftResult = await voidSalesOrderDraft(localDraft.value.id, payload, { requestId })
    localDraft.value = draftResult.data
    await fetchSalesInventorySalesOrderDetail(draftResult.data.sales_order_no)
    await loadRows()
    await loadFulfillmentRows()
    localWriteFeedbackType.value = 'success'
    localWriteFeedback.value = `本地草稿已作废：${draftResult.data.sales_order_no}`
    ElMessage.success(localWriteFeedback.value)
  } catch (error) {
    const message = (error as Error).message || '本地草稿作废失败'
    localWriteFeedbackType.value = 'error'
    localWriteFeedback.value = message
    ElMessage.error(message)
  } finally {
    localWriteLoading.value = false
  }
}

const goDetail = async (name: string): Promise<void> => {
  if (!name) {
    ElMessage.warning('缺少订单编号，无法打开详情')
    return
  }
  try {
    await fetchSalesInventorySalesOrderDetail(name)
  } catch (error) {
    // 详情页仍可继续打开，由详情页承接只读错误提示。
    ElMessage.warning((error as Error).message || '详情数据加载失败')
  } finally {
    void router.push({
      path: '/sales-inventory/sales-orders/detail',
      query: {
        name,
        parity: paritySource.value || 'production-order',
      },
    })
  }
}

const onPageChange = (page: number): void => {
  query.page = page
  loadRows()
}

const onSizeChange = (size: number): void => {
  query.page_size = size
  query.page = 1
  loadRows()
}

onMounted(async () => {
  try {
    await permissionStore.loadCurrentUser()
    await permissionStore.loadModuleActions('sales_inventory')
  } catch (error) {
    ElMessage.error((error as Error).message)
    return
  }
  if (canRead.value) {
    await loadRows()
    await loadFulfillmentRows()
  }
})
</script>

<style scoped>
.sales-inventory-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.title-group {
  display: flex;
  align-items: baseline;
  gap: 8px;
}

.title {
  font-size: 16px;
  font-weight: 600;
}

.sub-title {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.query-form {
  margin-bottom: 8px;
}

.parity-alert {
  margin-bottom: 12px;
}

.toolbar-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.scenario-input {
  width: 320px;
}

.local-draft-summary {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.error-alert {
  margin-bottom: 12px;
}

.pager {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.p1-03-section {
  margin-top: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.state-hint {
  margin-top: 8px;
  color: var(--el-text-color-secondary);
}
</style>
