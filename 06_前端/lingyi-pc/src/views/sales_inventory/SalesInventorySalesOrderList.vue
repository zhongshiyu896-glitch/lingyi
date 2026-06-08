<template>
  <div class="sales-order-list-page" data-testid="cand544-sales-order-list-page">
    <el-card shadow="never" data-testid="cand544-sales-order-shell">
      <template #header>
        <div class="header-row">
          <div class="title-group">
            <span class="title">大货管理 / 销售订单履约闸口查询</span>
            <span class="sub-title">NEXT-CAND-544 / fulfillment gate readonly</span>
          </div>
          <div class="header-actions">
            <div class="header-tags">
              <el-tag size="small" type="success" effect="plain">GET-only readback</el-tag>
              <el-tag size="small" type="warning" effect="plain">write chain disabled</el-tag>
            </div>
            <div class="guarded-actions" data-testid="cand544-sales-order-guarded-actions">
              <el-button
                v-for="action in readonlyGuardActions"
                :key="action.label"
                disabled
                data-action-type="write"
                data-guard-state="disabled"
              >
                {{ action.label }}
              </el-button>
            </div>
          </div>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        class="scope-alert"
        title="当前切片仅提供销售订单 fulfillment gate 列表/详情回读，不触发 delivery、export、customer-supplier write、stock-write、outbox/worker 或 ERPNext 写链路。"
      />

      <section class="summary-grid" data-testid="cand544-sales-order-summary">
        <div class="summary-card">
          <span class="summary-label">服务端总数</span>
          <strong class="summary-value">{{ serverTotal }}</strong>
        </div>
        <div class="summary-card">
          <span class="summary-label">当前页命中</span>
          <strong class="summary-value">{{ readonlySummary.filteredCount }}</strong>
        </div>
        <div class="summary-card">
          <span class="summary-label">草稿跟进</span>
          <strong class="summary-value">{{ readonlySummary.draftCount }}</strong>
        </div>
        <div class="summary-card">
          <span class="summary-label">交付跟进</span>
          <strong class="summary-value">{{ readonlySummary.deliveryCount }}</strong>
        </div>
        <div class="summary-card">
          <span class="summary-label">当前页客户数</span>
          <strong class="summary-value">{{ readonlySummary.customerCount }}</strong>
        </div>
        <div class="summary-card">
          <span class="summary-label">当前页金额</span>
          <strong class="summary-value">{{ formatMoney(readonlySummary.totalAmount, activeCurrency) }}</strong>
        </div>
      </section>

      <section class="query-panel" data-testid="cand544-sales-order-query-panel">
        <el-form :model="query" inline class="query-form">
          <el-form-item label="订单号">
            <el-input v-model="query.order_no" clearable placeholder="订单号" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="关键字">
            <el-input v-model="query.keyword" clearable placeholder="订单号/客户/公司/状态" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="客户">
            <el-input v-model="query.customer" clearable placeholder="客户名称" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="公司">
            <el-input v-model="query.company" clearable placeholder="公司" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="款号">
            <el-input v-model="query.item_code" clearable placeholder="款号" @keyup.enter="onSearch" />
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="query.status" clearable placeholder="全部状态" style="width: 180px">
              <el-option label="全部状态" value="" />
              <el-option
                v-for="status in statusOptions"
                :key="status"
                :label="statusLabel(status)"
                :value="status"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="跟进分组">
            <el-select v-model="query.followup_group" clearable placeholder="全部分组" style="width: 180px">
              <el-option label="全部分组" value="" />
              <el-option label="草稿跟进" value="draft-watch" />
              <el-option label="交付跟进" value="delivery-followup" />
              <el-option label="关闭订单" value="closed" />
            </el-select>
          </el-form-item>
          <el-form-item label="开始日期">
            <el-date-picker
              v-model="query.from_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="开始日期"
              clearable
            />
          </el-form-item>
          <el-form-item label="结束日期">
            <el-date-picker
              v-model="query.to_date"
              type="date"
              value-format="YYYY-MM-DD"
              placeholder="结束日期"
              clearable
            />
          </el-form-item>
          <el-form-item>
            <el-button @click="onReset">重置</el-button>
            <el-button type="primary" :loading="loading" @click="onSearch">查询</el-button>
          </el-form-item>
        </el-form>
      </section>

      <el-alert
        v-if="lastError"
        type="error"
        :closable="false"
        :title="lastError"
        class="error-alert"
        data-testid="cand544-sales-order-error"
      />

      <section class="readonly-panel" data-testid="cand544-sales-order-readback-notes">
        <el-descriptions border :column="3">
          <el-descriptions-item label="route_scope">
            /sales-inventory/sales-orders?tab=fulfillment-gate-readonly&amp;parity=sales-order
          </el-descriptions-item>
          <el-descriptions-item label="write_chain">disabled</el-descriptions-item>
          <el-descriptions-item label="当前页条数">{{ filteredRows.length }}</el-descriptions-item>
          <el-descriptions-item label="最后刷新">{{ lastLoadedAt || '-' }}</el-descriptions-item>
          <el-descriptions-item label="筛选分组">
            {{ query.followup_group ? followupGroupLabel(query.followup_group as SalesOrderReadonlyGroup) : '全部分组' }}
          </el-descriptions-item>
          <el-descriptions-item label="状态筛选">
            {{ query.status ? statusLabel(query.status) : '全部状态' }}
          </el-descriptions-item>
        </el-descriptions>
      </section>

      <div data-testid="cand544-sales-order-list-fulfillment-anchor">
        <SalesOrderFulfillmentGateReadonly :summary="fulfillmentGateReadonlySummary" />
      </div>

      <el-table
        v-loading="loading"
        :data="filteredRows"
        border
        class="result-table"
        :empty-text="emptyText"
        data-testid="cand544-sales-order-table"
      >
        <el-table-column prop="name" label="订单号" min-width="170" />
        <el-table-column prop="company" label="公司" min-width="140" />
        <el-table-column label="客户" min-width="160">
          <template #default="{ row }">
            {{ customerLabel(row.customer) }}
          </template>
        </el-table-column>
        <el-table-column prop="transaction_date" label="下单日期" min-width="120" />
        <el-table-column prop="delivery_date" label="交期" min-width="120" />
        <el-table-column label="跟进分组" min-width="130">
          <template #default="{ row }">
            <el-tag :type="followupGroupType(followupGroupFromRow(row))" effect="plain">
              {{ followupGroupLabel(followupGroupFromRow(row)) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="140">
          <template #default="{ row }">
            <el-tag :type="statusType(row.status)" effect="plain">
              {{ statusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="金额" min-width="140">
          <template #default="{ row }">
            {{ formatMoney(row.grand_total, row.currency) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <div class="row-actions">
              <el-button link type="primary" @click="openDetail(row)">查看详情</el-button>
              <el-button
                link
                disabled
                data-action-type="write"
                data-guard-state="disabled"
              >
                导出
              </el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pager" data-testid="cand544-sales-order-pagination">
        <el-pagination
          background
          layout="prev, pager, next, total, sizes"
          :current-page="query.page"
          :page-size="query.page_size"
          :total="serverTotal"
          :page-sizes="[10, 20, 50, 100]"
          @current-change="onPageChange"
          @size-change="onSizeChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { SalesOrderListItem } from '@/api/sales_inventory'
import {
  buildSalesOrderReadonlySummary,
  fetchSalesInventorySalesOrdersReadback,
  filterSalesOrderRows,
  type SalesOrderReadbackQuery,
  type SalesOrderReadonlyGroup,
} from '@/api/sales_inventory_sales_orders'
import SalesOrderFulfillmentGateReadonly from '@/views/sales_inventory/components/SalesOrderFulfillmentGateReadonly.vue'
import { useSalesOrderFulfillmentGateReadonly } from '@/views/sales_inventory/composables/useSalesOrderFulfillmentGateReadonly'
import { useSalesOrderReadback } from '@/views/sales_inventory/composables/useSalesOrderReadback'

interface SalesOrderListQueryState extends SalesOrderReadbackQuery {
  status: string
  followup_group: string
}

const route = useRoute()
const router = useRouter()

const {
  customerLabel,
  followupGroupFromRow,
  followupGroupLabel,
  followupGroupType,
  readonlyGuardActions,
  statusLabel,
  statusType,
} = useSalesOrderReadback()

const loading = ref(false)
const lastError = ref('')
const rows = ref<SalesOrderListItem[]>([])
const serverTotal = ref(0)
const lastLoadedAt = ref('')

const createDefaultQuery = (): SalesOrderListQueryState => ({
  order_no: '',
  keyword: '',
  company: '',
  customer: '',
  item_code: '',
  from_date: '',
  to_date: '',
  status: '',
  followup_group: '',
  page: 1,
  page_size: 20,
})

const query = reactive<SalesOrderListQueryState>(createDefaultQuery())

const filteredRows = computed(() => filterSalesOrderRows(rows.value, query))
const readonlySummary = computed(() => buildSalesOrderReadonlySummary(filteredRows.value))
const activeCurrency = computed(() => filteredRows.value[0]?.currency || rows.value[0]?.currency || '')
const { fulfillmentGateReadonlySummary } = useSalesOrderFulfillmentGateReadonly({
  rows: filteredRows,
  tab: computed(() => String(route.query.tab || 'fulfillment-gate-readonly')),
  parity: computed(() => String(route.query.parity || 'sales-order')),
  focus: computed(() => String(route.query.focus || 'fulfillment-source')),
  lastLoadedAt,
  lastError,
})
const statusOptions = computed(() => {
  const options = Array.from(
    new Set(rows.value.map((row) => row.status?.trim()).filter((value): value is string => Boolean(value))),
  )
  return options.length > 0
    ? options
    : ['Draft', 'To Bill', 'To Deliver', 'To Deliver and Bill', 'Completed', 'Cancelled']
})

const emptyText = computed(() => {
  if (loading.value) return '正在加载销售订单'
  if (lastError.value) return '查询失败'
  if (query.status || query.followup_group) return '当前筛选下暂无销售订单'
  return '暂无销售订单数据'
})

const formatMoney = (amount?: string | number | null, currency?: string | null): string => {
  if (amount === null || amount === undefined || amount === '') return '-'
  const numeric = Number(amount)
  if (!Number.isFinite(numeric)) return String(amount)
  const money = numeric.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
  return currency ? `${money} ${currency}` : money
}

const updateLoadedAt = (): void => {
  lastLoadedAt.value = new Date().toISOString()
}

const loadOrders = async (): Promise<void> => {
  loading.value = true
  lastError.value = ''
  try {
    const response = await fetchSalesInventorySalesOrdersReadback(query)
    rows.value = response.data.items
    serverTotal.value = response.data.total
    query.page = response.data.page
    query.page_size = response.data.page_size
    updateLoadedAt()
  } catch (error) {
    rows.value = []
    serverTotal.value = 0
    lastError.value = (error as Error).message || '销售订单查询失败'
  } finally {
    loading.value = false
  }
}

const onSearch = (): void => {
  query.page = 1
  void loadOrders()
}

const onReset = (): void => {
  Object.assign(query, createDefaultQuery())
  void loadOrders()
}

const onPageChange = (page: number): void => {
  query.page = page
  void loadOrders()
}

const onSizeChange = (size: number): void => {
  query.page = 1
  query.page_size = size
  void loadOrders()
}

const openDetail = (row: SalesOrderListItem): void => {
  router.push({
    path: '/sales-inventory/sales-orders/detail',
    query: {
      name: row.name,
      tab: String(route.query.tab || 'fulfillment-gate-readonly'),
      parity: String(route.query.parity || 'sales-order'),
      focus: String(route.query.focus || 'fulfillment-source'),
    },
  })
}

onMounted(() => {
  void loadOrders()
})
</script>

<style scoped>
.sales-order-list-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.header-row,
.header-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.title-group,
.header-tags {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.header-actions {
  flex-wrap: wrap;
  justify-content: flex-end;
}

.guarded-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.title {
  font-size: 18px;
  font-weight: 600;
}

.sub-title {
  color: var(--el-text-color-secondary);
  font-size: 13px;
}

.scope-alert,
.error-alert {
  margin-bottom: 16px;
}

.summary-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  margin-bottom: 16px;
}

.summary-card {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  background: var(--el-fill-color-blank);
}

.summary-label {
  color: var(--el-text-color-secondary);
  font-size: 12px;
}

.summary-value {
  font-size: 18px;
}

.query-panel,
.readonly-panel {
  margin-bottom: 16px;
}

.query-form {
  row-gap: 8px;
}

.result-table {
  width: 100%;
}

.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.pager {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}
</style>
